import logging
from collections import defaultdict
from enum import StrEnum
from itertools import chain
from pathlib import Path
from typing import overload, Sequence

from .config import ProcessingConfig, MergeStrategy, FullHalfConversion
from .subtitle import Subtitle, Events, Dialog
from .subtitle.types import Color, Position
from .text_processing import *

__all__ = (
    "Processor",
    "SubtitleType",
)

logger = logging.getLogger(__name__)

WHITE = Color(255, 255, 255)

AUDIO_MARKERS = ("♪♪", "♪", "♬", "⚟", "⚞", "📱", "☎", "🔊", "📢", "📺", "🎤",
                 "💻", "🎧", "📼", "🖭", "・", "〓", "⎚", "＝", "", "≫", ">>")
PARENTHESIS_START_MARKERS = ("<", "＜", "《", "｟", "≪", "〈", "［", "（（", "⟨")
PARENTHESIS_END_MARKERS = (">", "＞", "》", "｠", "≫", "〉", "］", "））", "⟩")
CONTINUOUS_LINE_MARKERS = ("→", "➡", "⤵️", "➥", "・")

TV_EXCLUSIVE_MARKERS = ("♪♪", "⚟", "⚞", "📱", "☎", "🔊", "📢", "📺", "🎤", "💻", "🎧", "📼", "🖭", "〓", "⎚", "＝",
                        "≫", ">>", "｟", "（（", "→", "➡", "⤵️", "➥", "・～", "・(", "・（", "｡", "[外:")
TV_SPLIT_PATTERN = re.compile(f"\u3000(?=[(（{''.join(chain(AUDIO_MARKERS, PARENTHESIS_START_MARKERS))}])"
                              f"|(?<=[{''.join(PARENTHESIS_END_MARKERS)}])\u3000")


class SubtitleType(StrEnum):
    TV_ASS = "tv_ass"
    TV_SRT = "tv_srt"
    WEB = "web"


def remove_affix(text: str, prefix: Sequence[str] | None = None, suffix: Sequence[str] | None = None) -> str:
    if prefix is not None:
        for p in prefix:
            text = text.removeprefix(p)
    if suffix is not None:
        for s in suffix:
            text = text.removesuffix(s)
    return text


def remove_line_markers(text: str) -> str:
    return remove_affix(text, PARENTHESIS_START_MARKERS + ("～",), PARENTHESIS_END_MARKERS + CONTINUOUS_LINE_MARKERS)


def guess_same_speaker(event1, event2, x_spacing=60, y_spacing=60) -> bool:
    return (event1.start == event2.start and event1.end == event2.end
            and event1.color == event1.color
            and event1.pos.y and event2.pos.y
            and (event1.pos.y == event2.pos.y
                 or abs(event1.pos.x - event2.pos.x) <= x_spacing
                 and abs(event1.pos.y - event2.pos.y) <= y_spacing
                 )
            )


def filter_empty_lines(doc: Subtitle) -> None:
    doc.events = Events(event for event in doc.events if event.text not in ("", "～"))


def full_half_conversion(doc: Subtitle, conversion: FullHalfConversion, raw: str = "", converted: str = ""):
    trans = str.maketrans(raw, converted)
    for event in doc.events:
        event.text = convert_half_full_numbers(event.text, conversion.numbers)
        event.text = convert_half_full_letters(event.text, conversion.letters)
        event.text = event.text.translate(trans)
    if conversion.convert_half_katakana:
        for event in doc.events:
            event.text = convert_half_katakana(event.text)


def _tv_text_preprocessing(doc: Subtitle) -> None:
    for event in doc.events:
        # remove audio markers
        if event.text.startswith(AUDIO_MARKERS):
            event.text = event.text[1:]
        event.text = event.text.replace("\u3000\u3000", "\u3000").strip()
        # handle gaiji
        event.text = re.sub(r"\[外：[0-9A-Z]{32}]", "", event.text)


