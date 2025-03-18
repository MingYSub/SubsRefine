import logging
import re
from pathlib import Path

from .events import Dialog, Events
from .types import Timecode, Position, Color
from ..config import OutputSettings
from ..constants import ASS_HEADER

__all__ = (
    "Subtitle",
    "load",
    "from_text",
)

logger = logging.getLogger(__name__)

OVERRIDE_BLOCK_PATTERN = re.compile(r"(?<!\\){([^}]*)}")


class Subtitle:
    def __init__(self):
        self.res_x = 960
        self.res_y = 540
        self.events = Events()

    @classmethod
    def load(cls, path: Path | str, encoding: str = "utf-8") -> "Subtitle":
        path = Path(path)

        if path.suffix == ".ass":
            return cls.from_ass_text(path.open("r", encoding=encoding).read())

        if path.suffix == ".srt":
            return cls.from_srt_text(path.open("r", encoding=encoding).read())

        if path.suffix == ".vtt":
            return cls.from_vtt_text(path.open("r", encoding=encoding).read())

        raise ValueError(f"Format not supported: {path.suffix}")

    @classmethod
    def from_text(cls, text: str) -> "Subtitle":
        if "-->" in text:
            return cls.from_vtt_text(text)
        return cls.from_ass_text(text)

    @classmethod
    def from_ass_text(cls, text: str) -> "Subtitle":
        def parse_ass_dialog(line: str) -> Dialog:
            splits = line.split(",", 9)

            start = Timecode(splits[1].strip())
            end = Timecode(splits[2].strip())
            style = splits[3].strip()
            name = splits[4].strip()
            text = splits[9].replace("\\N", "\n").strip()

            if "\\fscx50\\fscy50" in text:
                style = "Rubi"

            pos_match = re.search(r"\\pos\((\d+),(\d+)\)", text)
            pos = Position(*map(int, pos_match.groups())) if pos_match else Position(0, 0)

            text = re.sub(r"{([^}]*)\\c&[0-9a-fhA-FH]([^}]*)}(\s*{\\c&[0-9a-fhA-FH][^}]*})", r"{\1\2}\3", text)
            color_match = re.search(r"\\c([&hH0-9a-fA-F]+?)(?=[\\}])", text)
            color = Color.parse(color_match.group(1)) if color_match else Color(255, 255, 255)

            text = OVERRIDE_BLOCK_PATTERN.sub("", text)

            return Dialog(start, end, text, style, name, pos, color)

        doc = cls()
        lines = text.strip().splitlines()
        for line in lines:
            if line.startswith("Dialogue:"):
                doc.events.append(parse_ass_dialog(line))
            elif "ResX:" in line:
                try:
                    doc.res_x = int(re.search(r"ResX: ?(\d+)", line).group(1))
                except ValueError:
                    logger.warning("PlayResX is not a number")
            elif "ResY:" in line:
                try:
                    doc.res_y = int(re.search(r"ResY: ?(\d+)", line).group(1))
                except ValueError:
                    logger.warning("PlayResY is not a number")
        return doc


    @classmethod
    def from_srt_text(cls, text: str) -> "Subtitle":
        return cls.from_vtt_text(text)

    @classmethod
    def from_vtt_text(cls, text: str) -> "Subtitle":
        cue_pattern = re.compile(r"(?:^|.*\n).*?((?:\d+:)?\d{2}:\d{2}[.,]\d{2,3} +--> +(?:\d+:)?\d{2}:\d{2}[.,]\d{2,3}).*?\n")

        doc = cls()
        splits = cue_pattern.split(text.strip())
        for time_str, text in zip(splits[1::2], splits[2::2]):
            start, end = map(Timecode, time_str.split(" --> "))
            text = text.replace("&lrm;", "").replace("\u200e", "")
            text = text.replace("\u202a", "").replace("\u202c", "").strip()
            doc.events.append(Dialog(start, end, text))

        return doc

    def to_ass(self, show_speaker: bool = False, ending_char: str = "") -> str:
        return ASS_HEADER + self.events.to_ass_string(show_speaker, ending_char)

    def to_srt(self, show_speaker: bool = False, ending_char: str = "") -> str:
        return self.events.to_srt_string(show_speaker, ending_char)

    def to_txt(self, show_speaker: bool = False, ending_char: str = "", show_pause_tip: int = 0) -> str:
        result = []
        last_end = 0
        for event in self.events:
            if event.start - last_end >= show_pause_tip * 1000 > 0:
                result.append(f"({(event.start - last_end) // 1000}-second pause)")
            last_end = event.end
            text = event.text.replace("\n", "\u3000")
            result.append(
                f"[{event.name}]\t{text}{ending_char}"
                if show_speaker
                else f"{text}{ending_char}"
            )
        return "\n".join(result)

    def save(self, path: Path | str, config: OutputSettings | None = None) -> None:
        config = config or OutputSettings()
        path = Path(path)
        if path.suffix == ".ass":
            text = self.to_ass(config.show_speaker, config.ending)
        elif path.suffix == ".srt":
            text = self.to_srt(config.show_speaker, config.ending)
        elif path.suffix == ".txt":
            text = self.to_txt(config.show_speaker, config.ending, config.show_pause_tip)
        else:
            raise ValueError(f"Invalid format: {path.suffix}")

        encoding = "utf-8-sig" if path.suffix == ".ass" else "utf-8"
        with open(path, "w", encoding=encoding) as f:
            f.write(text)

    def __repr__(self) -> str:
        return f"Subtitle(with {len(self.events)} events)"


load = Subtitle.load
from_text = Subtitle.from_text
