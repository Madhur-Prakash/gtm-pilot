# gtm-pilot

A guided menu for [gputaskman](https://github.com/shanselman/gputaskman): live view, snapshots,
recordings, summaries, replays and before/after diffs, without remembering any flags.

> **Unofficial companion.** gtm-pilot is not part of gputaskman and isn't affiliated with it. It
> runs the `gputaskman` you already have installed and shows its output as-is, so every reading,
> label and `n/a` is exactly what gputaskman reports.

## Why

gputaskman's commands are powerful, but each one has its own flags:

```text
gputaskman -i 2 --gpu 0
gputaskman record -o session.jsonl --gpu 0 --interval 5 --duration 300
gputaskman --json --gpu 0 > before.json   # ...load a model...
gputaskman --json --gpu 0 > after.json
gputaskman diff before.json after.json
gputaskman summary session.jsonl
```

gtm-pilot puts them behind one menu. You pick the GPU from a list, choose intervals and durations
from presets, and it names and keeps the files for you.

## Install

You need two tools: **gputaskman**, which reads the GPU, and **gtm-pilot**, the menu. Both
install with [uv](https://docs.astral.sh/uv/getting-started/installation/), and each can be
installed either way below.

### 1. gputaskman

gtm-pilot uses gputaskman's `summary` and `replay` commands. They were added to gputaskman's
`main` branch after v0.4.1, so until a release includes them, build gputaskman from source.

**Install with uv tool** (once a release has `summary` and `replay`):

```powershell
uv tool install gputaskman
```

**Build from source** (has the newest commands today):

```powershell
git clone https://github.com/shanselman/gputaskman
uv tool install --force ./gputaskman
```

Or in one step, without keeping a clone:

```powershell
uv tool install --force git+https://github.com/shanselman/gputaskman
```

Check that it has the newer commands: `gputaskman --help` should mention `summary` and `replay`.
If gtm-pilot can't find gputaskman at all, it opens on an error screen with these install
steps. Install gputaskman, then press `r` there to look again; the menu opens once it's found.
With an older gputaskman, gtm-pilot still starts. The actions that version can't do are greyed
out, with a note saying which command is missing.

### 2. gtm-pilot

**Install with uv tool:**

```powershell
uv tool install gtm-pilot
```

**Build from source:**

```powershell
git clone https://github.com/Madhur-Prakash/gtm-pilot
cd gtm-pilot
uv build                       # optional: makes the wheel and sdist in dist/
uv tool install --force .
```

To update later, run `uv tool upgrade gtm-pilot`. For a source install, run `git pull`, then
`uv tool install --force .` again.

## Use

```powershell
gtm-pilot
```

| Key | Action | What it runs |
|---|---|---|
| `l` | **Live View** | `gputaskman -i N [--gpu N]`, gputaskman's own full-screen monitor (press `q` to come back) |
| `s` | **Snapshot** | `gputaskman --once --gpu N` |
| `n` | **Record Session** | `gputaskman record -o FILE --gpu N -i N [--duration N] [--no-system]` with a live sample count and a Stop button, then the summary |
| `u` | **Summarize Recording** | `gputaskman summary FILE` |
| `p` | **Replay Recording** | `gputaskman replay FILE`, offline playback (press `q` to come back) |
| `m` | **Measure a Change** | `--json` snapshot, waits while you load a model or start a script, a second snapshot, then `gputaskman diff` |
| `c` | **Compare Snapshots** | `gputaskman diff BEFORE AFTER` on two snapshots saved earlier |
| `g` | **List GPUs** | `gputaskman --list-gpus` |
| `o` | **Open Sessions Folder** | Opens the folder in Explorer, Finder or your file manager |

### Keys

On the menu, press an action's key, or use the arrow keys and Enter. `r` refreshes the GPU list,
`?` shows every key, and `q` quits. `Esc` goes back or cancels anywhere, and `Ctrl+P` opens
Textual's command palette (themes and more).

When you pick a recording or snapshot, the list shows recent files. You can also type a path,
with autocomplete:

- a grey suggestion appears as you type; `Tab` or `→` accepts it
- the list switches to what matches, with folders first, then files of the right type
- `↓` moves into the list, and choosing a folder opens it so you can keep typing

### Files

Recordings and snapshots go to `~/gpu-sessions` (for example `C:\Users\you\gpu-sessions`).
Names are readable and sort together:

```text
session_2026-11-13_21-18.jsonl                 # Record Session (you can type any name)
llama3.1-8b_2026-11-13_21-10_before.json       # Measure a Change, named after what you measure
llama3.1-8b_2026-11-13_21-10_after.json
```

Recording into an existing file adds a new run to it; `gputaskman summary` reports each run
separately. Snapshots are never overwritten: a second measurement with the same name in the
same minute gets `-2`, `-3`, and so on.

Recordings and snapshots hold the same process names, paths, command lines and model names as
gputaskman's `--json` output. Review them before you share them.

### Options

| Option | Environment variable | Default |
|---|---|---|
| `--sessions DIR` | `GTM_PILOT_SESSIONS` | `~/gpu-sessions` |
| `--gputaskman PATH` | `GTM_PILOT_GPUTASKMAN` | `gputaskman` (or `gtm`) on `PATH` |

```powershell
gtm-pilot --sessions D:\gpu-runs
```

## How it works

- gtm-pilot reads nothing from the GPU and adds no probes. Every action is one gputaskman
  command.
- Commands with text output (snapshot, diff, summary, GPU list) run in the background, and their
  output is shown in a scrollable page.
- Live View and Replay hand the terminal to gputaskman's own full-screen view, then return to the
  menu when you quit it.
- Record Session runs `gputaskman record` in the background and counts the samples as they're
  written. **Stop** ends it. gputaskman flushes every sample as it goes, so all finished samples
  are kept. On Linux and macOS, Stop sends Ctrl+C. On Windows, where a background process can't
  get one, it ends the process.

Built with [Textual](https://textual.textualize.io/), the same UI library gputaskman uses, so
installing both adds nothing new.

## Development

The package uses the root-level `gtm_pilot/` layout. Both regular and editable installs
are supported, so edits are available immediately during development.

```powershell
pip install -e .
gtm-pilot
python -m unittest discover -s tests
uv build
```

```text
gtm_pilot/          installed as gtm_pilot
  cli.py            command line: finds gputaskman, starts the app
  app.py            the Textual app: one method per menu action
  gputaskman.py     finding and running gputaskman, parsing --list-gpus and --help
  commands.py       the gputaskman argument list behind each action
  sessions.py       sessions folder, file names, opening the folder
  pathcomplete.py   path autocomplete for the file picker
  pilot.tcss        styles
  screens/
    menu.py         main menu and its shortcut keys
    keys.py         the ? page listing every key
    missing.py      shown when gputaskman isn't found
    forms.py        option dialogs (GPU, seconds, yes/no, text)
    files.py        recording / snapshot picker with path autocomplete
    output.py       scrollable command output
    record.py       recording progress and stop
    measure.py      before / after / diff
tests/              unittest; UI tests use a fake gputaskman, so no GPU is needed
```

## License

MIT. gputaskman is a separate project by Scott Hanselman under its own MIT license.