def tv_ass_process(doc: Subtitle, config: ProcessingConfig) -> None:
    def set_speakers(doc: Subtitle) -> None:
        speaker_record = defaultdict(set)

        x_spacing = int(60 * doc.res_x / 960)
        y_spacing = int(60 * doc.res_y / 540)

        none_speaker_count = 1
        same_speaker_flag = False

        for index, event in enumerate(doc.events):
            speaker = None
            text_stripped = remove_line_markers(event.text)

            # Find the specific speaker
            if text_stripped.startswith("（") and "）" in text_stripped:
                speaker_tmp = re.search(r"（(.*?)）", text_stripped).group(1)
                if text_stripped[len(speaker_tmp) + 2:].strip() or index + 1 < len(doc.events) and guess_same_speaker(
                        event, doc.events[index + 1], x_spacing, y_spacing):
                    speaker = speaker_tmp.strip().removesuffix("の声")
                    if "：" in speaker:
                        speaker = speaker[speaker.index("："):].strip()
                    same_speaker_flag = False
            elif "：" in text_stripped:
                speaker = text_stripped[:text_stripped.index("：")].strip()
                same_speaker_flag = False
            elif "≫" in text_stripped:
                speaker = text_stripped[:text_stripped.index("≫")].strip()
                same_speaker_flag = False

            if event.color != WHITE:
                # Set the speaker based on the color
                if event.color not in speaker_record or speaker and speaker not in speaker_record[event.color]:
                    logger.debug(f"Speaker found for {event.color}: {speaker}")
                speaker_record[event.color].add(speaker or "")
                speaker = event.color.to_ass_string()
            else:
                # Set the speaker based on parentheses or coordinates
                text = event.text
                if same_speaker_flag or index > 0 and doc.events[index - 1].text.endswith(CONTINUOUS_LINE_MARKERS):
                    speaker = doc.events[index - 1].name
                if text.startswith(PARENTHESIS_START_MARKERS):
                    same_speaker_flag = True
                if text.endswith(PARENTHESIS_END_MARKERS):
                    same_speaker_flag = False
                if not speaker and not same_speaker_flag and index > 0:
                    last_event = doc.events[index - 1]
                    if guess_same_speaker(event, last_event, x_spacing, y_spacing):
                        speaker = last_event.name

            if speaker:
                event.name = speaker
            else:
                event.name = f"Unknown{none_speaker_count}"
                none_speaker_count += 1

        color_speaker_mapping = {
            color: max(speakers, key=len) or f"Protagonist{i + 1}"
            for i, (color, speakers) in enumerate(speaker_record.items())
        }

        for event in doc.events:
            if event.color in color_speaker_mapping:
                event.name = color_speaker_mapping[event.color]

    def merge_duplicate_lines_by_time(doc: Subtitle, strategy: MergeStrategy = MergeStrategy.AUTO) -> None:
        if strategy not in MergeStrategy:
            raise ValueError(f"Invalid strategy: {strategy}")

        if strategy == MergeStrategy.NONE:
            return

        del_list = []

        for index in range(len(doc.events) - 1):
            event = doc.events[index]
            next_event = doc.events[index + 1]
            if event.start == next_event.start and event.end == next_event.end:
                if event.name == next_event.name:
                    next_event.text = event.text + "\u3000" + next_event.text
                    del_list.append(index)
                elif strategy == MergeStrategy.FORCE:
                    next_event.name = event.name + "/" + next_event.name
                    next_event.text = event.text + "\n" + next_event.text
                    del_list.append(index)

        doc.events.pop(del_list)

    del_list = [index for index, event in enumerate(doc.events) if event.style == "Rubi"]
    doc.events.pop(del_list)
    logger.info(f"Removed {len(del_list)} Rubi events")

    raw = "!?．％／＆＋－＝･“”(): ｡。"
    converted = "！？.%/&+-=・「」（）：\u3000\u3000\u3000"
    full_half_conversion(doc, config.full_half_conversion, raw, converted)
    logger.info("Normalized full-width/half-width characters")

    _tv_text_preprocessing(doc)
    logger.info("Completed text preprocessing")

    set_speakers(doc)
    logger.info("Assigned speakers")

    for event in doc.events:
        event.text = remove_line_markers(event.text).strip()
        for marker in AUDIO_MARKERS:
            event.text = event.text.removeprefix(marker).strip()
        if event.text.startswith("（") and "）" in event.text:
            event.text = event.text[event.text.index("）") + 1:]
        elif not event.name.startswith("Unknown"):
            event.text = event.text.removeprefix(event.name + "：").removeprefix(event.name + "≫")
        for marker in AUDIO_MARKERS:
            event.text = event.text.removeprefix(marker).strip()
        event.text = remove_line_markers(event.text).strip()
        event.text = re.sub(r"(?<=[？！])(?![\u3000？！」』]|$)", "\u3000", event.text)
    filter_empty_lines(doc)
    logger.info("Cleaned up text")

    if config.merge_strategy != MergeStrategy.NONE:
        merge_duplicate_lines_by_time(doc, config.merge_strategy)
        logger.info("Merged duplicate lines based on timing")


