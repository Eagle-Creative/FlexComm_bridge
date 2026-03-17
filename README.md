# FlexComm Bridge

A ROS 2 package that bridges ROS topics and MQTT topics with optional location-based namespacing.

## Highlights

- Bidirectional ROS 2 <-> MQTT forwarding
- JSON payload conversion for ROS messages
- Optional topic namespacing via `location_id`
- Local defaults that run without private infrastructure

## Repository Readiness

This repository is prepared for public publishing:

- No personal credentials in tracked config
- No private hostnames in default runtime files
- Open-source license (`MIT`)
- Sensible `.gitignore` for ROS 2 and Python workflows

## Requirements

- ROS 2 (tested with Jazzy-compatible dependencies)
- Python 3.10+
- MQTT broker (for local testing, `mosquitto`)

Install common dependencies:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients ros-jazzy-rclpy ros-jazzy-std-msgs
```

## Quick Start (Out of the Box)

1. Build the package:

```bash
colcon build --packages-select flexcomm_bridge
source install/setup.bash
```

2. Start a local MQTT broker:

```bash
mosquitto -v
```

3. Start the bridge in another terminal:

```bash
source install/setup.bash
ros2 run flexcomm_bridge bridge_node
```

Default config: `config/bridge_config.yaml`

- MQTT broker: `localhost:1883`
- ROS inbound topic: `/flexcomm/in`
- ROS outbound topic: `/flexcomm/out`
- MQTT namespace root: `bridge`
- MQTT inbound topic (namespaced): `bridge/demo_site/server/instructions`
- MQTT outbound topic (namespaced): `bridge/demo_site/server/status`

## Verify Bridging

Test MQTT -> ROS 2:

```bash
# Terminal A
ros2 topic echo /flexcomm/in

# Terminal B
mosquitto_pub -h localhost -t "bridge/demo_site/server/instructions" -m '"hello from mqtt"'
```

Test ROS 2 -> MQTT:

```bash
# Terminal A
mosquitto_sub -h localhost -t "bridge/demo_site/server/status" -v

# Terminal B
ros2 topic pub /flexcomm/out std_msgs/msg/String '{data: "hello from ros2"}'
```

## Configuration

Primary config file:

- `config/bridge_config.yaml`

If you need credentials or production broker values, keep them out of git by using local override files (for example `config/bridge_config.local.yaml`) and `.env` files.

## License

This project is licensed under the MIT License. See `LICENSE`.
