# Changelog

## 0.1.0 (unreleased)

First version.

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
