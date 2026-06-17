# Changelog

All notable changes to lexo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-06-17

### Changed

- Use SPDX license expression for verified PyPI metadata.
- Expand PyPI classifiers: add environment, intended audience, and per-version Python tags.
- Add Changelog and Releases links to project URLs.
- Fix README logo URL to absolute path so it renders on PyPI.

## [0.1.0] - 2026-06-17

First public release. Lexo is a complete, from-scratch rebuild of the previous
OCR Text Extractor into a local-first desktop document OCR tool. The legacy
Tkinter/CustomTkinter application has been removed.

### Added

- Document-centric engine with a hexagonal design: a UI-agnostic core behind
  swappable ports, driven identically by the CLI and the GUI.
- PDF operations: extract page ranges, split, crop, rotate, merge, and split
  two-up spreads.
- Smart OCR routing: digital PDF pages use their embedded text layer; only
  scanned pages are OCR'd (`--force-ocr` overrides).
- OCR via Google Docs OCR (free, best Burmese accuracy), behind a pluggable
  provider port so other engines can slot in.
- Burmese-aware text handling: NFC normalization and zero-width-space-safe
  cleaning.
- Exports: plain text (default), Markdown (with YAML frontmatter), and JSONL.
- A PySide6 desktop GUI (`lexo gui`): a top toolbar driving the open -> organize
  -> run -> proofread -> export flow, a left pages strip with per-page status and
  reordering, and a page preview beside an editable text pane. A visual crop/split
  editor for PDFs and images, copy-to-clipboard, and toast confirmations.
- Typer CLI: `info`, `check-update`, `extract`, `ocr`, `pdf` operations, `login`,
  `logout`, and `gui`.
- Bundled Noto Sans Myanmar font (SIL OFL) for consistent Burmese rendering.

### Changed

- Project renamed from `ocr-text-extractor` to `lexo`; installed with
  `uv tool install lexo`.
- OAuth scope narrowed to `drive.file`; tokens are stored in the OS keychain,
  replacing the previous pickle-based token storage.

### Removed

- The legacy v1 modules: the Tkinter GUI, the ad-hoc OCR processor, and pickle
  token storage.

[Unreleased]: https://github.com/PhilixTheExplorer/lexo/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/PhilixTheExplorer/lexo/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/PhilixTheExplorer/lexo/releases/tag/v0.1.0
