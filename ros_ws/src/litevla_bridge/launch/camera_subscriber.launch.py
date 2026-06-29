"""Launch camera subscriber node (VLA-24)."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("image_topic", default_value="/image_raw"),
            DeclareLaunchArgument("record_frames", default_value="false"),
            DeclareLaunchArgument("frame_save_dir", default_value="outputs/frames"),
            DeclareLaunchArgument("record_interval_sec", default_value="1.0"),
            Node(
                package="litevla_bridge",
                executable="camera_subscriber",
                name="litevla_camera_subscriber",
                output="screen",
                parameters=[
                    {
                        "image_topic": LaunchConfiguration("image_topic"),
                        "record_frames": ParameterValue(
                            LaunchConfiguration("record_frames"), value_type=bool
                        ),
                        "frame_save_dir": LaunchConfiguration("frame_save_dir"),
                        "record_interval_sec": ParameterValue(
                            LaunchConfiguration("record_interval_sec"), value_type=float
                        ),
                    }
                ],
            ),
        ]
    )
