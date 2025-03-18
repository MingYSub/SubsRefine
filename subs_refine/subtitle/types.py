from dataclasses import dataclass
from itertools import takewhile


class Timecode(int):
    def __new__(cls, time: str | int):
        if isinstance(time, int):
            return super().__new__(cls, time)

        time = time.replace(",", ".")

        if ":" in time and "." in time:
            hours, minutes, seconds_ms = time.split(":")
            seconds, milliseconds = seconds_ms.split(".")
            total_ms = (
                    int(hours) * 3600000 +
                    int(minutes) * 60000 +
                    int(seconds) * 1000 +
                    int(milliseconds.ljust(3, "0"))
            )
            return super().__new__(cls, total_ms)

        raise ValueError(f"Invalid time format: {time}")

    def __repr__(self):
        return f"Timecode({int(self)})"

    def __str__(self):
        return self.to_ass_string()

    def to_ass_string(self) -> str:
        total_seconds, milliseconds = divmod(self, 1000)
        total_minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"[:-1]

    def to_srt_string(self) -> str:
        total_seconds, milliseconds = divmod(self, 1000)
        total_minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


@dataclass(frozen=True)
class Position:
    x: int
    y: int


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    @classmethod
    def parse(cls, color_str: str):
        color_str = color_str.upper().lstrip("&H").lstrip(" \t")
        color_str = "".join(takewhile(lambda x: x in "0123456789ABCDEF", color_str))
        value = int(color_str, 16)
        if value > 0xFFFFFF:
            return cls(255, 255, 255)
        r = value & 0xFF
        g = (value >> 8) & 0xFF
        b = (value >> 16) & 0xFF
        return cls(r, g, b)

    def to_ass_string(self):
        return f"&H{self.b:02X}{self.g:02X}{self.r:02X}&"

    def __repr__(self):
        return f"Color({self.to_ass_string()})"
