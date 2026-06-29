"""Launch Webots MVP with dummy actions and heartbeat (VLA-26 + VLA-27)."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description() -> LaunchDescription:
    package_dir = get_package_share_directory("litevla_bridge")
    return LaunchDescription(
        [
            DeclareLaunchArgument("control_mode", default_value="dummy"),
            DeclareLaunchArgument("sequence_step_sec", default_value="2.0"),
            DeclareLaunchArgument("heartbeat_hz", default_value="10.0"),
            DeclareLaunchArgument("action_timeout_sec", default_value="0.5"),
            DeclareLaunchArgument("frame_timeout_sec", default_value="2.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([package_dir, "launch", "webots_sim.launch.py"])
                ),
            ),
            Node(
                package="litevla_bridge",
                executable="heartbeat_controller",
                name="litevla_heartbeat_controller",
                output="screen",
                parameters=[
                    {
                        "control_mode": LaunchConfiguration("control_mode"),
                        "heartbeat_hz": ParameterValue(
                            LaunchConfiguration("heartbeat_hz"), value_type=float
                        ),
                        "action_timeout_sec": ParameterValue(
                            LaunchConfiguration("action_timeout_sec"), value_type=float
                        ),
                        "frame_timeout_sec": ParameterValue(
                            LaunchConfiguration("frame_timeout_sec"), value_type=float
                        ),
                    }
                ],
            ),
            Node(
                package="litevla_bridge",
                executable="dummy_action_generator",
                name="litevla_dummy_action_generator",
                output="screen",
                parameters=[
                    {
                        "control_mode": LaunchConfiguration("control_mode"),
                        "sequence_step_sec": ParameterValue(
                            LaunchConfiguration("sequence_step_sec"), value_type=float
                        ),
                    }
                ],
            ),
        ]
    )
