#!/usr/bin/env python3
"""Validate i18n locale files for consistency.

Standalone CI script (stdlib only). Checks JSON syntax, file parity
between locale directories, key parity, empty values, and shared files.

Exit code 0 = all checks passed, 1 = at least one failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

__all__: list[str] = []

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = REPO_ROOT / "resources" / "i18n"
LOCALE_DIRS = ["en", "de"]
SHARED_FILES = ["emoji.json", "logs.json"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def flatten_keys(data: dict, prefix: str = "") -> set[str]:
    """Recursively flatten nested dict into dot-notation leaf keys.

    Args:
        data: Nested dictionary to flatten.
        prefix: Current key prefix for recursion.

    Returns:
        Set of dot-notation keys for all leaf values.
    """
    keys: set[str] = set()
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(flatten_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys


def find_empty_values(data: dict, prefix: str = "") -> list[str]:
    """Find all keys with empty string values.

    Args:
        data: Nested dictionary to check.
        prefix: Current key prefix for recursion.

    Returns:
        List of dot-notation keys that have empty string values.
    """
    empty: list[str] = []
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            empty.extend(find_empty_values(v, full_key))
        elif isinstance(v, str) and v == "":
            empty.append(full_key)
    return empty


# ---------------------------------------------------------------------------
# Validation passes
# ---------------------------------------------------------------------------


def pass_json_syntax() -> tuple[bool, list[str]]:
    """Pass 1: Verify all locale JSON files have valid syntax.

    Returns:
        Tuple of (success, list of error messages).
    """
    errors: list[str] = []
    file_count = 0

    # Shared files
    for name in SHARED_FILES:
        path = I18N_DIR / name
        if not path.exists():
            errors.append(f"  Missing shared file: {path}")
            continue
        file_count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"  {path}: {exc}")

    # Locale-specific files
    for locale in LOCALE_DIRS:
        locale_dir = I18N_DIR / locale
        if not locale_dir.is_dir():
            errors.append(f"  Missing locale directory: {locale_dir}")
            continue
        for json_file in sorted(locale_dir.glob("*.json")):
            file_count += 1
            try:
                json.loads(json_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"  {json_file}: {exc}")

    ok = len(errors) == 0
    if ok:
        return True, [f"[PASS] JSON syntax: {file_count}/{file_count} files valid"]
    return False, [
        f"[FAIL] JSON syntax: {len(errors)} error(s)",
        *errors,
    ]


def pass_file_parity() -> tuple[bool, list[str]]:
    """Pass 2: Verify en/ and de/ have matching filenames.

    Returns:
        Tuple of (success, list of status/error messages).
    """
    errors: list[str] = []
    locale_files: dict[str, set[str]] = {}

    for locale in LOCALE_DIRS:
        locale_dir = I18N_DIR / locale
        if not locale_dir.is_dir():
            errors.append(f"  Missing locale directory: {locale}")
            locale_files[locale] = set()
            continue
        locale_files[locale] = {f.name for f in locale_dir.glob("*.json")}

    if errors:
        return False, [f"[FAIL] File parity: {len(errors)} error(s)", *errors]

    # Compare each pair
    for i, loc_a in enumerate(LOCALE_DIRS):
        for loc_b in LOCALE_DIRS[i + 1 :]:
            only_a = locale_files[loc_a] - locale_files[loc_b]
            only_b = locale_files[loc_b] - locale_files[loc_a]
            if only_a:
                errors.append(f"  Only in {loc_a}/: {', '.join(sorted(only_a))}")
            if only_b:
                errors.append(f"  Only in {loc_b}/: {', '.join(sorted(only_b))}")

    if errors:
        return False, [
            f"[FAIL] File parity: {LOCALE_DIRS[0]}/ and" f" {LOCALE_DIRS[1]}/ differ",
            *errors,
        ]
    return True, [f"[PASS] File parity: {LOCALE_DIRS[0]}/ and" f" {LOCALE_DIRS[1]}/ have matching files"]


def pass_key_parity() -> tuple[bool, list[str]]:
    """Pass 3: Verify all keys in en/*.json exist in de/*.json and vice versa.

    Returns:
        Tuple of (success, list of status/error messages).
    """
    errors: list[str] = []
    ref_dir = I18N_DIR / LOCALE_DIRS[0]

    if not ref_dir.is_dir():
        return False, [f"[FAIL] Key parity: reference dir {ref_dir} missing"]

    for json_file in sorted(ref_dir.glob("*.json")):
        filename = json_file.name

        # Load reference locale
        try:
            ref_data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue  # Already caught in pass 1
        ref_keys = flatten_keys(ref_data)

        # Compare with each other locale
        for locale in LOCALE_DIRS[1:]:
            other_file = I18N_DIR / locale / filename
            if not other_file.exists():
                continue  # Already caught in pass 2

            try:
                other_data = json.loads(other_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            other_keys = flatten_keys(other_data)

            missing_in_other = ref_keys - other_keys
            missing_in_ref = other_keys - ref_keys

            if missing_in_other:
                errors.append(f"  {LOCALE_DIRS[0]}/{filename} vs" f" {locale}/{filename}")
                for key in sorted(missing_in_other):
                    errors.append(f"    Missing in {locale}: {key}")

            if missing_in_ref:
                errors.append(f"  {locale}/{filename} vs" f" {LOCALE_DIRS[0]}/{filename}")
                for key in sorted(missing_in_ref):
                    errors.append(f"    Missing in {LOCALE_DIRS[0]}: {key}")

    if errors:
        return False, [
            f"[FAIL] Key parity: {len(errors)} issue(s)",
            *errors,
        ]
    return True, ["[PASS] Key parity: all keys match across locales"]


def pass_no_empty_values() -> tuple[bool, list[str]]:
    """Pass 4: Check that no locale file contains empty string values.

    Returns:
        Tuple of (success, list of status/error messages).
    """
    errors: list[str] = []

    for locale in LOCALE_DIRS:
        locale_dir = I18N_DIR / locale
        if not locale_dir.is_dir():
            continue
        for json_file in sorted(locale_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            empty_keys = find_empty_values(data)
            if empty_keys:
                for key in empty_keys:
                    errors.append(f"  {locale}/{json_file.name}: empty value" f" for '{key}'")

    if errors:
        return False, [
            f"[FAIL] No empty values: {len(errors)} empty string(s) found",
            *errors,
        ]
    return True, ["[PASS] No empty values"]


def pass_shared_files() -> tuple[bool, list[str]]:
    """Pass 5: Validate shared files (emoji.json, logs.json) exist and parse.

    Returns:
        Tuple of (success, list of status/error messages).
    """
    errors: list[str] = []

    for name in SHARED_FILES:
        path = I18N_DIR / name
        if not path.exists():
            errors.append(f"  Missing: {name}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"  {name}: {exc}")
            continue

        if not isinstance(data, dict) or len(data) == 0:
            errors.append(f"  {name}: file is empty or not a dict")
            continue

        # Check for empty values in shared files too
        empty_keys = find_empty_values(data)
        if empty_keys:
            for key in empty_keys:
                errors.append(f"  {name}: empty value for '{key}'")

    if errors:
        return False, [
            f"[FAIL] Shared files: {len(errors)} issue(s)",
            *errors,
        ]
    return True, ["[PASS] Shared files valid"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all validation passes and report results.

    Returns:
        Exit code: 0 if all passes succeeded, 1 otherwise.
    """
    print("=== i18n Validation ===")  # noqa: T201

    passes = [
        pass_json_syntax,
        pass_file_parity,
        pass_key_parity,
        pass_no_empty_values,
        pass_shared_files,
    ]

    total_errors = 0
    for run_pass in passes:
        ok, messages = run_pass()
        for msg in messages:
            print(msg)  # noqa: T201
        if not ok:
            total_errors += 1

    print()  # noqa: T201
    if total_errors == 0:
        print("=== RESULT: PASS ===")  # noqa: T201
        return 0

    print(f"=== RESULT: FAIL ({total_errors}" f" error{'s' if total_errors != 1 else ''}) ===")  # noqa: T201
    return 1


if __name__ == "__main__":
    sys.exit(main())
