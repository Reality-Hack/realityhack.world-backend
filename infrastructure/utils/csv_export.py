import csv
from collections.abc import Iterable, Mapping
from pathlib import Path


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[Mapping[str, str]],
    *,
    encoding: str = "utf-8",
) -> None:
    """Write a CSV file with a header row followed by the given rows."""
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_multiselect_values(value: object) -> list[str]:
    """Parse a MultiSelectField value into a list of stored keys.

    Handles list values (already parsed), comma-separated strings, and empty/None.
    """
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [v.strip() for v in str(value).split(",") if v.strip()]


def choice_label(choices: Iterable[tuple[str, str]], key: str) -> str:
    """Return the human-readable label for a choice key, or the key as a fallback."""
    for choice_key, label in choices:
        if choice_key == key:
            return str(label)
    return key
