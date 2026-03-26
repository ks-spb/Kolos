"""Data models for launcher runtime state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from subprocess import Popen
from typing import Optional


@dataclass
class ProcessSpec:
    """Description of an executable Python target."""

    name: str
    script_path: Path


@dataclass
class ManagedProcess:
    """Runtime process container for one script."""

    spec: ProcessSpec
    process: Optional[Popen] = None

    def is_running(self) -> bool:
        """Return True when process exists and is alive."""
        return self.process is not None and self.process.poll() is None

