"""Application service layer: use cases shared by the CLI and the GUI.

This is GUI-free and engine-aware. It turns a file into an `ExtractedDoc`
(via embedded text or OCR) and renders it to an export format. Keeping it here
means the UI adapters stay thin and behaviour is identical across faces.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lexo.domain.events import Event
from lexo.domain.models import ExtractedDoc
from lexo.domain.ranges import PageRanges
from lexo.export import render
from lexo.infra.settings import Settings, load_settings
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit
from lexo.pipeline.engine import CancellationToken, OcrEngine
from lexo.pipeline.postprocess import postprocess
from lexo.pipeline.router import OcrRouter
from lexo.ports.pdf_toolkit import PdfToolkit
from lexo.text.extractor import TextExtractor

EventSink = Callable[[Event], None]


@dataclass
class LexoService:
    settings: Settings
    toolkit: PdfToolkit

    @classmethod
    def create(cls) -> LexoService:
        return cls(load_settings(), PyMuPdfToolkit())

    def extract(self, path: Path, ranges: PageRanges | None = None) -> ExtractedDoc:
        return TextExtractor(self.toolkit).extract(path, ranges)

    async def ocr(
        self,
        path: Path | list[Path],
        *,
        provider: str,
        lang: str | None = None,
        force_ocr: bool = False,
        ranges: PageRanges | None = None,
        on_event: EventSink | None = None,
        token: CancellationToken | None = None,
    ) -> ExtractedDoc:
        from lexo.providers import get_provider

        use_lang = lang or self.settings.ocr_language
        # Validate Google sign-in once, up front. Otherwise an expired or revoked
        # token surfaces as every page failing through the engine's retry loop
        # (slow, N cryptic errors) instead of one clear "sign in again" message.
        if provider == "google":
            import asyncio

            from lexo.infra.auth_google import get_credentials

            await asyncio.to_thread(get_credentials)
        engine = OcrEngine(get_provider(provider, use_lang), concurrency=self.settings.concurrency)
        router = OcrRouter(
            self.toolkit,
            engine,
            dpi=self.settings.render_dpi,
            batch_size=self.settings.ocr_batch_size,
        )
        if isinstance(path, list):
            return await router.process_images(
                path,
                ranges,
                lang=use_lang,
                postprocessor=postprocess,
                on_event=on_event,
                token=token,
            )
        if path.suffix.lower() == ".pdf":
            return await router.process_pdf(
                path,
                ranges,
                lang=use_lang,
                force_ocr=force_ocr,
                postprocessor=postprocess,
                on_event=on_event,
                token=token,
            )
        return await router.process_image(
            path, lang=use_lang, postprocessor=postprocess, on_event=on_event, token=token
        )

    def export(self, doc: ExtractedDoc, fmt: str) -> str:
        return render(doc, fmt)
