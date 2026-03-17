# Contributing

Thanks for your interest in improving `flexcomm_bridge`.

## Development Setup

1. Install dependencies:

```bash
sudo apt update
sudo apt install -y ros-jazzy-rclpy ros-jazzy-std-msgs mosquitto mosquitto-clients
```

2. Build and source:

```bash
colcon build --packages-select flexcomm_bridge
source install/setup.bash
```

3. Run local smoke test:

```bash
ros2 run flexcomm_bridge bridge_node
```

## Pull Request Guidelines

- Keep changes focused and small.
- Update `README.md` when behavior or config changes.
- Do not commit secrets, credentials, or machine-specific config.
- Keep default config in `config/bridge_config.yaml` public-safe.
- Ensure `colcon build --packages-select flexcomm_bridge` passes.

## Commit Message Style

Use clear, action-oriented messages, for example:

- `feat: add configurable namespace root`
- `fix: handle empty mqtt username`
- `docs: improve quickstart and config reference`

## Reporting Issues

When filing a bug, include:

- ROS 2 distro
- OS version
- Minimal config snippet
- Exact command run
- Relevant logs
