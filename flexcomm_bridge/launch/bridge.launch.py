# Copyright (c) 2026 FlexComm Bridge Contributors
# SPDX-License-Identifier: MIT
# Disclaimer: Provided "as is", without warranty; see LICENSE.

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get the config file path
    config_file = os.path.join(
        get_package_share_directory('flexcomm_bridge'),
        'config',
        'bridge_config.yaml'
    )
    
    return LaunchDescription([
        Node(
            package='flexcomm_bridge',
            executable='bridge_node',
            name='flexcomm_bridge',
            output='screen',
            emulate_tty=True,
            parameters=[{'config_path': config_file}]
        )
    ])
