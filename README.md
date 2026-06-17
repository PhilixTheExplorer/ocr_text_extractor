<p align="center">
  <img src="https://raw.githubusercontent.com/PhilixTheExplorer/lexo/main/src/lexo/assets/lexo.png" alt="Lexo logo" width="120">
</p>

<h1 align="center">Lexo</h1>

<p align="center">
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/v/lexo.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/pyversions/lexo.svg" alt="Python versions"></a>
  <a href="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml"><img src="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
</p>

**Lexo** stands for **L**ocal **EX**traction and **O**CR: a local-first desktop
document OCR tool. It turns PDFs and images into clean, editable text, with
strong support for **Burmese (Myanmar script)** using free, high-accuracy Google
Docs OCR.

Everything runs on your machine. The only network call is the optional OCR
provider, which uses your own Google account, so there is nothing to pay for.

## Features

- PDF operations: extract page ranges, split, crop, rotate, merge, and split
  two-up spreads into separate pages.
- Visual crop and split editor in the GUI: drag a crop box on the rendered page
  to remove headers and page numbers, and split scanned two-up spreads. Works on
  a PDF or a batch of images.
- Smart OCR routing: digital PDFs use their embedded text layer (instant and
  lossless); only scanned pages are OCR'd.
- OCR via Google Docs OCR: free, high-accuracy (especially for Burmese), run on
  your own Google account. Providers are pluggable behind a single interface.
- Burmese-aware text handling: NFC normalization and zero-width-space-safe
  cleaning.
- Proofread before you export: the desktop app shows each page beside an editable
  text pane.
- Exports: plain text (the default), Markdown (with YAML frontmatter), and JSONL
  (for NLP and LLM workflows).
- A desktop GUI and a scriptable CLI, both driving the same engine.

## Install

Lexo is a Python package. With [uv](https://docs.astral.sh/uv/):

```bash
uv tool install lexo            # the `lexo` CLI and `lexo gui`
```

Without uv, use any standard Python installer:

```bash
pipx install lexo
# or
python -m pip install lexo
```

Everything is included in the one install. There are no separate system
dependencies to set up.

## Quick start

```bash
# Digital PDF: extract the embedded text, instantly (plain text by default)
lexo extract report.pdf -o report.txt

# Scanned PDF or image: OCR it (Burmese by default) with your Google account
lexo login
lexo ocr scan.pdf --lang my -o scan.txt

# PDF operations
lexo pdf extract book.pdf --pages "1-3,7,10-" -o subset.pdf
lexo pdf split book.pdf --every 10
lexo pdf crop book.pdf --top 8 --bottom 8 -o trimmed.pdf

# Launch the desktop app
lexo gui
```

Run `lexo --help` (or `lexo pdf --help`) for the full command list.

## Commands

| Command | Purpose |
|---------|---------|
| `lexo extract <pdf>` | Extract the embedded text layer of a digital PDF |
| `lexo ocr <pdf\|image>` | OCR a scanned document (`--lang`, `--force-ocr`) |
| `lexo pdf info\|extract\|split\|crop\|rotate\|merge\|split-spread` | PDF operations |
| `lexo login` / `lexo logout` | Sign in to / out of Google (token stored in the OS keychain) |
| `lexo gui` | Launch the desktop app |
| `lexo info` | Show the version and where Lexo stores its data |
| `lexo check-update` | Check PyPI for a newer release |

All output formats are available via `--format text|markdown|jsonl`.

## Google Docs OCR setup (one-time)

OCR uses Google Docs OCR, which is free and runs on your own Google account. You
bring your own OAuth client credentials (`credentials.json`). It is a one-time
setup:

1. **Create or pick a Google Cloud project** at the
   [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable the Google Drive API**: APIs & Services -> Library -> search
   "Google Drive API" -> Enable.
3. **Configure the OAuth consent screen**: APIs & Services -> OAuth consent
   screen -> User type **External** -> add an app name and your email, then add
   your own Google account under **Test users**.
4. **Create the OAuth client**: APIs & Services -> Credentials -> Create
   credentials -> OAuth client ID -> Application type **Desktop app** -> Create
   -> **Download JSON**, and rename the file to `credentials.json`.
5. **Place `credentials.json`** where Lexo looks for it (first match wins):
   - the path in the `LEXO_GOOGLE_CREDENTIALS` environment variable, or
   - your Lexo config directory (run `lexo info` to see it), or
   - the current working directory.
6. **Sign in**: run `lexo login` (or in the GUI, Account -> Sign in with
   Google). A browser opens; approve access. The token is saved in your OS
   keychain, and `credentials.json` is only read during login.

Notes:

- Lexo requests only the least-privilege `drive.file` scope, so it can touch
  only the temporary files it creates while running OCR.
- While the OAuth app stays in **Testing** status, Google expires the sign-in
  roughly every 7 days, so you may need to run `lexo login` again periodically.
- Sign out any time with `lexo logout` (or Account -> Sign out); this removes
  the stored token.

## Burmese notes

- The OCR language hint defaults to `my`; override with `--lang`.
- Extracted text is normalized to Unicode NFC and zero-width spaces are
  preserved.
- A Myanmar Unicode font ([Noto Sans Myanmar](https://fonts.google.com/noto/specimen/Noto+Sans+Myanmar),
  SIL Open Font License) is bundled so Burmese renders in the GUI regardless of
  installed system fonts. The license travels with it as `OFL.txt`.

## Tech stack

| Area | Tools |
|------|-------|
| Language | Python 3.11+ |
| CLI | [Typer](https://typer.tiangolo.com/) |
| Desktop GUI | [PySide6](https://doc.qt.io/qtforpython/) (Qt) |
| PDF engine | [PyMuPDF](https://pymupdf.readthedocs.io/) |
| Images | [Pillow](https://pillow.readthedocs.io/en/stable/index.html/) |
| OCR | Google Docs OCR via the [Google Drive API](https://developers.google.com/workspace/drive) (`google-api-python-client` + `google-auth`) |
| Credentials | [keyring](https://github.com/jaraco/keyring) (OS keychain) |
| Settings | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (env-var config) |
| Logging | [structlog](https://www.structlog.org/) |
| Paths | [platformdirs](https://github.com/tox-dev/platformdirs) |
| Build & packaging | [uv](https://docs.astral.sh/uv/) + [Hatchling](https://hatch.pypa.io/) |
| Quality | [Ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy-lang.org/), [pytest](https://docs.pytest.org/) |
| CI/CD | GitHub Actions, PyPI Trusted Publishing |

## Development

```bash
uv sync
uv run ruff check src tests
uv run mypy src/lexo
uv run pytest
```

Design notes live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

AGPL-3.0, to align with PyMuPDF. See [LICENSE](LICENSE).
