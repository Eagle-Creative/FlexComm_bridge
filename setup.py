# Copyright (c) 2026 FlexComm Bridge Contributors
# SPDX-License-Identifier: MIT
# Disclaimer: Provided "as is", without warranty; see LICENSE.

from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'flexcomm_bridge'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('flexcomm_bridge/launch/*.py')),
    ],
    install_requires=['setuptools', 'paho-mqtt', 'pyyaml'],
    zip_safe=True,
    maintainer='FlexComm Bridge Maintainers',
    maintainer_email='maintainers@example.com',
    description='ROS 2 MQTT bridge with configurable topic mapping and namespacing',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bridge_node = flexcomm_bridge.bridge_node:main'
        ],
    },
)
