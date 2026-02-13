"""Document designer example — full ContentBrief -> DesignSpec -> rendered output.

Demonstrates the complete design intelligence pipeline:
  1. Build a ContentBrief describing what to produce.
  2. Optionally analyze a reference template for design DNA.
  3. DesignEngine (LLM-powered) produces a DesignSpec.
  4. Enhanced tools render the final files.

This example creates both a .pptx and a .docx from the same content brief.
"""

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.design.engine import DesignEngine
from firefly_dworkers.design.models import (
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    OutputType,
)
from firefly_dworkers.tools.document.models import SectionSpec
from firefly_dworkers.tools.document.word import WordTool
from firefly_dworkers.tools.presentation.models import SlideSpec
from firefly_dworkers.tools.presentation.powerpoint import PowerPointTool


async def main() -> None:
    # 1. Build a ContentBrief
    brief = ContentBrief(
        output_type=OutputType.PRESENTATION,
        title="Q4 Strategy Review",
        audience="C-suite executives",
        tone="formal",
        purpose="quarterly business review",
        sections=[
            ContentSection(
                heading="Executive Summary",
                content="Strong performance across all business units with 23% YoY revenue growth.",
                key_metrics=[],
            ),
            ContentSection(
                heading="Market Analysis",
                content="The AI advisory market continues to expand rapidly.",
                bullet_points=[
                    "Total addressable market: $38B by 2027",
                    "Three key competitors identified",
                    "Regulatory tailwinds in financial services",
                ],
                chart_ref="market_growth",
            ),
            ContentSection(
                heading="Recommendations",
                content="Prioritize organic growth in Q3-Q4.",
                bullet_points=[
                    "Launch AI Readiness Assessment offering",
                    "Expand healthcare vertical",
                    "Invest in proprietary tooling",
                ],
            ),
        ],
        datasets=[
            DataSet(
                name="market_growth",
                description="AI advisory market size projections",
                categories=["2024", "2025", "2026", "2027"],
                series=[
                    DataSeries(name="Market Size ($B)", values=[12.5, 18.3, 27.1, 38.0]),
                ],
            ),
        ],
    )

    # 2. DesignEngine produces the design spec (uses LLM)
    engine = DesignEngine(model="anthropic:claude-sonnet-4-5-20250929")
    spec = await engine.design(brief)

    print(f"Design profile: {spec.profile.primary_color} / {spec.profile.heading_font}")
    print(f"Slides designed: {len(spec.slides)}")
    print(f"Charts resolved: {list(spec.charts.keys())}")

    # 3. Render as PowerPoint
    if spec.slides:
        ppt = PowerPointTool()
        ppt_slides = [
            SlideSpec(
                layout=s.layout or "Title and Content",
                title=s.title,
                content="\n".join(
                    b.text for b in s.content_blocks if b.block_type == "text"
                ) if s.content_blocks else "",
                bullet_points=[
                    b for block in s.content_blocks
                    if block.block_type == "bullets"
                    for b in block.bullet_points
                ] if s.content_blocks else [],
                speaker_notes=s.speaker_notes,
                title_style=s.title_style,
                body_style=s.body_style,
                background_color=s.background,
            )
            for s in spec.slides
        ]
        ppt_path = await ppt.create_and_save("q4_review.pptx", slides=ppt_slides)
        print(f"\nPresentation saved to {ppt_path}")

    # 4. Render as Word document too
    word = WordTool()
    sections = [
        SectionSpec(
            heading=s.heading,
            heading_level=s.heading_level if s.heading_level > 0 else 1,
            content=s.content,
            bullet_points=s.bullet_points,
            heading_style=s.heading_style,
            body_style=s.body_style,
        )
        for s in spec.document_sections
    ] if spec.document_sections else [
        SectionSpec(heading="Generated Report", content="Design produced presentation layout only.")
    ]
    doc_path = await word.create_and_save("q4_review.docx", title=brief.title, sections=sections)
    print(f"Document saved to {doc_path}")


asyncio.run(main())
