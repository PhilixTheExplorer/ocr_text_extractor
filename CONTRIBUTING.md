# Contributing

Thanks for helping improve Lexo. This project is a local-first Python desktop and
CLI app for document OCR, with special care for Burmese text and PDF workflows.

## Development setup

Lexo uses Python 3.11+ and `uv`.

```bash
uv sync
```

Run the CLI from a checkout with:

```bash
uv run lexo --help
```

Launch the desktop app with:

```bash
uv run lexo gui
```

Install the repository's Git hooks once after cloning:

```bash
uv run lefthook install
```

The pre-push hook runs the same Ruff, Mypy, and Pytest checks as CI. Run it
manually at any time with `uv run lefthook run pre-push`.

## Before opening a pull request

Please run the smallest checks that match your change. For code changes, the
usual checks are:

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

If your change only updates documentation or GitHub metadata, tests usually are
not needed.

## Issues

When reporting a bug, include:

- What you tried to do
- What happened instead
- Your OS, Python version, Lexo version, and install method
- A small reproduction case, if possible

PDFs and images can contain private data. Please remove sensitive content before
attaching files to an issue.

## Pull requests

Keep pull requests focused and explain the user-visible behavior change. Add or
update tests when changing parsing, OCR routing, PDF operations, exports, or CLI
behavior.

Documentation fixes, typo fixes, and small quality-of-life improvements are
welcome.
