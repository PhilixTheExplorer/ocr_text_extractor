from pathlib import Path

from typer.testing import CliRunner

import lexo.cli.app as cli_app
from lexo import __version__
from lexo.cli.app import app
from lexo.domain.models import ExtractedDoc, PageText, TextKind

runner = CliRunner()


def test_version_constant() -> None:
    assert __version__


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "lexo" in result.stdout


def test_cli_info() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "data dir" in result.stdout


def test_cli_ocr_batch_writes_txt_for_folder(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "pdfs"
    output = tmp_path / "txt"
    source.mkdir()
    (source / "part006.pdf").write_bytes(b"pdf")

    class FakeService:
        async def ocr(self, path: Path, **kwargs) -> ExtractedDoc:
            assert path.name == "part006.pdf"
            return ExtractedDoc("id", path.name, 1, [PageText(0, "မြန်မာ", TextKind.SCANNED)])

        def export(self, doc: ExtractedDoc, fmt: str) -> str:
            assert fmt == "text"
            return doc.pages[0].text + "\n"

    monkeypatch.setattr(cli_app.LexoService, "create", lambda: FakeService())
    result = runner.invoke(
        app,
        ["ocr-batch", str(source), "--out-dir", str(output)],
    )

    assert result.exit_code == 0
    assert (output / "part006.txt").read_text(encoding="utf-8") == "မြန်မာ\n"
    assert "1 written" in result.stdout
