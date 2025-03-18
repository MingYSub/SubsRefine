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


def add_config_arguments(parser):
    # ProcessingConfig
    parser.add_argument("--merge-strategy", "-m", type=MergeStrategy, choices=list(MergeStrategy))
    parser.add_argument("--filter-interjections", "-fi", action=argparse.BooleanOptionalAction, default=None)

    # OutputSettings
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output-format", type=OutputFormat, choices=list(OutputFormat))
    parser.add_argument("--output-ending", type=str)
    parser.add_argument("--show-speaker", "-a", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--show-pause-tip", type=int)

    # FullHalfConversion
    parser.add_argument("--full-half-numbers", type=ConversionStrategy, choices=list(ConversionStrategy))
    parser.add_argument("--full-half-letters", type=ConversionStrategy, choices=list(ConversionStrategy))
    parser.add_argument("--convert-half-katakana", action=argparse.BooleanOptionalAction, default=None)

    # CJKSpacing
    parser.add_argument("--cjk-spacing", action=argparse.BooleanOptionalAction, dest="cjk_spacing_enabled",
                        default=None)
    parser.add_argument("--cjk-space-char", type=str)

    # RepetitionHandling
    parser.add_argument("--repetition-adjustment", "-r", action=argparse.BooleanOptionalAction,
                        dest="repetition_enabled", default=None)
    parser.add_argument("--repetition-connector", type=str)


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
