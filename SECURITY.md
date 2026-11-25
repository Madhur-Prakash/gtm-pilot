# Security policy

Related documents: [README](README.md) · [Contributing guide](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [License](LICENSE)

## Supported versions

Security fixes go into the latest release. Please upgrade before reporting a problem:

```powershell
uv tool upgrade gtm-pilot
```

| Version | Supported |
|---|---|
| 1.1.x (latest) | Yes |
| Older than 1.1 | No: upgrade to the latest release |

## Reporting a vulnerability

**Please don't report security problems in public issues.**

Report them privately through GitHub:
[Report a vulnerability](https://github.com/Madhur-Prakash/gtm-pilot/security/advisories/new)
(or the **Security** tab of the repository → **Report a vulnerability**).

Please include:

- what the problem is and what an attacker could do with it;
- the steps or a proof of concept that shows it;
- the gtm-pilot version (`gtm-pilot --version`), your OS and your Python version;
- if you know one, a suggested fix.

What to expect:

- an acknowledgement within 7 days;
- an assessment, and a plan if it is confirmed, within 14 days;
- a fixed release as soon as one is ready, with credit in the [changelog](CHANGELOG.md) and the
  security advisory unless you'd rather not be named.

Please give us a chance to release a fix before you disclose the problem publicly.

## Scope

gtm-pilot is a local terminal app. It has no network service, collects no telemetry, and
sends nothing anywhere. It runs the gputaskman executable on your own machine and shows what
it reports.

In scope, for example:

- gtm-pilot running a program other than the gputaskman you chose, or passing it arguments
  you didn't ask for;
- file names or paths that make gtm-pilot write outside the sessions folder;
- gtm-pilot exposing your data beyond the files it is documented to write.

Not in scope:

- **The gputaskman you point gtm-pilot at.** gtm-pilot runs the executable given with
  `--gputaskman` or `GTM_PILOT_GPUTASKMAN`, or the first `gputaskman` on your `PATH`, with your
  permissions; that is by design. Anyone who can change your `PATH` or environment can already
  run programs as you.
- **Problems in gputaskman itself.** Report them to
  [gputaskman](https://github.com/shanselman/gputaskman).
- **Problems in Textual, Python or other dependencies**, unless gtm-pilot uses them unsafely.
  Report them to those projects.

## Your data

Recordings (`.jsonl`) and snapshots (`.json`) are written to the sessions folder
(`~/gpu-sessions` by default). They hold gputaskman's output, which can include process names,
paths, command lines and model names. Check them before you share them. gtm-pilot also keeps the
settings each recording was started with in `.gtm-pilot-recordings` in the same folder. See
[Data files](README.md#data-files) for details.
