# FlexComm Bridge

`flexcomm_bridge` is a ROS 2 package that bridges ROS topics and MQTT topics.
It supports bidirectional forwarding, JSON payload conversion, and optional location-based MQTT topic namespacing.

## Quickstart

1. Install runtime dependencies:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients ros-jazzy-rclpy ros-jazzy-std-msgs
```

2. Build and source:

```bash
colcon build --packages-select flexcomm_bridge
source install/setup.bash
```

3. Start MQTT broker and bridge in separate terminals:

```bash
mosquitto -v
```

```bash
source install/setup.bash
ros2 run flexcomm_bridge bridge_node
```

4. Verify MQTT -> ROS 2:

```bash
# Terminal A
source install/setup.bash
ros2 topic echo /flexcomm/in

# Terminal B
mosquitto_pub -h localhost -t "bridge/demo_site/server/instructions" -m '"hello from mqtt"'
```

5. Verify ROS 2 -> MQTT:

```bash
# Terminal A
mosquitto_sub -h localhost -t "bridge/demo_site/server/status" -v

# Terminal B
source install/setup.bash
ros2 topic pub --once /flexcomm/out std_msgs/msg/String '{data: "hello from ros2"}'
```

## Features

- ROS 2 -> MQTT and MQTT -> ROS 2 forwarding
- Config-driven topic mapping
- Optional MQTT namespacing via `namespace_root` and `location_id`
- Local, public-safe defaults for first run
- MQTT transport via `paho-mqtt`

## Requirements

- ROS 2 (Jazzy or compatible)
- Python 3.10+
- MQTT broker (examples use Mosquitto)

Install common runtime dependencies:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients ros-jazzy-rclpy ros-jazzy-std-msgs
```

## Developer Guide

### Runtime Entry Points

- Node executable: `bridge_node = flexcomm_bridge.bridge_node:main`
- Launch file: `flexcomm_bridge/launch/bridge.launch.py`
- Effective runtime config: `config/bridge_config.yaml`

## Run

Start a local MQTT broker:

```bash
mosquitto -v
```

Run the bridge node:

```bash
source install/setup.bash
ros2 run flexcomm_bridge bridge_node
```

Or with launch file:

```bash
source install/setup.bash
ros2 launch flexcomm_bridge bridge.launch.py
```

Override config path at runtime:

```bash
source install/setup.bash
ros2 run flexcomm_bridge bridge_node --ros-args -p config_path:=/absolute/path/to/bridge_config.yaml
```

## Default Behavior

Default config file: `config/bridge_config.yaml`

- MQTT broker: `localhost:1883`
- Namespace root: `bridge`
- Location ID: `demo_site`
- ROS inbound topic: `/flexcomm/in`
- ROS outbound topic: `/flexcomm/out`
- MQTT inbound topic (effective): `bridge/demo_site/server/instructions`
- MQTT outbound topic (effective): `bridge/demo_site/server/status`

## Configuration

The runtime config is `config/bridge_config.yaml`.

Top-level fields:

- `protocol`: MQTT transport settings (`host`, `port`, TLS, credentials)
- `namespace_root`: MQTT topic root to namespace (default `bridge`)
- `location_id`: Injected into topics under `namespace_root`
- `connections`: List of bridge mappings

Connection entry format:

```yaml
- ros_topic: /example/in
  flexcomm_topic: bridge/server/input
  message_type: std_msgs/msg/String
  direction: mqtt_to_ros
```

`direction` values:

- `mqtt_to_ros`
- `ros_to_mqtt`
- `bidirectional`

### Namespacing Rules

- If `location_id` is empty, topic names are used as-is.
- If `location_id` is set, only topics under `namespace_root` are namespaced.
- Example with defaults:
  - Config topic: `bridge/server/status`
  - Effective MQTT topic: `bridge/demo_site/server/status`

### Extending for Additional Message Types

- Message conversion lives in `flexcomm_bridge/message_utils.py`.
- Dynamic message imports and connection wiring live in `flexcomm_bridge/bridge_node.py`.
- To add a new mapping, add an entry under `connections` with a valid ROS message type string (`package/msg/Type`).

### Logging and Diagnostics

- Startup logs show:
  - Loaded config path
  - Effective namespace root and location
  - Applied topic transformations
  - MQTT subscriptions/publications

For live troubleshooting:

```bash
mosquitto_sub -h localhost -t "#" -v
```

## Notes

- Keep production secrets out of git. Use local overrides (for example `config/bridge_config.local.yaml`) or environment-based injection in your deployment setup.
- This repository is intentionally generic and does not require project-specific infrastructure to run locally.

## Troubleshooting

- Bridge starts but no messages pass: verify broker is reachable with `mosquitto_sub -h localhost -t "#" -v`.
- Bridge starts but no messages pass: confirm the effective namespaced topic matches your publisher/subscriber topic.
- Bridge starts but no messages pass: check the ROS topic type matches `message_type` in config.
- `ros2 topic pub` exits with an error: ensure ROS environment is sourced in that terminal (`source install/setup.bash`).

## License

MIT License. See `LICENSE`.

## Repository Standards

- Contributing guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Pull request template: `.github/PULL_REQUEST_TEMPLATE.md`
- Issue templates: `.github/ISSUE_TEMPLATE/`
- Continuous integration: `.github/workflows/ci.yml`
