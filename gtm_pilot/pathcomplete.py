"""Path completion for the file picker: what can follow the text typed so far.

Matching ignores case (Windows paths do), but completions keep each entry's
real name and the user's own separator style (C:/ or C:\\).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from textual.suggester import Suggester


@dataclass(frozen=True)
class Match:
    path: Path
    name: str
    is_dir: bool
    # The full input text that picks this entry; folders end with a separator
    # so the next keystroke lists what is inside
    text: str


def separator(value: str) -> str:
    """Keep the separator the user is already typing"""
    if "\\" in value:
        return "\\"
    if "/" in value:
        return "/"
    return os.sep


def split(value: str, base: Path) -> tuple[Path, str, str]:
    """(folder to list, partial name being typed, typed text before it).
    Relative paths are under base (the sessions folder)."""
    cut = max(value.rfind("/"), value.rfind("\\")) + 1
    prefix, partial = value[:cut], value[cut:]

    if not prefix:
        return base, partial, prefix

    folder = Path(os.path.expanduser(prefix))
    if not folder.is_absolute():
        folder = base / folder
    return folder, partial, prefix


def matches(value: str, base: Path, suffixes: tuple[str, ...] = (), limit: int = 50) -> list[Match]:
    """Folders, then files ending in one of suffixes, whose names start with
    what is typed. Hidden entries only when the typed name starts with '.'."""
    folder, partial, prefix = split(value, base)

    try:
        entries = list(os.scandir(folder))
    except OSError:  # missing folder, no permission, not a folder
        return []

    sep = separator(value)
    typed = partial.casefold()
    wanted = tuple(s.casefold() for s in suffixes)
    show_hidden = partial.startswith(".")
    dirs: list[Match] = []
    files: list[Match] = []

    for entry in entries:
        name = entry.name
        if not name.casefold().startswith(typed):
            continue
        if name.startswith(".") and not show_hidden:
            continue

        try:
            is_dir = entry.is_dir()
        except OSError:
            continue

        if is_dir:
            dirs.append(Match(Path(entry.path), name, True, prefix + name + sep))
        elif not wanted or name.casefold().endswith(wanted):
            files.append(Match(Path(entry.path), name, False, prefix + name))

    def by_name(m: Match) -> str:
        return m.name.casefold()

    return (sorted(dirs, key=by_name) + sorted(files, key=by_name))[:limit]


def complete(value: str, base: Path, suffixes: tuple[str, ...] = ()) -> str | None:
    """Tab completion: the one match in full, or as much as all matches share.
    None when there is nothing to add."""
    found = matches(value, base, suffixes, limit=10_000)
    if not found:
        return None
    if len(found) == 1:
        return found[0].text

    _, partial, prefix = split(value, base)
    shared = os.path.commonprefix([m.name.casefold() for m in found])
    if len(shared) > len(partial):
        return prefix + found[0].name[: len(shared)]
    return None


def suffixes_for(pattern: str) -> tuple[str, ...]:
    """'*.jsonl' -> ('.jsonl',); anything else matches every file"""
    if pattern.startswith("*.") and not any(c in pattern[1:] for c in "*?["):
        return (pattern[1:],)
    return ()


class PathSuggester(Suggester):
    """Grey inline completion in the path box (→ or Tab accepts it)"""

    def __init__(self, base: Path, suffixes: tuple[str, ...]):
        # case_sensitive keeps the typed text as-is; matching itself ignores case.
        # No cache: the folder can change while the picker is open.
        super().__init__(use_cache=False, case_sensitive=True)
        self.base = base
        self.suffixes = suffixes

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None
        found = matches(value, self.base, self.suffixes, limit=1)
        return found[0].text if found else None
