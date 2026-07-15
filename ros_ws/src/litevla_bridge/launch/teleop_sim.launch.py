"""Launch keyboard teleop with heartbeat (VLA-28). Run in an interactive terminal."""

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
            DeclareLaunchArgument("heartbeat_hz", default_value="25.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([package_dir, "launch", "webots_sim.launch.py"])
                ),
                launch_arguments={
                    "interactive": "true",
                    "use_sim_time": "true",
                }.items(),
            ),
            Node(
                package="litevla_bridge",
                executable="heartbeat_controller",
                name="litevla_heartbeat_controller",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": True,
                        "control_mode": "teleop",
                        "require_frame": False,
                        "teleop_startup_grace_sec": 20.0,
                        "heartbeat_hz": ParameterValue(
                            LaunchConfiguration("heartbeat_hz"), value_type=float
                        ),
                        "action_timeout_sec": 0.2,
                    }
                ],
            ),
            Node(
                package="litevla_bridge",
                executable="command_recorder",
                name="litevla_command_recorder",
                output="screen",
                parameters=[{"use_sim_time": True, "enabled": True, "source": "teleop"}],
            ),
            Node(
                package="litevla_bridge",
                executable="teleop_keyboard",
                name="litevla_teleop_keyboard",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": True,
                        "control_mode": "teleop",
                        "poll_hz": 50.0,
                        "hold_sec": 0.12,
                    }
                ],
            ),
        ]
    )
