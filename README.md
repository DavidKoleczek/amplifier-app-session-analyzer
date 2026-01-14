# Amplifier Session Analyzer

Analyze Amplifier session logs and generate PDF reports on agent autonomy metrics.

## Installation

```bash
# Install globally
uv tool install git+https://github.com/DavidKoleczek/amplifier-app-session-analyzer@main

# Or run directly with uvx
uvx --from git+https://github.com/DavidKoleczek/amplifier-app-session-analyzer@main amplifier-session-analyzer

# Or from local source
uv pip install -e .
```

## Updating

```bash
# Reinstall to get the latest version
uv tool install git+https://github.com/DavidKoleczek/amplifier-app-session-analyzer@main
```

## Usage

```bash
# Analyze with all options
amplifier-session-analyzer \
  --time-scope "2026/01/10 - 2026/01/12" \
  --timezone "America/Los_Angeles" \
  --sessions-path /path/to/amplifier/projects \
  --output my-report.pdf
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --time-scope` | `default` | Time period: 'default' (last full week), 'YYYY/MM/DD', or 'YYYY/MM/DD - YYYY/MM/DD' |
| `-z, --timezone` | `America/New_York` | IANA timezone for interpreting dates |
| `-f, --format` | `md` | Output format: 'md' (Markdown) or 'pdf' |
| `-p, --sessions-path` | `~/.amplifier/projects` | Path to Amplifier projects directory |
| `-o, --output` | `autonomy-report.md` | Output file path (extension matches format) |

## What It Measures

**Autonomy Duration**: How long the AI agent works autonomously after receiving a user message, until it returns control to the user. Calculated as the time from `prompt:submit` to `prompt:complete`.

**Session Overlaps**: How often the user starts a new prompt in one session while another session is still processing, and the maximum number of parallel sessions observed.

## Development

```bash
# Run the smoke test
uv run python tests/smoke_test.py
```

The smoke test generates sample reports at `tests/.output/` using fixture data.

### Customizing Report Text

All user-facing text in the generated reports is centralized in [`amplifier_app_session_analyzer/constants.py`](amplifier_app_session_analyzer/constants.py). Edit this file to customize headings, descriptions, labels, and methodology text.
