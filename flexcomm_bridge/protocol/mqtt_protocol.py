#!/usr/bin/env python3

# Copyright (c) 2026 FlexComm Bridge Contributors
# SPDX-License-Identifier: MIT
# Disclaimer: Provided "as is", without warranty; see LICENSE.

import paho.mqtt.client as mqtt
import ssl
import json


class MqttProtocol:
    """
    MQTT protocol handler for FlexCommBridge.
    """

    def __init__(self, config):
        """
        Initialize the MQTT client with the given configuration.

        Args:
            config (dict): Configuration dictionary containing MQTT connection parameters.
        """
        # Create client - compatible with paho-mqtt 2.x
        try:
            # Try paho-mqtt 2.x initialization with callback_api_version
            import paho.mqtt.client as mqtt_module
            if hasattr(mqtt_module, 'CallbackAPIVersion'):
                self.client = mqtt.Client(callback_api_version=mqtt_module.CallbackAPIVersion.VERSION1)
            else:
                self.client = mqtt.Client()
        except:
            self.client = mqtt.Client()
            
        self.logger = config.get('logger', None)
        
        if self.logger:
            self.logger.info(f"MQTT config: {config}")
        else:
            print(f"MQTT config: {config}")

        # Set username and password if provided
        if config.get("username"):
            self.client.username_pw_set(config["username"], config["password"])

        # Configure SSL/TLS if required
        if config.get("use_ssl", False):
            self.client.tls_set(
                ca_certs=config.get("ca_cert", None),
                cert_reqs=ssl.CERT_REQUIRED
            )

        # Set up connection callback
        self.client.on_connect = self._on_connect
        
        # Connect to MQTT broker
        self.client.connect(config["host"], config["port"])
        self.client.loop_start()

        self.subscriptions = {}

        # Set the on_message handler
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback for when the client receives a CONNACK response from the server.
        Compatible with both paho-mqtt 1.x and 2.x

        Args:
            client: The MQTT client instance.
            userdata: Private user data.
            flags: Response flags sent by the broker.
            rc: Connection result code.
            properties: MQTT v5 properties (optional, for paho-mqtt 2.x)
        """
        if self.logger:
            self.logger.info(f"[MQTT] Connected to broker with result code: {rc}")
        else:
            print(f"[MQTT] Connected to broker with result code: {rc}")

    def publish(self, topic, payload):
        """
        Publish a message to an MQTT topic.

        Args:
            topic (str): The MQTT topic to publish to.
            payload: The message payload (will be converted to JSON).
        """
        json_payload = json.dumps(payload)
        self.client.publish(topic, json_payload)
        
        if self.logger:
            self.logger.debug(f"[MQTT] Published to {topic}: {json_payload}")

    def subscribe(self, topic, callback):
        """
        Subscribe to an MQTT topic with a callback function.

        Args:
            topic (str): The MQTT topic to subscribe to.
            callback (function): Callback function to handle received messages.
        """
        if self.logger:
            self.logger.info(f"[MQTT] Subscribing to: {topic}")
        else:
            print(f"[MQTT] Subscribing to: {topic}")
        
        self.client.subscribe(topic)
        self.subscriptions[topic] = callback

    def _on_message(self, client, userdata, msg):
        """
        Callback for when a PUBLISH message is received from the server.

        Args:
            client: The MQTT client instance.
            userdata: Private user data.
            msg: An instance of MQTTMessage containing topic, payload, qos, retain.
        """
        topic = msg.topic
        
        if self.logger:
            self.logger.debug(f"[MQTT] Received message on {topic}")
        else:
            print(f"[MQTT] Received message on {topic}")
        
        if topic in self.subscriptions:
            try:
                payload = json.loads(msg.payload.decode())
                self.subscriptions[topic](payload)
                
                if self.logger:
                    self.logger.debug(f"[MQTT] Processed message on {topic}: {payload}")
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.error(f"[MQTT] Failed to decode JSON on {topic}: {e}")
                else:
                    print(f"[MQTT] Failed to decode JSON on {topic}: {e}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[MQTT] Failed to process message on {topic}: {e}")
                else:
                    print(f"[MQTT] Failed to process message on {topic}: {e}")
        else:
            if self.logger:
                self.logger.warning(f"[MQTT] No subscription callback for topic: {topic}")
            else:
                print(f"[MQTT] No subscription callback for topic: {topic}")
