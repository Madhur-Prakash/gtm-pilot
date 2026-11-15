# Changelog

All notable changes to gtm-pilot are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.1](https://github.com/Madhur-Prakash/gtm-pilot/releases/tag/v1.0.1) - 2026-11-15

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
