<p align="center">
  <img src="https://raw.githubusercontent.com/PhilixTheExplorer/lexo/main/src/lexo/assets/lexo.png" alt="Lexo logo" width="120">
</p>

<h1 align="center">Lexo</h1>

<p align="center">
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/v/lexo.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/pyversions/lexo.svg" alt="Python versions"></a>
  <a href="https://pepy.tech/projects/lexo"><img src="https://api.pepy.tech/badge/lexo" alt="Total PyPI downloads"></a>
  <a href="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml"><img src="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
</p>

**Lexo** stands for **L**ocal **EX**traction and **O**CR: a local-first desktop
document OCR tool. It turns PDFs and images into clean, editable text, with
strong support for **Burmese (Myanmar script)** using free, high-accuracy Google
Docs OCR.

Everything runs on your machine. The only network call is the optional OCR
provider, which uses your own Google account, so there is nothing to pay for.
Lexo is built especially for Myanmar OCR work: scanned books, old Burmese PDFs,
dataset preparation, EPUB production, and other workflows where general-purpose
Latin-first OCR tools often fall short. Other non-Latin languages can work too
by passing the appropriate Google Docs OCR language hint.

## Features

- Myanmar-first OCR workflow: Burmese is the default OCR language hint, with
  Unicode normalization and bundled Myanmar font support for reliable review.
- Free Google Docs OCR from your own account: no paid OCR API, no per-page
  service fee, and no large local OCR model download.
- Multi-PDF batch OCR: process selected PDF files or every PDF in a folder,
  exporting one resumable UTF-8 TXT file per PDF.
- Error recovery for long OCR runs: transient page failures are retried
  automatically, and failed pages can be retried without re-running the whole
  document.
- PDF operations: extract page ranges, split, crop, rotate, merge, and split
  two-up spreads into separate pages.
- Visual crop and split editor in the GUI: drag a crop box on the rendered page
  to remove headers and page numbers, and split scanned two-up spreads. Works on
  a PDF or a batch of images.
- Smart OCR routing: digital PDFs use their embedded text layer (instant and
  lossless); only scanned pages are OCR'd.
- OCR via Google Docs OCR: free, high-accuracy (especially for Burmese), run on
  your own Google account. Other non-Latin scripts can also work with the right
  `--lang` value. Providers are pluggable behind a single interface.
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

For the desktop workflow, launch the app, open a document, choose text extraction
or Google Docs OCR, review the result, and export it:

```bash
lexo gui
```

For the CLI, digital PDFs can be extracted without an account:

```bash
lexo extract report.pdf -o report.txt
```

Scanned PDFs and images use Google Docs OCR. Complete the one-time Google setup
below, sign in, then run OCR:

```bash
lexo login
lexo ocr scan.pdf --lang my -o scan.txt
```

Basic PDF operations do not require Google sign-in:

```bash
lexo pdf extract book.pdf --pages "1-3,7,10-" -o subset.pdf
lexo pdf split book.pdf --every 10
lexo pdf crop book.pdf --top 8 --bottom 8 -o trimmed.pdf
```

Run `lexo --help` (or `lexo pdf --help`) for the full command list.

## Batch OCR PDFs

Use batch OCR to process multiple PDFs without opening and exporting each one
separately. Pass a folder to process every PDF directly inside it:

```bash
lexo login
lexo ocr-batch ./pdfs --out-dir ./txt
```

You can also pass specific PDF files:

```bash
lexo ocr-batch chapter-a.pdf chapter-b.pdf --out-dir ./txt
```

Lexo keeps each source filename and changes its extension to `.txt`. Existing
TXT files are skipped so an interrupted batch can resume; pass `--overwrite` to
replace them. Batch OCR processes every page visually by default. Pass
`--no-force-ocr` if usable embedded text should be preserved instead.

In the desktop app, choose **Batch OCR PDFs** on the welcome screen or open
**File -> Batch OCR PDFs...**. Select individual PDFs or load every PDF from a
folder, choose the output folder, and start OCR.

