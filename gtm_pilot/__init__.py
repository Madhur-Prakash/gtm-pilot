"""gtm-pilot: a guided menu for gputaskman."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gtm-pilot")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0"
