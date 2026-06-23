"""Launch heartbeat controller (VLA-27)."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("heartbeat_hz", default_value="10.0"),
            DeclareLaunchArgument("action_timeout_sec", default_value="0.5"),
            DeclareLaunchArgument("frame_timeout_sec", default_value="2.0"),
            DeclareLaunchArgument("require_frame", default_value="true"),
            Node(
                package="litevla_bridge",
                executable="heartbeat_controller",
                name="litevla_heartbeat_controller",
                output="screen",
                parameters=[
                    {
                        "heartbeat_hz": ParameterValue(
                            LaunchConfiguration("heartbeat_hz"), value_type=float
                        ),
                        "action_timeout_sec": ParameterValue(
                            LaunchConfiguration("action_timeout_sec"), value_type=float
                        ),
                        "frame_timeout_sec": ParameterValue(
                            LaunchConfiguration("frame_timeout_sec"), value_type=float
                        ),
                        "require_frame": ParameterValue(
                            LaunchConfiguration("require_frame"), value_type=bool
                        ),
                    }
                ],
            ),
        ]
    )
