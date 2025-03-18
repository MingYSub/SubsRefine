import logging
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum, StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)


def dict_to_dataclass(cls, data: dict):
    if data is None:
        return None
    field_types = {f.name: f.type for f in fields(cls)}
    kwargs = {}
    for name, value in data.items():
        if name not in field_types:
            continue
        field_type = field_types[name]

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            kwargs[name] = field_type(value)
        elif is_dataclass(field_type):
            kwargs[name] = dict_to_dataclass(field_type, value)
        else:
            kwargs[name] = value
    return cls(**kwargs)


class MergeStrategy(StrEnum):
    """Options for handling duplicate lines merging"""
    NONE = "none"
    AUTO = "auto"
    FORCE = "force"


class ConversionStrategy(StrEnum):
    """Character conversion options for numbers/letters"""
    SKIP = "skip"
    HALF = "half"
    FULL = "full"
    SINGLE_FULL = "single_full"  # Full-width if single, half-width otherwise


class OutputFormat(StrEnum):
    """Supported output file formats"""
    TXT = "txt"
    SRT = "srt"
    ASS = "ass"


@dataclass
class OutputSettings:
    """Configuration for output formatting"""
    dir: Path | None = None
    format: OutputFormat = OutputFormat.TXT
    ending: str = ""  # String appended to each sentence end
    show_speaker: bool = False
    show_pause_tip: int = 0


@dataclass
class FullHalfConversion:
    """Full-width/Half-width character conversion settings"""
    numbers: ConversionStrategy = ConversionStrategy.HALF
    letters: ConversionStrategy = ConversionStrategy.HALF
    convert_half_katakana: bool = True


@dataclass
class CJKSpacing:
    """Spacing rules between CJK and Western characters"""
    enabled: bool = False
    space_char: str = "\u2006"


@dataclass
class RepetitionHandling:
    """Settings for handling repeated syllables"""
    enabled: bool = True
    connector: str = "… "  # String to connect repeated syllables


@dataclass
class Mapping:
    text: dict[str, str] = field(default_factory=dict)
    regex: dict[str, str] = field(default_factory=dict)


@dataclass
class ProcessingConfig:
    merge_strategy: MergeStrategy = MergeStrategy.AUTO
    filter_interjections: bool = True
    output: OutputSettings = field(default_factory=OutputSettings)
    full_half_conversion: FullHalfConversion = field(default_factory=FullHalfConversion)
    cjk_spacing: CJKSpacing = field(default_factory=CJKSpacing)
    repetition_adjustment: RepetitionHandling = field(default_factory=RepetitionHandling)
    mapping: Mapping = field(default_factory=Mapping)

    @classmethod
    def from_yaml(cls, path: Path | str, encoding: str = "utf-8") -> "ProcessingConfig":
        import yaml

        with open(path, "r", encoding=encoding) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessingConfig":
        return dict_to_dataclass(cls, data)
