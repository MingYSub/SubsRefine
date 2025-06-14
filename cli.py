import argparse
import logging
from dataclasses import asdict
from itertools import chain
from pathlib import Path

from subs_refine import SCRIPT_VERSION, Processor
from subs_refine.config import ProcessingConfig, ConversionStrategy, OutputFormat, MergeStrategy


def main():
    parser = argparse.ArgumentParser(description=f"SubsRefine {SCRIPT_VERSION} | Process Japanese subtitles")
    parser.add_argument("--conf", type=Path, default=Path(__file__).parent / "config.yaml",
                        help="Configuration file path")
    parser.add_argument("path", nargs="+", type=Path, help="Input files/directories")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    add_config_arguments(parser)
    args = parser.parse_args()

    logger = logging.getLogger("subs_refine")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    config = ProcessingConfig.from_yaml(args.conf) if args.conf.exists() else ProcessingConfig()
    override_dict = build_override_dict(args)
    config = merge_config(config, override_dict)

    if args.verbose:
        console_handler.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler("SubsRefine.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug("Configuration:\n%s", asdict(config))
    else:
        console_handler.setLevel(logging.WARNING)

    process_paths(args.path, config)


def add_boolean_pair(parser, flag: str, dest: str, help_text: str = ""):
    parser.add_argument(f"-{flag}", action="store_true", dest=dest, default=None,
                        help=f"Enable {help_text}".strip())
    parser.add_argument(f"-{flag.upper()}", action="store_false", dest=dest, default=None,
                        help=f"Disable {help_text}".strip())


def add_config_arguments(parser):
    # ProcessingConfig
    parser.add_argument(
        "-m", "--merge-strategy",
        type=MergeStrategy, choices=list(MergeStrategy),
        help="Strategy for merging overlapping time-aligned lines"
    )
    add_boolean_pair(parser, "i", "filter_interjections", "interjection filtering")

    # OutputSettings
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        help="Directory to store output files"
    )
    parser.add_argument(
        "-f", "--output-format",
        type=OutputFormat, choices=list(OutputFormat),
        help="Output file format (e.g., txt, srt, json)"
    )
    parser.add_argument(
        "-e", "--output-ending",
        type=str,
        help="String to append at the end of each line"
    )
    add_boolean_pair(parser, "s", "show_speaker", "speaker name display")
    parser.add_argument(
        "-p", "--show-pause-tip",
        type=int,
        help="Show pause tip if pause exceeds this duration (in milliseconds)"
    )

    # FullHalfConversion
    parser.add_argument(
        "--numbers",
        type=ConversionStrategy, choices=list(ConversionStrategy), dest="full_half_numbers",
        help="Conversion strategy for full-width/half-width numbers"
    )
    parser.add_argument(
        "--letters",
        type=ConversionStrategy, choices=list(ConversionStrategy), dest="full_half_letters",
        help="Conversion strategy for full-width/half-width letters"
    )
    add_boolean_pair(parser, "k", "convert_half_katakana", "conversion of half-width katakana to full-width")

    # CJKSpacing
    add_boolean_pair(parser, "c", "cjk_spacing_enabled", "automatic spacing between CJK and latin characters")
    parser.add_argument(
        "--cjk-space-char",
        type=str,
        help="Custom space character to insert between CJK and latin characters"
    )

    # RepetitionHandling
    add_boolean_pair(parser, "r", "repetition_enabled", "adjustment of repeated phrases")
    parser.add_argument(
        "--repetition-connector",
        type=str,
        help="Connector used between repeated syllables"
    )



def build_override_dict(args) -> dict:
    override = {}
    arg_dict = vars(args)

    mapping = {
        "merge_strategy": ["merge_strategy"],
        "filter_interjections": ["filter_interjections"],
        "output_dir": ["output", "dir"],
        "output_format": ["output", "format"],
        "output_ending": ["output", "ending"],
        "show_speaker": ["output", "show_speaker"],
        "show_pause_tip": ["output", "show_pause_tip"],
        "full_half_numbers": ["full_half_conversion", "numbers"],
        "full_half_letters": ["full_half_conversion", "letters"],
        "convert_half_katakana": ["full_half_conversion", "convert_half_katakana"],
        "cjk_spacing_enabled": ["cjk_spacing", "enabled"],
        "cjk_space_char": ["cjk_spacing", "space_char"],
        "repetition_enabled": ["repetition_adjustment", "enabled"],
        "repetition_connector": ["repetition_adjustment", "connector"],
    }

    for arg_name, path in mapping.items():
        value = arg_dict.get(arg_name)
        if value is not None:
            current = override
            for key in path[:-1]:
                current = current.setdefault(key, {})
            current[path[-1]] = value

    return override


def merge_config(config: ProcessingConfig, override: dict) -> ProcessingConfig:
    config_dict = asdict(config)

    def deep_merge(target, updates):
        for k, v in updates.items():
            if isinstance(v, dict):
                node = target.setdefault(k, {})
                deep_merge(node, v)
            else:
                target[k] = v

    deep_merge(config_dict, override)
    return ProcessingConfig.from_dict(config_dict)


def get_all_files_from_dir(paths: Path) -> list[Path]:
    return [
        path for path in chain(paths.glob("*.ass"), paths.glob("*.srt"), paths.glob("*.vtt"))
        if path.is_file() and not path.stem.endswith("_processed")
    ]


def process_paths(paths: list[Path], config: ProcessingConfig):
    processor = Processor(config)
    files = sorted(set(p for path in paths for p in (get_all_files_from_dir(path) if path.is_dir() else [path])))

    total = len(files)
    if total == 0:
        print("No files found to process.")
        return

    total_files_width = len(str(total))
    processed_count = 0

    for file in files:
        processed_count += 1
        print(f"\rProcessing: [{processed_count:0{total_files_width}}/{total}] {file.name}")
        try:
            processor(file)
        except Exception as e:
            print(f"Failed: {e}")


if __name__ == "__main__":
    main()
