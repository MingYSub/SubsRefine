import logging
from collections.abc import Sequence
from dataclasses import dataclass

from .types import Timecode, Position, Color

logger = logging.getLogger(__name__)


@dataclass
class Dialog:
    start: Timecode
    end: Timecode
    text: str
    style: str = "Default"
    name: str = ""
    pos: Position | None = None
    color: Color | None = None

    def to_ass_string(self, actor: bool = False, ending_char: str = "") -> str:
        return f"Dialogue: 0,{self.start},{self.end},Default,{self.name if actor else ''},0,0,0,," +\
            self.text.replace('\n', '\\N') + ending_char


class Events(list[Dialog]):
    def pop(self, index: int | Sequence[int] = -1) -> None:
        if isinstance(index, int):
            index = (index,)
        for i in sorted(index, reverse=True):
            super().pop(i)

    def to_ass_string(self, show_speaker: bool = False, ending_char: str = "") -> str:
        return "\n".join(l.to_ass_string(show_speaker, ending_char) for l in self)

    def to_srt_string(self, show_speaker: bool = False, ending_char: str = "") -> str:
        result = []
        for i, line in enumerate(self):
            result.append(
                "%d\n%s --> %s\n%s%s%s\n"
                % (
                    i + 1,
                    line.start.to_srt_string(),
                    line.end.to_srt_string(),
                    f"{{{line.name}}}" if show_speaker and line.name else "",
                    line.text,
                    ending_char,
                )
            )
        return "\n".join(result)
