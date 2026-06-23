"""Unit tests for litevla_bridge (no ROS runtime required)."""

from litevla_bridge import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"