## Video walkthroughs

Short walkthroughs (~1 min each) covering setup and common Burmese OCR workflows.

OCR processing time depends on your network speed and Google Drive's response
time. Lexo retries each page automatically on transient failures. If any pages
still fail, a "Retry Failed Pages" button appears so you can re-run just those.

### 1 - Install with uv and one-time Google Cloud setup

Everything needed before the first OCR run:
install Lexo with `uv tool install lexo` → create a Google Cloud project →
enable the Drive API → configure the OAuth consent screen → create and download
`credentials.json` → place it in the config directory → run `lexo login` to sign in.

https://github.com/user-attachments/assets/92d86684-ebaa-438a-a6dd-880d49943405

### 2 - Main OCR workflow: scanned Burmese PDF (GUI)

Full GUI walkthrough for a scanned Burmese PDF:
open the file → use the visual editor to **split two-up spreads** and **crop**
headers/margins → **run Google Docs OCR** → review the per-page text → **export**
to plain text.

https://github.com/user-attachments/assets/b247cdc5-0421-4400-bc6c-f4dc35268268

### 3 - Legacy Windows font PDF: getting real Burmese text with Google OCR (GUI)

Some Burmese documents were created with old non-Unicode Windows fonts such as
Win Innwa or Win Myanmar. These fonts render Burmese glyphs by mapping them onto
ASCII codepoints, so the PDF actually stores English characters internally - the
font is what makes them look Burmese on screen. When you run text extraction on
such a file, you get those raw ASCII characters back, which is technically correct
but not useful as Burmese text. This video shows how to recognise this case in the
GUI and switch to Google Docs OCR instead, which reads the page visually and
returns proper Unicode Burmese.

https://github.com/user-attachments/assets/9cd60cbc-6a2b-4925-b076-89e97346e391

## Commands

| Command | Purpose |
|---------|---------|
| `lexo extract <pdf>` | Extract the embedded text layer of a digital PDF |
| `lexo ocr <pdf\|image>` | OCR a scanned document (`--lang`, `--force-ocr`) |
| `lexo ocr-batch <files-or-folders> -o <directory>` | OCR multiple PDFs to individual UTF-8 TXT files |
| `lexo pdf info\|extract\|split\|crop\|rotate\|merge\|split-spread` | PDF operations |
| `lexo login` / `lexo logout` | Sign in to / out of Google (token stored in the OS keychain) |
| `lexo gui` | Launch the desktop app |
| `lexo info` | Show the version and where Lexo stores its data |
| `lexo check-update` | Check PyPI for a newer release |

Single-document extraction and OCR support `--format text|markdown|jsonl`.
Batch OCR exports plain text.

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
- Other non-Latin languages may work through Google Docs OCR when you pass the
  matching language hint.
- Extracted text is normalized to Unicode NFC and zero-width spaces are
  preserved.
- A Myanmar Unicode font ([Noto Sans Myanmar](https://fonts.google.com/noto/specimen/Noto+Sans+Myanmar),
  SIL Open Font License) is bundled so Burmese renders in the GUI regardless of
  installed system fonts. The license travels with it as `OFL.txt`.

Lexo exists because many OCR tools are strongest on Latin-script documents. Local
engines such as Tesseract and PaddleOCR can be useful, but Myanmar accuracy,
setup size, and reliability vary a lot in practice. Lexo uses Google Docs OCR as
the practical free path today, while keeping the OCR provider boundary open for
better future options.

## Future direction

Lexo focuses on turning scanned or legacy Burmese documents into editable text.
Document intelligence features such as layout-aware extraction, table structure,
and semantic field detection are not built in yet. If a reliable free approach
becomes available, they are natural next steps.

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

## Contributing

Bug reports, documentation fixes, and focused pull requests are welcome. Please
see [CONTRIBUTING.md](CONTRIBUTING.md) for setup notes, recommended checks, and
privacy guidance before attaching sample PDFs or images.

## License

AGPL-3.0, to align with PyMuPDF. See [LICENSE](LICENSE).
