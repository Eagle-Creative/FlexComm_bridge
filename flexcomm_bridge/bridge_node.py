# Copyright (c) 2026 FlexComm Bridge Contributors
# SPDX-License-Identifier: MIT
# Disclaimer: Provided "as is", without warranty; see LICENSE.

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
import yaml
import json
from importlib import import_module
from flexcomm_bridge.protocol.mqtt_protocol import MqttProtocol
from flexcomm_bridge.message_utils import message_to_json, json_to_message
import os
from ament_index_python.packages import get_package_share_directory

class FlexCommBridge(Node):
    """
    A ROS 2 node that bridges ROS topics with external systems using MQTT protocol.
    """

    def __init__(self, config_path=None):
        """
        Initialize the FlexCommBridge node.

        Args:
            config_path (str, optional): Path to the configuration file. Defaults to package bridge_config.yaml.
        """
        super().__init__('flexcomm_bridge')
        self.get_logger().info("Initializing FlexCommBridge...")
        
        # Declare parameter for config path
        self.declare_parameter('config_path', '')
        self.declare_parameter('deployment_config_path', '')
        
        # Load configuration
        if config_path is None:
            config_path = self.get_parameter('config_path').get_parameter_value().string_value
        
        if not config_path or not os.path.exists(config_path):
            config_path = os.path.join(
                get_package_share_directory('flexcomm_bridge'), 
                'config', 
                'bridge_config.yaml'
            )
        
        self.get_logger().info(f"Loading configuration from: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        deployment_config_param = self.get_parameter('deployment_config_path').get_parameter_value().string_value

        # Get location_id from config for topic namespacing
        self.location_id = self.config.get('location_id', '')
        self.namespace_root = str(self.config.get('namespace_root', 'bridge')).strip('/ ')
        if not self.namespace_root:
            self.namespace_root = 'bridge'

        if self.location_id:
            self.get_logger().info(
                f"Using location-based topic namespacing: {self.namespace_root}/{self.location_id}/"
            )
        else:
            self.get_logger().info(
                f"No location_id specified, using default topics: {self.namespace_root}/"
            )

        # Initialize MQTT protocol with logger
        mqtt_config = self.config['protocol']
        mqtt_config['logger'] = self.get_logger()
        self.protocol = MqttProtocol(mqtt_config)
        self._topic_publishers = {}  # Store ROS publishers (renamed to avoid conflict with Node._publishers)

        self.get_logger().info(f"Loaded configuration: {self.config}")

        # Setup connections
        self.connections = list(self.config.get('connections', []))
        self._augment_connections_with_robot_joint_states(deployment_config_param)
        self._augment_connections_with_robot_endeffector_states(deployment_config_param)
        self._setup_connections()

    def _load_enabled_robot_names(self, deployment_config_path=''):
        """
        Load enabled robot names from deployment profile.

        Args:
            deployment_config_path (str): Path to deployment profile.

        Returns:
            list[str]: Enabled robot names.
        """
        profile_path = deployment_config_path or self.config.get('deployment_config_path', '')
        if not profile_path:
            return []

        if not os.path.exists(profile_path):
            return []

        try:
            with open(profile_path, 'r') as profile_file:
                deployment_profile = yaml.safe_load(profile_file) or {}
        except Exception as error:
            self.get_logger().error(
                f"Failed to parse deployment profile for auto topic mapping: {error}"
            )
            return []

        robot_entries = deployment_profile.get('robots', {}).get('entries', [])
        if not isinstance(robot_entries, list) or not robot_entries:
            return []

        robot_names = []
        for index, robot in enumerate(robot_entries):
            if not isinstance(robot, dict):
                continue
            if not robot.get('enabled', True):
                continue

            robot_name = str(robot.get('name', f'robot_{index}')).strip()
            if robot_name:
                robot_names.append(robot_name)

        return robot_names

    def _augment_connections_with_robot_joint_states(self, deployment_config_path=''):
        """
        Auto-add ROS→MQTT joint state forwarding for each enabled robot in deployment profile.

        The generated MQTT topic is: <namespace_root>/robots/<robot_name>/joint_states
        and will be namespaced to <namespace_root>/<location_id>/... automatically.
        """
        auto_enabled = self.config.get('auto_publish_robot_joint_states', False)
        if not auto_enabled:
            return

        profile_path = deployment_config_path or self.config.get('deployment_config_path', '')
        if not profile_path:
            self.get_logger().warn(
                "auto_publish_robot_joint_states enabled but no deployment_config_path provided"
            )
            return

        if not os.path.exists(profile_path):
            self.get_logger().warn(
                f"auto_publish_robot_joint_states enabled but deployment profile not found: {profile_path}"
            )
            return

        robot_names = self._load_enabled_robot_names(profile_path)
        if not robot_names:
            self.get_logger().info(
                "No robots.entries found in deployment profile for auto joint state mapping"
            )
            return

        existing_ros_topics = {
            connection.get('ros_topic')
            for connection in self.connections
            if isinstance(connection, dict)
        }

        added_connections = 0
        for robot_name in robot_names:

            ros_topic = f'/{robot_name}/joint_states'
            if ros_topic in existing_ros_topics:
                continue

            self.connections.append({
                'ros_topic': ros_topic,
                'flexcomm_topic': f'{self.namespace_root}/robots/{robot_name}/joint_states',
                'message_type': 'sensor_msgs/msg/JointState',
                'direction': 'ros_to_mqtt',
            })
            existing_ros_topics.add(ros_topic)
            added_connections += 1

        self.get_logger().info(
            f"Auto-added {added_connections} robot joint state ROS→MQTT connection(s) from deployment profile"
        )

    def _augment_connections_with_robot_endeffector_states(self, deployment_config_path=''):
        """
        Auto-add ROS→MQTT endeffector state forwarding for each enabled robot in deployment profile.

        The generated MQTT topic is: <namespace_root>/robots/<robot_name>/endeffector_state
        and will be namespaced to <namespace_root>/<location_id>/... automatically.
        """
        auto_enabled = self.config.get('auto_publish_robot_endeffector_states', False)
        if not auto_enabled:
            return

        profile_path = deployment_config_path or self.config.get('deployment_config_path', '')
        if not profile_path:
            self.get_logger().warn(
                "auto_publish_robot_endeffector_states enabled but no deployment_config_path provided"
            )
            return

        if not os.path.exists(profile_path):
            self.get_logger().warn(
                f"auto_publish_robot_endeffector_states enabled but deployment profile not found: {profile_path}"
            )
            return

        robot_names = self._load_enabled_robot_names(profile_path)
        if not robot_names:
            self.get_logger().info(
                "No robots.entries found in deployment profile for auto endeffector state mapping"
            )
            return

        existing_ros_topics = {
            connection.get('ros_topic')
            for connection in self.connections
            if isinstance(connection, dict)
        }

        added_connections = 0
        for robot_name in robot_names:
            ros_topic = f'/{robot_name}/endeffector_state'
            if ros_topic in existing_ros_topics:
                continue

            self.connections.append({
                'ros_topic': ros_topic,
                'flexcomm_topic': f'{self.namespace_root}/robots/{robot_name}/endeffector_state',
                'message_type': 'mirobot_msgs/msg/EndeffectorState',
                'direction': 'ros_to_mqtt',
            })
            existing_ros_topics.add(ros_topic)
            added_connections += 1

        self.get_logger().info(
            f"Auto-added {added_connections} robot endeffector state ROS→MQTT connection(s) from deployment profile"
        )

    def _namespace_mqtt_topic(self, topic):
        """
        Apply location-based namespacing to MQTT topics.
        
        Args:
            topic (str): Base MQTT topic
            
        Returns:
            str: Namespaced topic (e.g., bridge/lab_a/instructions)
        """
        if not self.location_id:
            return topic
        
        # Strip leading/trailing slashes
        topic = topic.strip('/')

        root_prefix = f'{self.namespace_root}/'
        
        # If topic already starts with namespace root, inject location_id
        if topic.startswith(root_prefix):
            # Split into parts: <namespace_root>/<rest>
            parts = topic.split('/', 1)
            if len(parts) == 2:
                # Insert location_id: <namespace_root>/<location_id>/<rest>
                return f"{self.namespace_root}/{self.location_id}/{parts[1]}"
            else:
                # Just <namespace_root> - add location_id
                return f"{self.namespace_root}/{self.location_id}"

        if topic == self.namespace_root:
            return f"{self.namespace_root}/{self.location_id}"
        
        # Otherwise return as-is
        return topic

    def _setup_connections(self):
        """
        Setup ROS subscriptions and MQTT subscriptions based on configuration.
        """
        for conn in self.connections:
            self.get_logger().info(f"Processing connection: {conn}")
            
            try:
                msg_type = self._import_msg_type(conn['message_type'])
                
                # Apply location-based namespacing to MQTT topic
                mqtt_topic = self._namespace_mqtt_topic(conn['flexcomm_topic'])
                
                # Log if topic was namespaced
                if mqtt_topic != conn['flexcomm_topic']:
                    self.get_logger().info(
                        f"Applied namespace: {conn['flexcomm_topic']} → {mqtt_topic}"
                    )

                # ROS to MQTT (backward compatible with ros_to_unity)
                if conn['direction'] in ('ros_to_mqtt', 'ros_to_unity', 'bidirectional'):
                    self.get_logger().info(
                        f"Setting up ROS→MQTT subscription: {conn['ros_topic']} → {mqtt_topic}"
                    )
                    self.create_subscription(
                        msg_type,
                        conn['ros_topic'],
                        self._ros_to_mqtt_callback(conn, mqtt_topic),
                        10
                    )

                # MQTT to ROS (backward compatible with unity_to_ros)
                if conn['direction'] in ('mqtt_to_ros', 'unity_to_ros', 'bidirectional'):
                    self.get_logger().info(
                        f"Setting up MQTT→ROS subscription: {mqtt_topic} → {conn['ros_topic']}"
                    )
                    self.protocol.subscribe(
                        mqtt_topic,
                        self._mqtt_to_ros_callback(conn, msg_type)
                    )
            except Exception as e:
                self.get_logger().error(f"Failed to setup connection {conn}: {e}")

    def _import_msg_type(self, type_str):
        """
        Import a ROS message type from a string.

        Args:
            type_str (str): Message type in format 'package_name/msg/MessageType'

        Returns:
            type: The imported message class

        Example:
            'sensor_msgs/msg/JointState' → sensor_msgs.msg.JointState
        """
        pkg, _, msg = type_str.partition('/msg/')
        module = import_module(f"{pkg}.msg")
        return getattr(module, msg)

    def _ros_to_mqtt_callback(self, conn, mqtt_topic):
        """
        Create a callback for ROS to MQTT message forwarding.

        Args:
            conn (dict): Connection configuration
            mqtt_topic (str): Namespaced MQTT topic

        Returns:
            function: Callback function
        """
        def callback(msg):
            try:
                self.get_logger().debug(f"Received ROS message on {conn['ros_topic']}")
                json_payload = message_to_json(msg)
                self.protocol.publish(mqtt_topic, json_payload)
                self.get_logger().debug(
                    f"Published to MQTT: {mqtt_topic} = {json_payload}"
                )
            except Exception as e:
                self.get_logger().error(f"Error in ROS→MQTT callback: {e}")
        return callback
    
    # Backward compatibility alias
    def _ros_to_unity_callback(self, conn):
        return self._ros_to_mqtt_callback(conn)

    def _mqtt_to_ros_callback(self, conn, msg_type):
        """
        Create a callback for MQTT to ROS message forwarding.

        Args:
            conn (dict): Connection configuration
            msg_type (type): ROS message type

        Returns:
            function: Callback function
        """
        def callback(json_data):
            try:
                self.get_logger().info(
                    f"[BRIDGE] Received MQTT message on {conn['flexcomm_topic']}, publishing to ROS: {conn['ros_topic']}"
                )
                self.get_logger().debug(
                    f"Received MQTT message on {conn['flexcomm_topic']}: {json_data}"
                )
                ros_msg = json_to_message(json_data, msg_type)
                pub = self._get_or_create_publisher(conn['ros_topic'], msg_type)
                
                # DIAGNOSTIC: Count number of subscribers to this topic
                pub_info = self.count_subscribers(conn['ros_topic'])
                self.get_logger().info(f"[BRIDGE DIAGNOSTIC] Topic {conn['ros_topic']} has {pub_info} subscribers")
                
                pub.publish(ros_msg)
                self.get_logger().info(f"[BRIDGE] Published to ROS: {conn['ros_topic']}")
            except Exception as e:
                import traceback
                self.get_logger().error(f"Error in MQTT→ROS callback: {e}")
                self.get_logger().error(f"Traceback: {traceback.format_exc()}")
                self.get_logger().error(f"JSON data: {json_data}")
                self.get_logger().error(f"Message type: {msg_type}")
        return callback
    
    # Backward compatibility alias
    def _unity_to_ros_callback(self, conn, msg_type):
        return self._mqtt_to_ros_callback(conn, msg_type)

    def _get_or_create_publisher(self, topic, msg_type):
        """
        Get or create a ROS publisher for a topic with RELIABLE QoS.

        Args:
            topic (str): ROS topic name
            msg_type (type): ROS message type

        Returns:
            Publisher: ROS publisher object
        """
        if topic not in self._topic_publishers:
            # Use RELIABLE QoS with TRANSIENT_LOCAL durability
            # This ensures messages are delivered even if subscriber joins after publish
            qos_profile = QoSProfile(
                reliability=QoSReliabilityPolicy.RELIABLE,
                durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=10
            )
            self._topic_publishers[topic] = self.create_publisher(msg_type, topic, qos_profile)
            self.get_logger().info(f"Created publisher for topic: {topic} with RELIABLE + TRANSIENT_LOCAL QoS")
        return self._topic_publishers[topic]

def main(args=None):
    """
    Main entry point for the FlexCommBridge node.
    """
    rclpy.init(args=args)
    bridge = FlexCommBridge()
    bridge.get_logger().info("FlexCommBridge initialized, starting spin...")
    
    try:
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        bridge.get_logger().info("Shutting down FlexCommBridge...")
    finally:
        bridge.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