def tv_srt_process(doc: Subtitle, config: ProcessingConfig) -> None:
    raw = "!?．％／＆＋－＝･“”:〜 ｡。\n"
    converted = "！？.%/&+-=・「」：～\u3000\u3000\u3000\u3000"
    full_half_conversion(doc, config.full_half_conversion, raw, converted)
    logger.info("Normalized full-width/half-width characters")

    new_events = []
    for event in doc.events:
        splits = TV_SPLIT_PATTERN.split(event.text)
        for text in splits:
            for marker in CONTINUOUS_LINE_MARKERS:
                text = text.replace(marker, "")
            text = text.strip()
            if text:
                new_events.append(Dialog(start=event.start, end=event.end, text=text))
    doc.events = Events(new_events)
    logger.info("Split events with special characters")

    _tv_text_preprocessing(doc)
    logger.info("Completed text preprocessing")

    for event in doc.events:
        event.text = re.sub(r"\(.*?\)", "", event.text)
        event.text = re.sub(r"（.*?）", "", event.text)
        event.text = re.sub(r"(?<=[？！])(?![\u3000？！」』]|$)", "\u3000", event.text)
        for marker in AUDIO_MARKERS:
            event.text = event.text.removeprefix(marker).strip()
        event.text = remove_line_markers(event.text).strip()
    filter_empty_lines(doc)
    logger.info("Cleaned up text")


def web_process(doc: Subtitle, config: ProcessingConfig) -> None:
    raw = "!?．％／＆＋－＝･“”:〜 ｡。\n"
    converted = "！？.%/&+-=・「」：～\u3000\u3000\u3000\u3000"
    full_half_conversion(doc, config.full_half_conversion, raw, converted)
    logger.info("Normalized full-width/half-width characters")

    new_events = []
    for event in doc.events:
        event.text = re.sub(r"<.*?>", "", event.text)
        event.text = re.sub(r"{.*?}", "", event.text)
        if "\u3000-" in event.text or "\u3000（" in event.text:
            splits = re.split("\u3000(?=[-（])", event.text)
            for text in splits:
                text = text.strip()
                if text:
                    new_events.append(Dialog(start=event.start, end=event.end, text=text))
        else:
            new_events.append(event)
    doc.events = Events(new_events)
    logger.info("Split events with special characters")

    prefixes = ("〈", "・～", "♪～", "♪")
    suffixes = ("〉", "～・", "～♪", "♪", "⸺")
    for event in doc.events:
        event.text = re.sub(r"\(.*?\)", "", event.text)
        event.text = re.sub(r"^〔.*?〕$", "", event.text)
        event.text = re.sub(r"^(?:- ?)?（.*?）", "", event.text)
        event.text = event.text.removeprefix("-").strip()
        event.text = re.sub(r"(?<=[？！])(?![\u3000？！」』]|$)", "\u3000", event.text)
        event.text = remove_affix(event.text, prefixes, suffixes)
    filter_empty_lines(doc)
    logger.info("Cleaned up text")

    del_list = []
    for index, event in enumerate(doc.events):
        if index == 0:
            continue
        last_event = doc.events[index - 1]
        if event.start == last_event.end and event.text == last_event.text:
            last_event.end = doc.events[index].end
            del_list.append(index)
    doc.events.pop(del_list)
    logger.info(f"Removed {len(del_list)} duplicate events")


