"""Launch Webots MVP and drive robot to save Purshottam reference PNGs."""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    output_dir = LaunchConfiguration("output_dir")
    startup_wait = LaunchConfiguration("startup_wait_sec")

    webots = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("litevla_bridge"), "launch", "webots_sim.launch.py"]
            )
        )
    )

    capture = Node(
        package="litevla_bridge",
        executable="reference_frame_capture",
        name="litevla_reference_frame_capture",
        output="screen",
        parameters=[
            {
                "output_dir": output_dir,
                "startup_wait_sec": startup_wait,
                "ready_timeout_sec": 120.0,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "output_dir",
                default_value="data/reference_images",
                description="Directory for red_cone_*.png and stop_barrier_close.png",
            ),
            DeclareLaunchArgument(
                "startup_wait_sec",
                default_value="3.0",
                description="Seconds to settle after /odom and /image_raw appear",
            ),
            webots,
            capture,
        ]
    )
