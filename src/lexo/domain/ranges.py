"""Human-friendly page ranges, e.g. "1-3,7,10-".

Parse once, then resolve against a concrete page count to get 0-based indices.
Input is 1-based and inclusive; open-ended ("10-") and open-start ("-3") are
supported.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class _Range:
    start: int | None  # 1-based inclusive; None = start of document
    end: int | None  # 1-based inclusive; None = end of document
    parity: str | None = None  # "odd" | "even" keeps only those 1-based pages


class PageRanges:
    def __init__(self, ranges: list[_Range]) -> None:
        self._ranges = ranges

    @classmethod
    def all_pages(cls) -> PageRanges:
        # An open range that resolves to every page of any document.
        return cls([_Range(None, None)])

    @classmethod
    def parse(cls, spec: str) -> PageRanges:
        if not spec or not spec.strip():
            raise ValueError("empty page range")
        ranges: list[_Range] = []
        for raw in spec.split(","):
            part = raw.strip()
            if not part:
                continue
            keyword = part.lower()
            if keyword == "all":
                ranges.append(_Range(None, None))
            elif keyword in ("odd", "even"):
                ranges.append(_Range(None, None, parity=keyword))
            elif "-" in part:
                lo, _, hi = part.partition("-")
                lo, hi = lo.strip(), hi.strip()
                start = cls._to_int(lo) if lo else None
                end = cls._to_int(hi) if hi else None
                if start is not None and end is not None and start > end:
                    raise ValueError(f"range start after end: {part!r}")
                ranges.append(_Range(start, end))
            else:
                n = cls._to_int(part)
                ranges.append(_Range(n, n))
        if not ranges:
            raise ValueError(f"no valid ranges in {spec!r}")
        return cls(ranges)

    @staticmethod
    def _to_int(s: str) -> int:
        try:
            n = int(s)
        except ValueError as exc:
            raise ValueError(f"not a page number: {s!r}") from exc
        if n < 1:
            raise ValueError(f"page numbers are 1-based: {s!r}")
        return n

    def resolve(self, total_pages: int) -> list[int]:
        """Return sorted, de-duplicated 0-based indices within [0, total_pages)."""
        if total_pages < 0:
            raise ValueError("total_pages must be >= 0")
        out: set[int] = set()
        for r in self._ranges:
            start = r.start or 1
            end = r.end or total_pages
            for p in range(start, end + 1):
                if not 1 <= p <= total_pages:
                    continue
                if r.parity == "odd" and p % 2 == 0:
                    continue
                if r.parity == "even" and p % 2 == 1:
                    continue
                out.add(p - 1)
        return sorted(out)

    def __repr__(self) -> str:
        return f"PageRanges({self._ranges!r})"