class Processor:
    def __init__(self, config: ProcessingConfig | None = None):
        self.config = config or ProcessingConfig()

    def set_config(self, config: ProcessingConfig) -> None:
        self.config = config

    @overload
    def __call__(self, doc: Subtitle) -> None:
        ...

    @overload
    def __call__(self, path: Path | str) -> None:
        ...

    def __call__(self, doc_or_path: Subtitle | Path | str) -> None:
        if isinstance(doc_or_path, Subtitle):
            self.process_subtitle(doc_or_path)
        else:
            try:
                path = Path(doc_or_path)
                self.process_and_save(path)
            except Exception as e:
                logger.error(f"Error processing file {doc_or_path}: {e}")
                raise ValueError(f"Error processing file {doc_or_path}: {e}")

    def process_and_save(self, path: Path | str) -> None:
        logger.info(f"Starting processing {path}")
        path = Path(path)
        doc = Subtitle.load(path)
        self.process_subtitle(doc)
        output_filename = path.with_name(f"{path.stem}_processed.{self.config.output.format}").name
        output_dir = self.config.output.dir or path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        doc.save(output_path, self.config.output)
        logger.info(f"Finished processing. Saved to {output_path}")

    def process_subtitle(self, doc: Subtitle, type_: SubtitleType | str | None = None) -> None:
        logger.info("Starting subtitle processing...")

        if type_ is None:
            default_position = Position(0, 0)
            if any(event.pos is not None and event.pos != default_position for event in doc.events):
                type_ = SubtitleType.TV_ASS
            elif any(marker in event.text for event in doc.events for marker in TV_EXCLUSIVE_MARKERS):
                type_ = SubtitleType.TV_SRT
            else:
                type_ = SubtitleType.WEB
        else:
            try:
                type_ = SubtitleType(type_)
            except ValueError:
                logger.error(f"Invalid subtitle type {type_}")
                raise ValueError(f"Invalid subtitle type {type_}")

        logger.info(f"Detected subtitle type: {type_.value}")

        if type_ == SubtitleType.TV_ASS:
            tv_ass_process(doc, self.config)
        elif type_ == SubtitleType.TV_SRT:
            tv_srt_process(doc, self.config)
        elif type_ == SubtitleType.WEB:
            web_process(doc, self.config)

        for event in doc.events:
            event.text = re.sub("\u3000+", "\u3000", event.text).replace(
                "⁉", "!?").replace("⁈", "?!").replace("‼", "!!")

        if self.config.filter_interjections:
            for event in doc.events:
                event.text = filter_interjections(event.text)
            filter_empty_lines(doc)
            logger.info("Filtered interjections")

        if self.config.cjk_spacing.enabled:
            for event in doc.events:
                event.text = cjk_spacing(event.text, self.config.cjk_spacing.space_char)
            logger.info("Applied CJK spacing adjustments")

        if self.config.repetition_adjustment.enabled:
            for event in doc.events:
                event.text = adjust_repeated_syllables(event.text, self.config.repetition_adjustment.connector)
            logger.info("Adjusted repeated syllables")

        for event in doc.events:
            for key, value in self.config.mapping.text.items():
                event.text = event.text.replace(key, value)
            for pattern, replacement in self.config.mapping.regex.items():
                event.text = re.sub(pattern, replacement, event.text)
        logger.info(f"Finished custom text replacements")

        for event in doc.events:
            event.text = fix_western_text(event.text)
        logger.info(f"Fixed western text")

        logger.info("Subtitle processing completed successfully")
