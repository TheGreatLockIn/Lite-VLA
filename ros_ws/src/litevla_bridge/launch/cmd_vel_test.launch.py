"""Launch cmd_vel movement test sequence (VLA-25)."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
            DeclareLaunchArgument("max_linear_vel", default_value="0.2"),
            DeclareLaunchArgument("max_angular_vel", default_value="0.6"),
            DeclareLaunchArgument("step_duration_sec", default_value="2.0"),
            Node(
                package="litevla_bridge",
                executable="cmd_vel_tester",
                name="litevla_cmd_vel_tester",
                output="screen",
                parameters=[
                    {
                        "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                        "max_linear_vel": ParameterValue(
                            LaunchConfiguration("max_linear_vel"), value_type=float
                        ),
                        "max_angular_vel": ParameterValue(
                            LaunchConfiguration("max_angular_vel"), value_type=float
                        ),
                        "step_duration_sec": ParameterValue(
                            LaunchConfiguration("step_duration_sec"), value_type=float
                        ),
                    }
                ],
            ),
        ]
    )
