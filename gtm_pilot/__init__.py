"""gtm-pilot: a guided menu for gputaskman."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _source_version() -> str | None:
    """The version in pyproject.toml when running from a source checkout.

    An editable install runs the code from the checkout but records the
    version only when it is installed, so after a version bump it would
    report the old one until reinstalled. Reading pyproject.toml keeps
    --version right. A wheel install has no pyproject.toml beside the
    package, so this returns None there."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        import tomllib

        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    except (OSError, ValueError):
        return None
    return project.get("version") if project.get("name") == "gtm-pilot" else None


try:
    __version__ = _source_version() or version("gtm-pilot")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0"
