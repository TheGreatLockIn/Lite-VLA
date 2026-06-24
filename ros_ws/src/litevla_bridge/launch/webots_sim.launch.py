#!/usr/bin/env python3
"""Launch Webots MVP arena with litevla_robot (VLA-23)."""

from __future__ import annotations

import os
from pathlib import Path

import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.wait_for_controller_connection import WaitForControllerConnection

from litevla_bridge.webots_launcher import InteractiveWebotsLauncher


def _launch_setup(context: LaunchContext) -> list[launch.Action]:
    package_dir = get_package_share_directory("litevla_bridge")
    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")
    interactive = LaunchConfiguration("interactive").perform(context).lower() in {
        "1",
        "true",
        "yes",
    }

    # Must stay a LaunchConfiguration so WebotsLauncher.execute() can redirect
    # to its temp copy (with Ros2Supervisor appended).
    world_path = PathJoinSubstitution([package_dir, "worlds", world])
    if interactive:
        webots = InteractiveWebotsLauncher(
            world=world_path,
            mode="realtime",
            ros2_supervisor=True,
        )
    else:
        webots = WebotsLauncher(
            world=world_path,
            mode="realtime",
            ros2_supervisor=True,
        )

    robot_description_path = os.path.join(package_dir, "resource", "litevla_robot.urdf")
    robot_description = Path(robot_description_path).read_text(encoding="utf-8")
    ros2_control_params = os.path.join(package_dir, "resource", "ros2_control.yml")

    use_twist_stamped = os.environ.get("ROS_DISTRO", "") in {"jazzy", "kilted", "rolling"}
    if use_twist_stamped:
        cmd_vel_remapping = ("/diffdrive_controller/cmd_vel", "/cmd_vel")
    else:
        cmd_vel_remapping = ("/diffdrive_controller/cmd_vel_unstamped", "/cmd_vel")

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": use_sim_time,
            }
        ],
    )

    robot_driver = WebotsController(
        robot_name="litevla_robot",
        parameters=[
            {
                "robot_description": robot_description_path,
                "use_sim_time": use_sim_time,
                "set_robot_state_publisher": False,
            },
            ros2_control_params,
        ],
        remappings=[
            cmd_vel_remapping,
            ("/diffdrive_controller/odom", "/odom"),
            ("/image_raw/image_color", "/image_raw"),
        ],
        respawn=True,
    )

    controller_manager_timeout = ["--controller-manager-timeout", "120"]
    prefix = "python.exe" if os.name == "nt" else ""

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        prefix=prefix,
        arguments=["joint_state_broadcaster"] + controller_manager_timeout,
        parameters=[{"use_sim_time": use_sim_time}],
    )
    diffdrive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        prefix=prefix,
        arguments=["diffdrive_controller"] + controller_manager_timeout,
        parameters=[{"use_sim_time": use_sim_time}],
    )

    waiting_nodes = WaitForControllerConnection(
        target_driver=robot_driver,
        nodes_to_start=[joint_state_broadcaster_spawner],
    )

    spawn_diffdrive_after_joint = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[diffdrive_controller_spawner],
        )
    )

    shutdown_on_webots_exit = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=webots,
            on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
        )
    )

    return [
        LogInfo(msg="Lite-VLA Webots MVP — expect /image_raw and /cmd_vel after driver starts"),
        webots,
        webots._supervisor,
        robot_state_publisher,
        robot_driver,
        waiting_nodes,
        spawn_diffdrive_after_joint,
        shutdown_on_webots_exit,
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value="mvp_arena.wbt"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument(
                "interactive",
                default_value="false",
                description="Drop Webots --batch so the GUI camera follows the robot",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
