# Changelog

All notable changes to gtm-pilot are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

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
