#!/usr/bin/env python3
"""Launch Webots MVP arena with litevla_robot (VLA-23)."""

from __future__ import annotations

import os

import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.wait_for_controller_connection import WaitForControllerConnection


def generate_launch_description() -> LaunchDescription:
    package_dir = get_package_share_directory("litevla_bridge")
    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    webots = WebotsLauncher(
        world=PathJoinSubstitution([package_dir, "worlds", world]),
        mode="realtime",
        ros2_supervisor=True,
    )

    robot_description_path = os.path.join(package_dir, "resource", "litevla_robot.urdf")
    ros2_control_params = os.path.join(package_dir, "resource", "ros2_control.yml")

    use_twist_stamped = os.environ.get("ROS_DISTRO", "") in {"jazzy", "kilted", "rolling"}
    if use_twist_stamped:
        cmd_vel_remapping = ("/diffdrive_controller/cmd_vel", "/cmd_vel")
    else:
        cmd_vel_remapping = ("/diffdrive_controller/cmd_vel_unstamped", "/cmd_vel")

    robot_driver = WebotsController(
        robot_name="litevla_robot",
        parameters=[
            {
                "robot_description": robot_description_path,
                "use_sim_time": use_sim_time,
                "set_robot_state_publisher": True,
            },
            ros2_control_params,
        ],
        remappings=[
            cmd_vel_remapping,
            ("/diffdrive_controller/odom", "/odom"),
            # webots_ros2 publishes {topicName}/image_color; remap to project /image_raw
            ("/image_raw/image_color", "/image_raw"),
        ],
        respawn=True,
    )

    controller_manager_timeout = ["--controller-manager-timeout", "60"]
    prefix = "python.exe" if os.name == "nt" else ""

    diffdrive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        prefix=prefix,
        arguments=["diffdrive_controller"] + controller_manager_timeout,
        parameters=[{"use_sim_time": use_sim_time}],
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        prefix=prefix,
        arguments=["joint_state_broadcaster"] + controller_manager_timeout,
        parameters=[{"use_sim_time": use_sim_time}],
    )

    waiting_nodes = WaitForControllerConnection(
        target_driver=robot_driver,
        nodes_to_start=[diffdrive_controller_spawner, joint_state_broadcaster_spawner],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value="mvp_arena.wbt"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            LogInfo(msg="Lite-VLA Webots MVP — expect /image_raw and /cmd_vel after driver starts"),
            webots,
            webots._supervisor,
            robot_driver,
            waiting_nodes,
            launch.actions.RegisterEventHandler(
                event_handler=launch.event_handlers.OnProcessExit(
                    target_action=webots,
                    on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
                )
            ),
        ]
    )
