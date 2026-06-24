"""Webots launch helpers for Lite-VLA interactive teleop."""

from __future__ import annotations

from launch.substitutions import TextSubstitution
from webots_ros2_driver.webots_launcher import WebotsLauncher


class InteractiveWebotsLauncher(WebotsLauncher):
    """WebotsLauncher without ``--batch`` so the GUI tracks the robot during teleop."""

    def __init__(self, *args, interactive: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if interactive:
            self._drop_batch_flag()

    def _drop_batch_flag(self) -> None:
        executable = self._ExecuteLocal__process_description  # noqa: SLF001
        executable._Executable__cmd = [  # noqa: SLF001
            part
            for part in executable._Executable__cmd  # noqa: SLF001
            if not (
                len(part) == 1
                and isinstance(part[0], TextSubstitution)
                and part[0].text == "--batch"
            )
        ]
