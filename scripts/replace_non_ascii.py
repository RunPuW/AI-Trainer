"""
Replace non-ASCII characters in Python files.

Loads translations from scripts/translations.json to avoid
inline Chinese characters being modified by linters.

Usage:
    python scripts/replace_non_ascii.py --dry-run
    python scripts/replace_non_ascii.py --apply
    python scripts/replace_non_ascii.py --apply --preserve-strings
"""

import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Tuple


SCRIPT_DIR = Path(__file__).parent
TRANSLATIONS_PATH = SCRIPT_DIR / "translations.json"


def load_translations() -> Dict[str, str]:
    """Load translations from JSON file."""
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_in_string(line: str, pos: int) -> bool:
    """Check if position is inside a string literal."""
    in_single = False
    in_double = False
    in_triple_single = False
    in_triple_double = False

    i = 0
    while i < pos:
        if i + 2 < len(line):
            triple = line[i:i+3]
            if triple == "'''":
                in_triple_single = not in_triple_single
                i += 3
                continue
            if triple == '"""':
                in_triple_double = not in_triple_double
                i += 3
                continue

        char = line[i]
        if char == "'" and not in_double and not in_triple_double:
            in_single = not in_single
        elif char == '"' and not in_single and not in_triple_single:
            in_double = not in_double

        i += 1

    return in_single or in_double or in_triple_single or in_triple_double


def process_file(
    file_path: Path,
    translations: Dict[str, str],
    dry_run: bool = True,
    preserve_strings: bool = True,
) -> List[Tuple[int, str, str]]:
    """Process a single file to replace non-ASCII characters."""
    changes = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ERROR] Cannot read {file_path}: {e}")
        return changes

    # Sort translations by key length (longest first) for proper replacement
    sorted_translations = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    new_lines = []
    for i, line in enumerate(lines):
        new_line = line

        # Check if line contains non-ASCII
        if not any(ord(c) > 127 for c in line):
            new_lines.append(line)
            continue

        # Preserve encoding declarations
        if i < 3 and ('coding' in line or 'encoding' in line):
            new_lines.append(line)
            continue

        # Replace Chinese everywhere except string literals (if preserve_strings)
        for chinese, english in sorted_translations:
            if chinese in new_line:
                pos = new_line.find(chinese)
                while pos != -1:
                    if not (preserve_strings and is_in_string(new_line, pos)):
                        new_line = new_line[:pos] + english + new_line[pos + len(chinese):]
                    pos = new_line.find(chinese, pos + len(english))

        if new_line != line:
            changes.append((i + 1, line.rstrip(), new_line.rstrip()))

        new_lines.append(new_line)

    # Write changes
    if not dry_run and changes:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"[ERROR] Cannot write {file_path}: {e}")

    return changes


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in directory."""
    python_files = []
    for path in root_dir.rglob("*.py"):
        if "__pycache__" in str(path) or ".git" in str(path):
            continue
        python_files.append(path)
    return sorted(python_files)


def main():
    parser = argparse.ArgumentParser(
        description="Replace non-ASCII characters in Python files"
    )
    parser.add_argument("--root", default=".", help="Root directory to process")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to files")
    parser.add_argument("--preserve-strings", action="store_true", default=True, help="Preserve string literals")
    parser.add_argument("--translate-strings", action="store_true", help="Also translate strings")

    args = parser.parse_args()

    if args.translate_strings:
        args.preserve_strings = False

    if not args.dry_run and not args.apply:
        print("Please specify --dry-run or --apply")
        return

    translations = load_translations()
    print(f"Loaded {len(translations)} translations from {TRANSLATIONS_PATH}")

    root_dir = Path(args.root)
    python_files = find_python_files(root_dir)

    print(f"\nFound {len(python_files)} Python files to process")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"Preserve strings: {args.preserve_strings}")
    print("-" * 60)

    total_changes = 0
    files_with_changes = 0

    for file_path in python_files:
        changes = process_file(
            file_path,
            translations,
            dry_run=args.dry_run,
            preserve_strings=args.preserve_strings,
        )

        if changes:
            files_with_changes += 1
            total_changes += len(changes)

            try:
                rel_path = file_path.relative_to(root_dir)
            except ValueError:
                rel_path = file_path

            print(f"\n{rel_path}:")
            for line_num, original, modified in changes[:5]:
                print(f"  L{line_num}: {original[:60]}... -> {modified[:60]}...")

            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more changes")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files with changes: {files_with_changes}")
    print(f"  Total changes: {total_changes}")

    if args.dry_run:
        print(f"\nRun with --apply to apply changes")


if __name__ == "__main__":
    main()
