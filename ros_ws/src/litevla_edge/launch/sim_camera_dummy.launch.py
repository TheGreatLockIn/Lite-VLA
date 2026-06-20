from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="image_tools",
                executable="cam2image",
                name="sim_camera",
                output="screen",
                parameters=[
                    {
                        "burger_mode": True,
                        "frequency": 10.0,
                        "width": 320,
                        "height": 240,
                    }
                ],
                remappings=[
                    ("image", "/image_raw"),
                ],
            ),
            Node(
                package="litevla_edge",
                executable="dummy_controller",
                name="litevla_dummy_controller",
                output="screen",
                parameters=[
                    {
                        "cmd_vel_topic": "/cmd_vel",
                        "image_topic": "/image_raw",
                        "dummy_action": "MOVE_FORWARD",
                        "publish_hz": 6.6,
                    }
                ],
            ),
        ]
    )
