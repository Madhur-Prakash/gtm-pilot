<div align="center">

# gtm-pilot

<p>A guided terminal interface for <a href="https://github.com/shanselman/gputaskman">gputaskman</a>.</p>


  [![PyPI version](https://img.shields.io/pypi/v/gtm-pilot.svg?logo=pypi&label=gtm-pilot%20on%20PyPI)](https://pypi.org/project/gtm-pilot/)
  [![PyPI Downloads](https://static.pepy.tech/personalized-badge/gtm-pilot?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/gtm-pilot)
  ![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
  ![License](https://img.shields.io/badge/License-MIT-green)
  ![Builds with Textual](https://img.shields.io/badge/built%20with-Textual-6f42c1.svg)
  ![Backend: gputaskman](https://img.shields.io/badge/backend-gputaskman-24292f.svg)


  ![GPU Monitoring](https://img.shields.io/badge/GPU-Monitoring-2ea44f.svg)
  ![Terminal TUI](https://img.shields.io/badge/Interface-Terminal%20TUI-6f42c1.svg)
  ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-555.svg)

<p><a href="https://pypi.org/project/gtm-pilot/">View on PyPI</a></p>

</div>

gtm-pilot brings live GPU monitoring, snapshots, recordings, summaries, replays, and
before-and-after comparisons into one focused menu. It runs the `gputaskman` executable
already installed on your machine and presents its output without changing measurements,
labels, process names, or `n/a` values.

gtm-pilot is an unofficial companion. It is not part of or affiliated with gputaskman.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Data files](#data-files)
- [How it works](#how-it-works)
- [Development](#development)
- [License](#license)

## Features

- GPU selection from a detected adapter list.
- Live View with configurable refresh intervals.
- One-shot GPU snapshots.
- Time-based or manually stopped recording sessions.
- Live recording sample counts and progress.
- Recording summaries and offline replays.
- Before-and-after measurements for model loads and scripts.
- Comparisons between saved JSON snapshots.
- Recent-file browsing with path autocomplete.
- Cross-platform sessions-folder opening.
- Keyboard shortcuts and a built-in key reference.
- Compatibility detection for older gputaskman installations.
- Explicit error messages when gputaskman is missing or a command fails.

## Requirements

- Python 3.11 or newer.
- [gputaskman](https://github.com/shanselman/gputaskman), available as `gputaskman`
  or `gtm` on `PATH`.
- A terminal that supports Textual applications.

gtm-pilot does not install gputaskman automatically. It uses the executable you provide or
the first compatible executable it discovers.

## Installation

### Install gputaskman

Install a released version with uv:

```powershell
uv tool install gputaskman
```

For the newest commands, install from source:

```powershell
uv tool install --force git+https://github.com/shanselman/gputaskman
```

gtm-pilot uses the `summary` and `replay` commands. Run the following to check the
commands provided by your installation:

```powershell
gputaskman --help
```

### Install gtm-pilot

Install the published tool:

```powershell
uv tool install gtm-pilot
```

Or install the current checkout:

```powershell
git clone https://github.com/Madhur-Prakash/gtm-pilot
cd gtm-pilot
pip install -e .
```

The editable install keeps source changes available immediately during development.

## Usage

Start the application:

```powershell
gtm-pilot
```

You can also start the package module directly:

```powershell
python -m gtm_pilot
```

### Menu actions

| Key | Action | Description |
|---|---|---|
| `l` | Live View | Opens gputaskman's full-screen monitor. |
| `s` | Snapshot | Captures one reading for a selected GPU. |
| `n` | Record Session | Records GPU usage to a JSONL file. |
| `u` | Summarize Recording | Summarizes a saved recording. |
| `p` | Replay Recording | Replays a recording offline. |
| `m` | Measure a Change | Captures before and after snapshots, then runs a diff. |
| `c` | Compare Snapshots | Diffs two saved snapshots. |
| `g` | List GPUs | Displays GPU indexes and adapter details. |
| `o` | Open Sessions Folder | Opens the folder containing saved data. |
| `r` | Refresh GPUs | Refreshes the detected GPU list. |
| `?` | Show Keys | Opens the complete keyboard reference. |
| `q` | Quit | Exits gtm-pilot. |

### Keyboard reference

| Context | Keys | Action |
|---|---|---|
| Menu | Arrow keys, `Enter` | Navigate and select |
| Forms | `Tab`, `Shift+Tab`, `Enter`, `Esc` | Move, submit, or cancel |
| File picker | `Tab` or `Right Arrow` | Complete the current path |
| File picker | `Down Arrow` | Move from the path field to the list |
| File picker | `Enter` | Open a file or enter a folder |
| Recording | `s` or `Esc` | Stop recording |
| Output | Arrow keys, `Page Up`, `Page Down` | Scroll output |
| Output | `Esc`, `q`, `Enter` | Return to the menu |
| Anywhere | `Ctrl+P` | Open Textual's command palette |
| Anywhere | `Ctrl+Q` | Quit |

## Configuration

| Command-line option | Environment variable | Default |
|---|---|---|
| `--sessions DIR` | `GTM_PILOT_SESSIONS` | `~/gpu-sessions` |
| `--gputaskman PATH` | `GTM_PILOT_GPUTASKMAN` | `gputaskman`, then `gtm` on `PATH` |

Examples:

```powershell
gtm-pilot --sessions D:\gpu-runs
gtm-pilot --gputaskman D:\tools\gputaskman.exe
```

Command-line options take precedence over environment variables. Additional options:

```powershell
gtm-pilot --help
gtm-pilot --version
```

## Data files

Saved data defaults to:

```text
~/gpu-sessions
```

On Windows, this typically resolves to:

```text
C:\Users\<username>\gpu-sessions
```

Recordings use `.jsonl` files:

```text
session_2026-11-13_21-18.jsonl
```

Measurements use paired `.json` files:

```text
llama3.1-8b_2026-11-13_21-10_before.json
llama3.1-8b_2026-11-13_21-10_after.json
```

File behavior:

- Existing recordings are appended to by gputaskman.
- Snapshots are never overwritten.
- Repeated measurements receive `-2`, `-3`, and later suffixes.
- Measurement labels are made filesystem-safe and limited to 40 characters.
- File pickers show recent files first, with folders before matching files.
- Path matching is case-insensitive and preserves the separator style being typed.
- Hidden files are shown only when the typed name begins with a dot.

Review recordings and snapshots before sharing them. They may contain process names,
paths, command lines, and model names from gputaskman's JSON output.

## Compatibility and error handling

gtm-pilot discovers gputaskman in this order:

1. The path passed with `--gputaskman`.
2. `GTM_PILOT_GPUTASKMAN`.
3. `gputaskman` on `PATH`.
4. `gtm` on `PATH`.
5. The default `~/.local/bin` tool location.

The application checks `gputaskman --help` for the `diff`, `record`, `summary`, and
`replay` commands. Actions unavailable in the installed version are disabled with an
explanation.

If gputaskman cannot be found, gtm-pilot shows installation guidance. Press `r` after
installing it to search again. If a command fails, its error output is displayed instead
of being silently discarded.

## How it works

- gtm-pilot does not read GPU data directly or add monitoring probes.
- Every measurement comes from the installed gputaskman executable.
- Text-producing commands run away from the UI thread and appear in scrollable output pages.
- Live View and Replay hand the terminal to gputaskman's own full-screen interface.
- Record Session counts complete samples as they are written.
- On Linux and macOS, stopping a recording sends `SIGINT`.
- On Windows, stopping a background recording terminates its process after finished samples
  have been preserved.
- Windows captured commands run without opening an extra console window.

## Development

The package uses a root-level `gtm_pilot/` layout and Hatchling as its build backend.

```powershell
pip install -e .
python -m unittest discover -s tests
uv build
```

Project layout:

```text
gtm_pilot/
  cli.py            command-line entry point
  app.py            Textual application and action dispatch
  gputaskman.py     executable discovery and command execution
  commands.py       gputaskman argument builders
  sessions.py       session paths and filenames
  pathcomplete.py   file-picker autocomplete
  pilot.tcss        Textual styles
  screens/          application screens and dialogs
tests/              unit and UI tests using a fake gputaskman
```

## License

gtm-pilot is released under the [MIT License](LICENSE).

gputaskman is a separate project by Scott Hanselman and remains under its own license.
