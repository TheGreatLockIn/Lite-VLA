from setuptools import find_packages, setup

package_name = "litevla_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/config",
            ["config/bridge_params.yaml", "config/webots_sim.yaml"],
        ),
        (
            "share/" + package_name + "/launch",
            [
                "launch/verify_spawn.launch.py",
                "launch/webots_sim.launch.py",
                "launch/camera_subscriber.launch.py",
                "launch/cmd_vel_test.launch.py",
                "launch/dummy_sim.launch.py",
                "launch/heartbeat.launch.py",
                "launch/full_stack.launch.py",
                "launch/teleop_sim.launch.py",
                "launch/reference_capture.launch.py",
            ],
        ),
        ("share/" + package_name + "/worlds", ["worlds/mvp_arena.wbt"]),
        (
            "share/" + package_name + "/resource",
            ["resource/litevla_robot.urdf", "resource/ros2_control.yml"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Raj Dangi",
    maintainer_email="dangiprince263@gmail.com",
    description="Lite-VLA ROS 2 control bridge package.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "workspace_ping = litevla_bridge.workspace_ping:main",
            "spawn_verifier = litevla_bridge.spawn_verifier:main",
            "camera_subscriber = litevla_bridge.camera_subscriber:main",
            "cmd_vel_publisher = litevla_bridge.cmd_vel_publisher:main",
            "cmd_vel_tester = litevla_bridge.cmd_vel_tester:main",
            "dummy_action_generator = litevla_bridge.dummy_action_generator:main",
            "heartbeat_controller = litevla_bridge.heartbeat_controller:main",
            "teleop_keyboard = litevla_bridge.teleop_keyboard:main",
            "command_recorder = litevla_bridge.command_recorder:main",
            "reference_frame_capture = litevla_bridge.reference_frame_capture:main",
        ],
    },
)
