#!/usr/bin/env python3

# Copyright (c) 2026 FlexComm Bridge Contributors
# SPDX-License-Identifier: MIT
# Disclaimer: Provided "as is", without warranty; see LICENSE.

"""
Utility functions for converting ROS messages to/from JSON format.
"""

import json
from array import array


def _to_json_compatible(value):
    """Recursively convert ROS field values into JSON-serializable types."""
    if hasattr(value, '__slots__'):
        return message_to_json(value)

    if isinstance(value, array):
        return list(value)

    if isinstance(value, (list, tuple)):
        return [_to_json_compatible(item) for item in value]

    if isinstance(value, dict):
        return {key: _to_json_compatible(item) for key, item in value.items()}

    return value


def message_to_json(msg):
    """
    Convert a ROS message to a JSON-serializable dictionary.

    Args:
        msg: ROS message object

    Returns:
        dict: JSON-serializable dictionary representation of the message
    """
    result = {}
    for field in msg.__slots__:
        value = getattr(msg, field)
        result[field] = _to_json_compatible(value)
    return result


def json_to_message(data, msg_type):
    """
    Convert a JSON dictionary to a ROS message.

    Args:
        data (dict): JSON dictionary containing message data
        msg_type (type): ROS message type class

    Returns:
        ROS message object of msg_type
    """
    msg = msg_type()

    # Convenience handling for std_msgs/String-like messages:
    # - If payload is not a dict, map it to msg.data directly
    # - If payload is a dict without "data", serialize full dict into msg.data
    if hasattr(msg, 'data'):
        if not isinstance(data, dict):
            if isinstance(data, (dict, list)):
                msg.data = json.dumps(data)
            else:
                msg.data = str(data)
            return msg
        if 'data' not in data:
            msg.data = json.dumps(data)
            return msg
    
    # Get field type information from ROS2 message
    field_types = msg_type.get_fields_and_field_types()
    
    for key, value in data.items():
        if hasattr(msg, key):
            attr = getattr(msg, key)
            field_type = field_types.get(key, '')
            
            # Handle nested messages (have __slots__ attribute)
            if hasattr(attr, '__slots__'):
                if isinstance(value, dict):
                    nested_msg = json_to_message(value, type(attr))
                    setattr(msg, key, nested_msg)
            # Handle lists
            elif isinstance(value, list):
                if len(value) > 0 and isinstance(value[0], dict):
                    # List of nested messages - parse type from field_type
                    # Format: "sequence<package/MessageType>"
                    if 'sequence<' in field_type:
                        # Extract message type
                        msg_type_str = field_type.split('<')[1].rstrip('>')
                        # Convert "package_name/MessageType" to module import
                        if '/' in msg_type_str:
                            pkg, msg_name = msg_type_str.split('/')
                            # Import the message type
                            import importlib
                            msg_module = importlib.import_module(f'{pkg}.msg')
                            nested_msg_type = getattr(msg_module, msg_name)
                            # Convert each dict to message object
                            converted_list = [json_to_message(item, nested_msg_type) for item in value]
                            setattr(msg, key, converted_list)
                        else:
                            # Fallback: just set the list
                            setattr(msg, key, value)
                    else:
                        # Not a sequence type, just set directly
                        setattr(msg, key, value)
                else:
                    # List of primitives or empty list
                    setattr(msg, key, value)
            # Handle all primitives (strings, numbers, bools, etc.)
            else:
                setattr(msg, key, value)
    return msg
