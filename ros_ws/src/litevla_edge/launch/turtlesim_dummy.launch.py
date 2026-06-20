from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="turtlesim",
                executable="turtlesim_node",
                name="turtlesim",
                output="screen",
            ),
            Node(
                package="litevla_edge",
                executable="dummy_controller",
                name="litevla_dummy_controller",
                output="screen",
                parameters=[
                    {
                        "cmd_vel_topic": "/turtle1/cmd_vel",
                        "dummy_action": "MOVE_FORWARD",
                        "publish_hz": 6.6,
                    }
                ],
            ),
        ]
    )
