"""HTML → PDF rendering (WeasyPrint on Linux/Docker, xhtml2pdf fallback on Windows)."""

from __future__ import annotations

import logging
import sys
from io import BytesIO
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_XHTML2PDF_READY = False

_LINUX_FONT_DIRS = (
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/TTF"),
)


def _fonts_dir() -> Path:
    return Path(settings.BASE_DIR) / "static" / "fonts"


def _find_font(filename: str) -> Path | None:
    bundled = _fonts_dir() / filename
    if bundled.exists():
        return bundled
    for directory in _LINUX_FONT_DIRS:
        candidate = directory / filename
        if candidate.exists():
            return candidate
    return None


def _setup_xhtml2pdf_fonts() -> None:
    """Register DejaVu fonts for Greek text in xhtml2pdf/reportlab."""
    global _XHTML2PDF_READY
    if _XHTML2PDF_READY:
        return

    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    import xhtml2pdf.default as xhtml2pdf_default

    regular = _find_font("DejaVuSans.ttf")
    bold = _find_font("DejaVuSans-Bold.ttf")
    if not regular:
        raise RuntimeError("DejaVuSans.ttf not found — required for PDF Greek text")

    if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular)))

    bold_name = "DejaVuSans-Bold"
    if bold and bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(bold)))
    elif bold_name not in pdfmetrics.getRegisteredFontNames():
        bold_name = "DejaVuSans"

    addMapping("DejaVuSans", 0, 0, "DejaVuSans")
    addMapping("DejaVuSans", 1, 0, bold_name)
    addMapping("DejaVuSans", 0, 1, "DejaVuSans")
    addMapping("DejaVuSans", 1, 1, bold_name)

    # xhtml2pdf resolves CSS font-family via this map; default Helvetica lacks Greek glyphs.
    xhtml2pdf_default.DEFAULT_FONT.update(
        {
            "dejavusans": "DejaVuSans",
            "dejavu": "DejaVuSans",
            "dejavu sans": "DejaVuSans",
            "dejavusans-bold": bold_name,
            "dejavu-bold": bold_name,
            "helvetica": "DejaVuSans",
            "helvetica-bold": bold_name,
            "helvetica-boldoblique": bold_name,
            "helvetica-oblique": "DejaVuSans",
            "arial": "DejaVuSans",
            "sans": "DejaVuSans",
            "sansserif": "DejaVuSans",
            "sans-serif": "DejaVuSans",
        }
    )

    _XHTML2PDF_READY = True


def _render_with_weasyprint(html: str, base_url: str | None) -> bytes:
    if sys.platform == "win32":
        raise OSError("WeasyPrint requires GTK libraries (use Docker or xhtml2pdf fallback)")

    from weasyprint import HTML

    return HTML(string=html, base_url=base_url or "/").write_pdf()


def _xhtml2pdf_link_callback(uri: str, rel: str) -> str:
    """Resolve file:// and absolute paths for embedded images (logo)."""
    from urllib.parse import unquote, urlparse

    if uri.startswith("data:"):
        return uri

    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path = unquote(parsed.path)
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        return path

    candidate = Path(uri)
    if candidate.is_file():
        return str(candidate)

    return uri


def _render_with_xhtml2pdf(html: str) -> bytes:
    from xhtml2pdf import pisa

    _setup_xhtml2pdf_fonts()
    result = BytesIO()
    status = pisa.CreatePDF(
        src=html,
        dest=result,
        encoding="utf-8",
        link_callback=_xhtml2pdf_link_callback,
    )
    if status.err:
        raise RuntimeError("xhtml2pdf failed to render PDF")
    return result.getvalue()


def render_pdf(html: str, base_url: str | None = None) -> bytes:
    """
    Render HTML to PDF bytes.
    Uses WeasyPrint when system libraries are available (Docker/Linux),
    otherwise falls back to xhtml2pdf (Windows dev without GTK).
    """
    try:
        return _render_with_weasyprint(html, base_url)
    except Exception as exc:
        logger.info("WeasyPrint unavailable (%s), using xhtml2pdf fallback", exc)

    return _render_with_xhtml2pdf(html)
