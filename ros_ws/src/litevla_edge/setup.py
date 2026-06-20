from setuptools import setup

package_name = "litevla_edge"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (
            f"share/{package_name}/launch",
            [
                "launch/sim_camera_dummy.launch.py",
                "launch/turtlesim_dummy.launch.py",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="rach.dev",
    maintainer_email="rach.dev@example.com",
    description="Minimal LiteVLA-Edge ROS 2 prototype.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "dummy_controller = litevla_edge.dummy_controller:main",
        ],
    },
)
