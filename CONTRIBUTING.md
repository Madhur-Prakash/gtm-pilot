# Contributing to gtm-pilot

Thanks for helping improve gtm-pilot. This guide covers setting up a checkout, the rules the
code follows, testing, and how changes are released.

Related documents: [README](README.md) · [Changelog](CHANGELOG.md) · [Security policy](SECURITY.md) · [License](LICENSE)

## Contents

- [Ways to contribute](#ways-to-contribute)
- [Setting up](#setting-up)
- [Running the tests](#running-the-tests)
- [How gtm-pilot is built](#how-gtm-pilot-is-built)
- [Making a change](#making-a-change)
- [Pull requests](#pull-requests)
- [Releasing](#releasing)

## Ways to contribute

- **Report a bug** in [Issues](https://github.com/Madhur-Prakash/gtm-pilot/issues). Include
  your OS, terminal, Python version, `gtm-pilot --version`, `gputaskman --help` (which
  commands it lists), and the steps that show the problem. A screenshot helps with layout
  problems; say how big the terminal was.
- **Suggest a feature** in an issue before writing a large change, so we can agree on the
  approach first.
- **Fix a bug or add a feature** with a pull request (see below).
- **Improve the docs**: the [README](README.md) and this guide.

Security problems are not reported in public issues: see the [security policy](SECURITY.md).

Problems with the GPU readings themselves (wrong numbers, missing processes, driver errors)
belong to [gputaskman](https://github.com/shanselman/gputaskman/issues), since gtm-pilot shows
its output unchanged.

## Setting up

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/) (or plain pip).

```powershell
git clone https://github.com/Madhur-Prakash/gtm-pilot
cd gtm-pilot
uv sync
uv run gtm-pilot
```

To have a `gtm-pilot` command on your PATH that runs your checkout, so code changes take
effect the next time you start it:

```powershell
uv tool install --editable .
```

With pip instead:

```powershell
python -m pip install -e .
```

An editable install reads the version from `pyproject.toml`, so `gtm-pilot --version`
always matches the checkout.

The tests don't need a GPU or gputaskman. To try a change in the real app you need
gputaskman, which is installed with gtm-pilot; see [Installation](README.md#installation).

## Running the tests

```powershell
uv run python -m unittest discover -s tests
```

With pip: `python -m unittest discover -s tests`.

| File | What it covers |
|---|---|
| `tests/test_app.py` | The UI, driven by Textual's test pilot and a fake gputaskman |
| `tests/test_commands.py` | gputaskman argument lists, CLI helpers, small functions |
| `tests/test_gputaskman.py` | Finding gputaskman and parsing its output |
| `tests/test_pathcomplete.py` | File picker autocomplete |
| `tests/test_sessions.py` | File names, the sessions folder, saved recording settings |

`test_live_view_hands_over_the_terminal` needs a real terminal: it fails with
`SuspendNotSupported` when the tests run headless, as they do in an editor or in CI.

## How gtm-pilot is built

The [project layout](README.md#development) is in the README. A few rules the code keeps to:

- **gtm-pilot never reads the GPU itself.** Every reading comes from the gputaskman
  executable, and its output is shown unchanged: numbers, labels, process names and `n/a`
  values. New features drive gputaskman commands rather than add probes of their own.
- **gputaskman arguments are plain data** in `gtm_pilot/commands.py`, apart from the UI, so
  each one is easy to test.
- **Older gputaskman versions keep working.** An action that needs a subcommand names it in
  `needs=` in `gtm_pilot/screens/menu.py`, and is greyed out when `gputaskman --help` doesn't
  list it.
- **Every screen fits a small terminal.** Screens and dialogs use the `FitsTerminal` mixin
  (`gtm_pilot/screens/fit.py`) so their buttons stay on screen, and `test_app.py` checks this
  at several sizes.
- **Slow commands run off the UI thread**, in Textual workers, so the app stays responsive.
- **The same on Windows, Linux and macOS.** Anything that touches processes, signals or paths
  is written for all three: Windows has no `SIGINT` for a background process, for example.
- **Files are never overwritten.** Snapshots get `-2`, `-3` suffixes, and recordings are only
  appended to.

## Making a change

1. Create a branch from `main`.
2. Make the change, with tests. UI changes get a test in `tests/test_app.py` using
   `FakeGputaskman`.
3. Run the tests.
4. Try it in the real app, including on a short terminal (about 24 rows) if it changes a
   screen.
5. If users will notice the change, add it to the **Unreleased** section of the
   [changelog](CHANGELOG.md), under *Added*, *Changed* or *Fixed*.
6. Update the [README](README.md) if it changes a key, an option, a file gtm-pilot writes, or
   how something works.

Style:

- Follow the surrounding code: type hints, `from __future__ import annotations`, and small
  functions.
- Comments explain *why*, not what.
- Text the user sees is plain and specific: say what happened and what to do next.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`.

## Pull requests

- Keep a pull request to one change, and describe what it does and why.
- Link the issue it fixes, if there is one.
- Say how you tested it: OS, terminal, and gputaskman version.
- Add screenshots for changes to screens.
- Make sure the tests pass.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE), like the rest of gtm-pilot.

## Releasing

For maintainers. gtm-pilot follows [Semantic Versioning](https://semver.org/): a patch release
(`1.1.1`) for fixes, a minor release (`1.2.0`) for new features, and a major release for
changes that break how people use it.

1. In [CHANGELOG.md](CHANGELOG.md), rename **Unreleased** to the new version with today's date,
   point its link at `vX.Y.Z`, and start a new empty **Unreleased** section above it.
2. Set `version` in `pyproject.toml` and run `uv lock`.
3. Commit, then tag and push:

   ```powershell
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

4. Build and upload to PyPI:

   ```powershell
   Remove-Item -Recurse -Force dist
   python -m build
   python -m twine check dist/*
   python -m twine upload dist/*
   ```

5. Create the GitHub release from the tag, with that version's changelog entry as its notes:

   ```powershell
   gh release create vX.Y.Z --title "gtm-pilot X.Y.Z" --notes-file notes.md
   ```

PyPI never accepts the same version twice, so a mistake found after uploading needs a new
patch release.
