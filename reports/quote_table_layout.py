"""
Αυστηρά πλαίσια στηλών πίνακα γραμμών προσφοράς (PDF).

Όλα τα πλάτη σε mm, άθροισμα = QUOTE_PDF_TABLE_WIDTH_MM.
Αλλαγή εδώ ενημερώνει αρχή/τέλος κάθε στήλης — όχι δυναμική τοποθέτηση ανά μήκος κειμένου.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Πλάτος κειμένου A4: 210mm − 16mm − 16mm περιθώρια quote_pdf.html
QUOTE_PDF_TABLE_WIDTH_MM = 178


@dataclass(frozen=True)
class QuotePdfColumn:
    key: str
    header: str
    width_mm: int
    align: str  # left | right
    pad_top: int = 6
    pad_right: int = 8
    pad_bottom: int = 6
    pad_left: int = 8
    nowrap: bool = False
    wrap: bool = False

    @property
    def start_mm(self) -> int:
        return _COLUMN_STARTS[self.key]

    @property
    def end_mm(self) -> int:
        return self.start_mm + self.width_mm

    def cell_style(self) -> str:
        parts = [
            f"width:{self.width_mm}mm",
            f"max-width:{self.width_mm}mm",
            f"min-width:{self.width_mm}mm",
            "box-sizing:border-box",
            f"padding:{self.pad_top}px {self.pad_right}px {self.pad_bottom}px {self.pad_left}px",
            f"text-align:{self.align}",
        ]
        if self.nowrap:
            parts.append("white-space:nowrap")
        if self.wrap:
            parts.append("word-wrap:break-word")
            parts.append("overflow-wrap:break-word")
        return ";".join(parts)


QUOTE_PDF_COLUMNS: tuple[QuotePdfColumn, ...] = (
    QuotePdfColumn(
        key="num",
        header="#",
        width_mm=10,
        align="left",
        pad_right=10,
        pad_left=2,
        nowrap=True,
    ),
    QuotePdfColumn(
        key="desc",
        header="Περιγραφή",
        width_mm=52,
        align="left",
        pad_left=0,
        pad_right=30,
        wrap=True,
    ),
    QuotePdfColumn(
        key="cat",
        header="Κατηγορία",
        width_mm=24,
        align="left",
        pad_left=2,
        pad_right=6,
        nowrap=True,
    ),
    QuotePdfColumn(
        key="qty",
        header="Ποσ.",
        width_mm=21,
        align="right",
        pad_left=8,
        pad_right=8,
        nowrap=True,
    ),
    QuotePdfColumn(
        key="unit",
        header="Μον.",
        width_mm=17,
        align="left",
        nowrap=True,
    ),
    QuotePdfColumn(
        key="price",
        header="Τιμή",
        width_mm=27,
        align="right",
        nowrap=True,
    ),
    QuotePdfColumn(
        key="total",
        header="Σύνολο",
        width_mm=27,
        align="right",
        nowrap=True,
    ),
)

_COLUMN_STARTS: dict[str, int] = {}
_offset = 0
for _col in QUOTE_PDF_COLUMNS:
    _COLUMN_STARTS[_col.key] = _offset
    _offset += _col.width_mm

assert _offset == QUOTE_PDF_TABLE_WIDTH_MM, (
    f"Στήλες PDF: {_offset}mm ≠ {QUOTE_PDF_TABLE_WIDTH_MM}mm"
)


def get_quote_pdf_table_layout() -> dict[str, Any]:
    """Context για template PDF — στήλες με start/end mm και έτοιμο inline style."""
    category_col = next(c for c in QUOTE_PDF_COLUMNS if c.key == "cat")
    return {
        "width_mm": QUOTE_PDF_TABLE_WIDTH_MM,
        "columns": QUOTE_PDF_COLUMNS,
        "category_start_mm": category_col.start_mm,
        "table_style": (
            f"width:{QUOTE_PDF_TABLE_WIDTH_MM}mm;"
            f"max-width:{QUOTE_PDF_TABLE_WIDTH_MM}mm;"
            "table-layout:fixed;"
            "border-collapse:collapse;"
        ),
    }
