from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("image_topic", default_value="/image_raw"),
            DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
            DeclareLaunchArgument("wait_seconds", default_value="45.0"),
            LogInfo(
                msg=(
                    "Start Webots first: ./ros_ws/scripts/run_webots_mvp.sh "
                    "(requires Webots + ros-jazzy-webots-ros2)"
                )
            ),
            Node(
                package="litevla_bridge",
                executable="spawn_verifier",
                name="litevla_spawn_verifier",
                output="screen",
                parameters=[
                    {
                        "image_topic": LaunchConfiguration("image_topic"),
                        "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                        "wait_seconds": LaunchConfiguration("wait_seconds"),
                        "publish_test_cmd": True,
                    }
                ],
            ),
        ]
    )
