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
            DeclareLaunchArgument("heartbeat_hz", default_value="10.0"),
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
                        "use_sim_time": True,
                        "control_mode": "teleop",
                        "require_frame": False,
                        "heartbeat_hz": ParameterValue(
                            LaunchConfiguration("heartbeat_hz"), value_type=float
                        ),
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
                parameters=[{"use_sim_time": True, "control_mode": "teleop"}],
            ),
        ]
    )
