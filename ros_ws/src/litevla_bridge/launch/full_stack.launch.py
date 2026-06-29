"""Launch full Lite-VLA robot stack for Epic 102 integration demo (VLA-28)."""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def _launch_nodes(context, *args, **kwargs):
    package_dir = get_package_share_directory("litevla_bridge")
    control_mode = LaunchConfiguration("control_mode").perform(context)
    nodes = [
        Node(
            package="litevla_bridge",
            executable="heartbeat_controller",
            name="litevla_heartbeat_controller",
            output="screen",
            parameters=[
                {
                    "control_mode": control_mode,
                    "heartbeat_hz": ParameterValue(
                        LaunchConfiguration("heartbeat_hz"), value_type=float
                    ),
                }
            ],
        ),
        Node(
            package="litevla_bridge",
            executable="camera_subscriber",
            name="litevla_camera_subscriber",
            output="screen",
            parameters=[{"record_frames": False}],
        ),
    ]
    if control_mode == "dummy":
        nodes.append(
            Node(
                package="litevla_bridge",
                executable="dummy_action_generator",
                name="litevla_dummy_action_generator",
                output="screen",
                parameters=[
                    {
                        "control_mode": "dummy",
                        "sequence_step_sec": ParameterValue(
                            LaunchConfiguration("sequence_step_sec"), value_type=float
                        ),
                    }
                ],
            )
        )
    if control_mode == "teleop":
        nodes.append(
            Node(
                package="litevla_bridge",
                executable="command_recorder",
                name="litevla_command_recorder",
                output="screen",
                parameters=[{"enabled": True, "source": "teleop"}],
            )
        )
    return nodes


def generate_launch_description() -> LaunchDescription:
    package_dir = get_package_share_directory("litevla_bridge")
    return LaunchDescription(
        [
            DeclareLaunchArgument("control_mode", default_value="dummy", description="dummy | teleop | model"),
            DeclareLaunchArgument("heartbeat_hz", default_value="10.0"),
            DeclareLaunchArgument("sequence_step_sec", default_value="2.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([package_dir, "launch", "webots_sim.launch.py"])
                ),
            ),
            OpaqueFunction(function=_launch_nodes),
        ]
    )
