"""TemplateAnalyzer — extracts design DNA from existing documents.

Analyzes PPTX, DOCX, and XLSX files to produce a :class:`DesignProfile`
capturing colors, fonts, layouts, and other design attributes.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from xml.etree.ElementTree import Element

from firefly_dworkers.design.models import DesignProfile

# ── Lazy library imports ────────────────────────────────────────────────────

try:
    import pptx

    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import docx

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# ── Constants ───────────────────────────────────────────────────────────────

_DRAWINGML_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

_SUPPORTED_FORMATS: dict[str, str] = {
    ".pptx": "pptx",
    ".docx": "docx",
    ".xlsx": "xlsx",
}


class TemplateAnalyzer:
    """Analyzes existing documents to extract their design language (colors, fonts, layouts)."""

    # ── Public API ──────────────────────────────────────────────────────────

    def _detect_format(self, source: str) -> str:
        """Detect format from file extension.

        Returns ``'pptx'``, ``'docx'``, or ``'xlsx'``.

        Raises:
            ValueError: For unsupported or unrecognised extensions.
        """
        _, ext = os.path.splitext(source)
        ext = ext.lower()
        fmt = _SUPPORTED_FORMATS.get(ext)
        if fmt is None:
            raise ValueError(f"Unsupported format: '{ext}'. Expected one of {sorted(_SUPPORTED_FORMATS.keys())}")
        return fmt

    async def analyze(self, source: str) -> DesignProfile:
        """Auto-detect format and extract design DNA into a :class:`DesignProfile`."""
        fmt = self._detect_format(source)
        dispatch = {
            "pptx": self._analyze_pptx,
            "docx": self._analyze_docx,
            "xlsx": self._analyze_xlsx,
        }
        return await dispatch[fmt](source)

    # ── PPTX analysis ──────────────────────────────────────────────────────

    async def _analyze_pptx(self, path: str) -> DesignProfile:
        """Extract from PPTX: layout names, theme colors, font scheme, slide dimensions."""
        if not PPTX_AVAILABLE:
            raise ImportError("python-pptx required: pip install firefly-dworkers[presentation]")
        return await asyncio.to_thread(self._analyze_pptx_sync, path)

    def _analyze_pptx_sync(self, path: str) -> DesignProfile:
        prs = pptx.Presentation(path)

        # Layouts
        available_layouts: list[str] = [layout.name for layout in prs.slide_layouts]

        # Theme colors from XML
        color_palette: list[str] = []
        primary_color = ""
        secondary_color = ""
        accent_color = ""
        try:
            master_element = prs.slide_masters[0].element
            color_palette, primary_color, secondary_color, accent_color = self._extract_theme_colors(master_element)
        except Exception:
            pass

        # Font scheme from XML
        heading_font = ""
        body_font = ""
        try:
            master_element = prs.slide_masters[0].element
            heading_font, body_font = self._extract_font_scheme(master_element)
        except Exception:
            pass

        # Slide dimensions (EMU)
        margins: dict[str, float] = {}
        try:
            if prs.slide_width is not None and prs.slide_height is not None:
                margins["slide_width_emu"] = float(prs.slide_width)
                margins["slide_height_emu"] = float(prs.slide_height)
        except Exception:
            pass

        return DesignProfile(
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
            color_palette=color_palette,
            heading_font=heading_font,
            body_font=body_font,
            available_layouts=available_layouts,
            margins=margins,
        )

    # ── DOCX analysis ──────────────────────────────────────────────────────

    async def _analyze_docx(self, path: str) -> DesignProfile:
        """Extract from DOCX: style names, fonts from styles, margins from first section."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx required: pip install firefly-dworkers[document]")
        return await asyncio.to_thread(self._analyze_docx_sync, path)

    def _analyze_docx_sync(self, path: str) -> DesignProfile:
        doc = docx.Document(path)

        # Style names
        styles: list[str] = []
        try:
            styles = [s.name for s in doc.styles if s.type is not None]
        except Exception:
            pass

        # Extract fonts from key styles
        heading_font = ""
        body_font = ""
        font_sizes: dict[str, float] = {}
        try:
            heading_font, body_font, font_sizes = self._extract_docx_fonts(doc)
        except Exception:
            pass

        # Margins from first section
        margins: dict[str, float] = {}
        try:
            if doc.sections:
                section = doc.sections[0]
                for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
                    val = getattr(section, attr, None)
                    if val is not None:
                        # Convert EMU to inches (914400 EMU per inch)
                        margins[attr.replace("_margin", "")] = round(float(val) / 914400.0, 3)
        except Exception:
            pass

        return DesignProfile(
            heading_font=heading_font,
            body_font=body_font,
            font_sizes=font_sizes,
            styles=styles,
            margins=margins,
        )

    # ── XLSX analysis ──────────────────────────────────────────────────────

    async def _analyze_xlsx(self, path: str) -> DesignProfile:
        """Extract from XLSX: default font, column widths, sheet names."""
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl required: pip install firefly-dworkers[data]")
        return await asyncio.to_thread(self._analyze_xlsx_sync, path)

    def _analyze_xlsx_sync(self, path: str) -> DesignProfile:
        wb = openpyxl.load_workbook(path, read_only=True)

        # Default font
        body_font = ""
        font_sizes: dict[str, float] = {}
        try:
            if wb.active is not None:
                cell = wb.active.cell(row=1, column=1)
                if cell.font and cell.font.name:
                    body_font = cell.font.name
                if cell.font and cell.font.sz:
                    font_sizes["default"] = float(cell.font.sz)
        except Exception:
            pass

        # Sheet names as layout info
        available_layouts: list[str] = []
        try:
            available_layouts = wb.sheetnames
        except Exception:
            pass

        wb.close()

        return DesignProfile(
            body_font=body_font,
            font_sizes=font_sizes,
            available_layouts=available_layouts,
        )

    # ── Private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _extract_theme_colors(master_element: Any) -> tuple[list[str], str, str, str]:
        """Parse clrScheme from the slide master XML element.

        Returns ``(color_palette, primary_color, secondary_color, accent_color)``.
        """
        color_palette: list[str] = []
        primary_color = ""
        secondary_color = ""
        accent_color = ""

        clr_scheme = master_element.find(f".//{{{_DRAWINGML_NS}}}clrScheme")
        if clr_scheme is None:
            return color_palette, primary_color, secondary_color, accent_color

        # Map of clrScheme child tag local names to semantic meaning
        tag_map: dict[str, str] = {
            "dk1": "dark1",
            "dk2": "dark2",
            "lt1": "light1",
            "lt2": "light2",
            "accent1": "accent1",
            "accent2": "accent2",
            "accent3": "accent3",
            "accent4": "accent4",
            "accent5": "accent5",
            "accent6": "accent6",
            "hlink": "hlink",
            "folHlink": "folHlink",
        }

        for child in clr_scheme:
            local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_name not in tag_map:
                continue

            color_hex = TemplateAnalyzer._extract_color_value(child)
            if color_hex:
                color_palette.append(color_hex)

                if local_name == "dk1" and not primary_color:
                    primary_color = color_hex
                elif local_name == "dk2" and not secondary_color:
                    secondary_color = color_hex
                elif local_name == "accent1" and not accent_color:
                    accent_color = color_hex

        return color_palette, primary_color, secondary_color, accent_color

    @staticmethod
    def _extract_color_value(element: Element) -> str:
        """Extract a hex color value from a color scheme child element.

        Looks for ``srgbClr`` (val attr) and ``sysClr`` (lastClr attr) sub-elements.
        """
        for sub in element:
            local = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
            if local == "srgbClr":
                val = sub.get("val", "")
                if val:
                    return f"#{val}"
            elif local == "sysClr":
                last_clr = sub.get("lastClr", "")
                if last_clr:
                    return f"#{last_clr}"
        return ""

    @staticmethod
    def _extract_font_scheme(master_element: Any) -> tuple[str, str]:
        """Parse fontScheme from the slide master XML element.

        Returns ``(heading_font, body_font)``.
        """
        heading_font = ""
        body_font = ""

        font_scheme = master_element.find(f".//{{{_DRAWINGML_NS}}}fontScheme")
        if font_scheme is None:
            return heading_font, body_font

        # Major font (headings)
        major = font_scheme.find(f"{{{_DRAWINGML_NS}}}majorFont")
        if major is not None:
            latin = major.find(f"{{{_DRAWINGML_NS}}}latin")
            if latin is not None:
                heading_font = latin.get("typeface", "")

        # Minor font (body)
        minor = font_scheme.find(f"{{{_DRAWINGML_NS}}}minorFont")
        if minor is not None:
            latin = minor.find(f"{{{_DRAWINGML_NS}}}latin")
            if latin is not None:
                body_font = latin.get("typeface", "")

        return heading_font, body_font

    @staticmethod
    def _extract_docx_fonts(doc: Any) -> tuple[str, str, dict[str, float]]:
        """Extract font info from DOCX styles.

        Returns ``(heading_font, body_font, font_sizes)``.
        """
        heading_font = ""
        body_font = ""
        font_sizes: dict[str, float] = {}

        for style in doc.styles:
            if style.type is None:
                continue
            try:
                name = style.name
                font = style.font
                if font is None:
                    continue

                if name == "Normal" and font.name:
                    body_font = font.name
                    if font.size:
                        font_sizes["body"] = round(float(font.size) / 12700.0, 1)
                elif name == "Heading 1" and font.name:
                    heading_font = font.name
                    if font.size:
                        font_sizes["h1"] = round(float(font.size) / 12700.0, 1)
                elif name == "Heading 2" and font.name and font.size:
                    font_sizes["h2"] = round(float(font.size) / 12700.0, 1)
            except Exception:
                continue

        return heading_font, body_font, font_sizes
