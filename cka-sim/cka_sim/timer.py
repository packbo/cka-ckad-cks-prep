"""Simple timers: per-question and global (exam)."""
from __future__ import annotations

import time


class Timer:
    def __init__(self) -> None:
        self.start = time.time()

    def elapsed(self) -> float:
        return time.time() - self.start

    def fmt(self) -> str:
        s = int(self.elapsed())
        return f"{s // 60:02d}:{s % 60:02d}"


def fmt_seconds(sec: float) -> str:
    s = int(sec)
    return f"{s // 60:02d}:{s % 60:02d}"
