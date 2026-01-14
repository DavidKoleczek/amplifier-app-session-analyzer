# Amplifier Session Analyzer

Analyze Amplifier session logs and generate reports on agent autonomy metrics.

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
amplifier-session-analyzer \
  --time-scope "2026/01/10 - 2026/01/14" \
  --timezone "America/New_York" \
  --format html \
  --output my-report.html \
  --sessions-path ~/.amplifier/projects \
  --exclude-project "session-analyzer" \
  --features semantic_categories
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --time-scope` | `default` | Time period: 'default' (last full week), 'YYYY/MM/DD', or 'YYYY/MM/DD - YYYY/MM/DD' |
| `-z, --timezone` | `America/New_York` | IANA timezone for interpreting dates |
| `-f, --format` | `md` | Output format: 'md' (Markdown), 'html', or 'pdf' |
| `-p, --sessions-path` | `~/.amplifier/projects` | Path to Amplifier projects directory |
| `-o, --output` | `autonomy-report.<format>` | Output file path |
| `-x, --exclude-project` | (none) | Exclude projects matching pattern (can be used multiple times) |
| `-F, --features` | (none) | Enable optional features (e.g., `semantic_categories`) |

## What It Measures

**Autonomy Duration**: How long the AI agent works autonomously after receiving a user message, until it returns control to the user.

**Session Overlaps**: How often the user starts a new prompt in one session while another session is still processing, and the maximum number of parallel sessions observed.

**Semantic Categories**: When enabled with `-F semantic_categories`, uses an LLM to classify each user prompt into categories like question, implementation, debugging, review, exploration, etc.

## Development

```bash
# Run the smoke test
uv run python tests/smoke_test.py
```

The smoke test generates sample reports at `tests/.output/` using fixture data.

### Customizing Report Text

All user-facing text in the generated reports is centralized in [`amplifier_app_session_analyzer/constants.py`](amplifier_app_session_analyzer/constants.py). Edit this file to customize headings, descriptions, labels, and methodology text.
