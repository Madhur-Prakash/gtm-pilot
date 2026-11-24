# Changelog

All notable changes to gtm-pilot are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.1.1...HEAD)

### Fixed

- `gtm-pilot --version` run from a source checkout (an editable install) now reports the
  version in `pyproject.toml`, instead of the one it had when it was installed.

## [1.1.1](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.1.0...v1.1.1) - 2026-11-24

Resume Recording now continues a recording exactly as it was started.

### Fixed

- **Resume Recording could change a recording's settings.** The form let you pick a different
  GPU, sampling interval or system RAM/CPU setting, which mixed two kinds of samples in one
  file. These are now fixed to the original settings and shown at the top of the form; only
  how much longer to record is asked.
- **Older recordings resumed at 1 s.** Recordings made before 1.1.0, or by gputaskman
  directly, had no saved settings, so the form fell back to a 1 s interval even for a
  recording taken every 10 s. gtm-pilot now works out the interval from the samples' own
  timestamps (a pause in between doesn't throw it off), the GPU from its name, and whether
  system RAM/CPU was recorded.

## [1.1.0](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.0.3...v1.1.0) - 2026-11-24

Pause and resume recordings.

### Added

- **Pause and resume a recording while it runs.** Record Session has a Pause button, and
  `p` or `Space` toggle it. Pausing ends the current `gputaskman record` run cleanly, so
  every finished sample is kept and nothing is sampled while paused. Resuming appends to the
  same file. A timed recording resumes for the time it has left, so paused time doesn't count
  towards its duration. The status line shows the recorded time (paused time excluded), how
  long it has been paused, and how many pauses there have been.
- **Resume Recording** (`e` on the menu) continues any saved recording, even one from an
  earlier gtm-pilot session, appending to the same file. The form is filled in with the GPU,
  interval and system RAM/CPU setting the recording was started with.
- **`--resume FILE`** on the command line opens Resume Recording for that file at start-up.
  It accepts a path, or a recording name in the sessions folder with or without `.jsonl`.
- gtm-pilot now saves the settings each recording starts with in `.gtm-pilot-recordings` in
  the sessions folder.

### Changed

- The recording summary says how many times the recording was paused, and how to add to it
  later.
- Forms can start on a given GPU and on an interval that isn't one of the presets.

## [1.0.3](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.0.2...v1.0.3) - 2026-11-19

Fixes dialogs and pages that ran off a small terminal.

### Fixed

- **Record Session: the file name could not be typed.** On a terminal around 30 rows the form
  was taller than the screen, so the File name box and the Cancel / Start recording buttons
  were drawn past the bottom edge with no way to reach them. Dialogs now cap their scrolling
  part to the room the rest of the dialog leaves, so the bottom is always on screen.
- The file picker, the `?` keys page, the Record and Measure pages and the "gputaskman not
  found" page did the same on short terminals: the buttons, the last fields and the install
  commands are now reachable, scrolling when they have to.
- Long titles and field questions no longer run off the side of a narrow dialog, and dialog
  buttons stack one per line when there isn't room for them side by side.
- Dialogs re-fit themselves when the terminal is resized.

## [1.0.2](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.0.1...v1.0.2) - 2026-11-16

Dependency and documentation update.

- gputaskman is now installed automatically as a runtime dependency of gtm-pilot.
- Documented that gputaskman can also be installed separately for standalone use or
  newer source commands.
- Clarified the README description of gputaskman as gtm-pilot's backend.

## [1.0.1](https://github.com/Madhur-Prakash/gtm-pilot/compare/v1.0.0...v1.0.1) - 2026-11-15

Packaging and documentation fixes. No changes to the app.

- PyPI classifier now says **Production/Stable** (was Alpha), and lists Python 3.11 to 3.14.
- README Python badge now says **3.11+**, matching `requires-python` (it said 3.8+).
- This changelog now names gtm-pilot.

---

## [1.0.0](https://github.com/Madhur-Prakash/gtm-pilot/releases/tag/v1.0.0) - 2026-11-15

First stable release.

- Menu for gputaskman's live view, snapshot, record, summary, replay, diff and `--list-gpus`.
- Forms with GPU picker and interval/duration presets (or a custom number of seconds).
- Record Session with a live sample count, progress for timed recordings, a Stop button, and
  the summary afterwards.
- Measure a Change: before snapshot, pause, after snapshot, diff, with files named after what
  you measure.
- One-key shortcuts for every menu action (shown in the footer and the list), and a `?` page
  listing every key.
- Path autocomplete in the file picker: inline suggestion (Tab or → accepts) and a live list
  of matching folders and files.
- Actions an installed gputaskman can't do yet are greyed out instead of failing.
- If gputaskman isn't found, an error screen shows how to install it (uv tool or from source),
  and `r` looks again. If gputaskman is found but fails, the menu says why.
- `--sessions` / `GTM_PILOT_SESSIONS` and `--gputaskman` / `GTM_PILOT_GPUTASKMAN`.
- Root-level `gtm_pilot` package layout with support for editable installation using
  `pip install -e .`.
- Refreshed project documentation with installation, configuration, keyboard, data-file,
  compatibility, and development guidance.
