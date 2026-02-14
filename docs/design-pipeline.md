# Design Intelligence Pipeline

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Pipeline Stages](#pipeline-stages)
  - [Stage 1: Content Brief](#stage-1-content-brief)
  - [Stage 2: Template Analysis](#stage-2-template-analysis)
  - [Stage 3: Design Engine](#stage-3-design-engine)
  - [Stage 4: Converters](#stage-4-converters)
  - [Stage 5: Rendering](#stage-5-rendering)
- [Supported Output Formats](#supported-output-formats)
  - [Presentations (PPTX)](#presentations-pptx)
  - [Documents (DOCX)](#documents-docx)
  - [Spreadsheets (XLSX)](#spreadsheets-xlsx)
  - [PDF](#pdf)
- [Pipeline Tools](#pipeline-tools)
  - [DesignPipelineTool (Presentation)](#designpipelinetool-presentation)
  - [DocumentPipelineTool](#documentpipelinetool)
  - [SpreadsheetPipelineTool](#spreadsheetpipelinetool)
  - [UnifiedDesignPipeline](#unifieddesignpipeline)
- [Design Models](#design-models)
- [Autonomy and Checkpoints](#autonomy-and-checkpoints)
- [Image Resolution](#image-resolution)
- [LLM Integration](#llm-integration)
- [Usage Examples](#usage-examples)
- [Related Documentation](#related-documentation)

---

The design intelligence pipeline is the creative brain of firefly-dworkers. It takes structured content from upstream workers and produces professionally designed output artifacts (presentations, documents, spreadsheets) using LLM-powered design reasoning.

---

## Overview

The pipeline solves a key problem: bridging the gap between **content** (what to say) and **design** (how to present it). Rather than relying on hardcoded templates, the pipeline uses an LLM to make design decisions -- layout selection, content distribution, chart types, typography -- producing output that adapts to brand guidelines and audience context.

Three core components work together:

| Component | Module | Responsibility |
|-----------|--------|----------------|
| `TemplateAnalyzer` | `firefly_dworkers.design.analyzer` | Extracts design DNA from reference templates |
| `DesignEngine` | `firefly_dworkers.design.engine` | LLM-powered layout and style decisions |
| Converters | `firefly_dworkers.design.converter` | Translates design output to tool-specific input |

---

## Architecture

```
                          ┌─────────────────┐
                          │  ContentBrief   │
                          │  (from workers) │
                          └────────┬────────┘
                                   │
                    ┌──────────────┤
                    ▼              ▼
           ┌────────────┐  ┌──────────────────┐
           │  Template   │  │  Autonomous      │
           │  Analyzer   │  │  Profile Gen     │
           │  (XML+VLM)  │  │  (LLM)           │
           └──────┬──────┘  └────────┬─────────┘
                  │                  │
                  └──────┬───────────┘
                         ▼
               ┌──────────────────┐
               │  DesignProfile   │
               │  (design DNA)    │
               └────────┬────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  DesignEngine    │
               │  (LLM layout)   │
               └────────┬────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   DesignSpec     │
               │   (blueprint)   │
               └────────┬────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐
    │ Slide     │ │ Section   │ │ Sheet     │
    │ Converter │ │ Converter │ │ Converter │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
          ▼             ▼              ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐
    │ PowerPoint│ │ Word/PDF  │ │ Excel     │
    │ Tool      │ │ Tool      │ │ Tool      │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
          ▼             ▼              ▼
       .pptx         .docx/.pdf      .xlsx
```

---

## Pipeline Stages

### Stage 1: Content Brief

The pipeline starts with a `ContentBrief` -- a structured handoff from upstream workers (analyst, researcher, manager) containing the raw content and context.

```python
from firefly_dworkers.design.models import ContentBrief, OutputType, ContentSection

brief = ContentBrief(
    output_type=OutputType.PRESENTATION,
    title="Q4 Revenue Analysis",
    audience="Board of Directors",
    tone="professional",
    purpose="Quarterly business review",
    sections=[
        ContentSection(
            heading="Revenue Overview",
            content="Total revenue grew 15% YoY...",
            key_metrics=[KeyMetric(label="Revenue", value="$4.2M", change="+15%")],
            chart_ref="revenue_data",
        ),
        ContentSection(
            heading="Market Expansion",
            content="Three new markets entered...",
            bullet_points=["LATAM: $800K", "APAC: $1.2M", "EMEA: $600K"],
        ),
    ],
    datasets=[
        DataSet(
            name="revenue_data",
            categories=["Q1", "Q2", "Q3", "Q4"],
            series=[DataSeries(name="Revenue", values=[3.1, 3.5, 3.8, 4.2])],
        ),
    ],
)
```

Key fields:

| Field | Purpose |
|-------|---------|
| `output_type` | Target format: `PRESENTATION`, `DOCUMENT`, `SPREADSHEET`, `PDF` |
| `title` | Document title |
| `sections` | Content sections with headings, text, bullets, metrics |
| `audience` | Target audience (influences design tone) |
| `tone` | Desired tone (professional, creative, academic) |
| `datasets` | Data for chart generation |
| `reference_template` | Path to a template file for design extraction |
| `image_requests` | Requests for images (AI-generated, URL, file, stock) |

### Stage 2: Template Analysis

When a `reference_template` is provided, the `TemplateAnalyzer` extracts design DNA into a `DesignProfile`. It uses a two-pass approach:

1. **XML Analysis** (fast, reliable) -- parses the template file directly to extract colors, fonts, layout names, and placeholder positions.
2. **VLM Fallback** (optional) -- when XML analysis yields incomplete results, sends rendered images to a vision-language model for richer design extraction.

```python
from firefly_dworkers.design.analyzer import TemplateAnalyzer

analyzer = TemplateAnalyzer(vlm_model="anthropic:claude-sonnet-4-5-20250929")
profile = await analyzer.analyze("corporate_template.pptx")

# profile.primary_color → "#1F4E79"
# profile.heading_font → "Calibri"
# profile.available_layouts → ["Title Slide", "Title and Content", ...]
# profile.layout_zones → {"Title Slide": LayoutZone(...), ...}
```

The analyzer supports PPTX, DOCX, and XLSX templates. For presentations, it also extracts `LayoutZone` data with precise placeholder positions, enabling template-aware content placement.

When no template is provided, the `DesignEngine` generates a `DesignProfile` autonomously using the LLM based on audience, tone, and purpose context.

### Stage 3: Design Engine

The `DesignEngine` is the LLM-powered creative core. It makes three key decisions:

1. **Chart type selection** -- analyzes each `DataSet` and selects the optimal chart type using heuristics first (temporal → line, few categories → pie, etc.), with optional LLM fallback for ambiguous cases.
2. **Layout design** -- uses the LLM to decide the structure: which slides/sections/sheets to create, what content goes where, and which layouts to use.
3. **Style application** -- applies the `DesignProfile` colors, fonts, and spacing throughout.

```python
from firefly_dworkers.design.engine import DesignEngine

engine = DesignEngine(model="anthropic:claude-sonnet-4-5-20250929")
spec = await engine.design(brief, profile)

# spec.slides → [SlideDesign(...), SlideDesign(...), ...]
# spec.charts → {"revenue_data": ResolvedChart(chart_type="line", ...)}
# spec.output_type → OutputType.PRESENTATION
```

The engine outputs a `DesignSpec` -- the fully resolved blueprint containing:

- `slides` (for presentations) -- list of `SlideDesign` with layout, title, content blocks
- `document_sections` (for documents) -- list of `SectionDesign` with headings, content, tables
- `sheets` (for spreadsheets) -- list of `SheetDesign` with headers, rows, formatting
- `charts` -- resolved chart specifications (type, data, colors)
- `images` -- resolved image data (bytes, dimensions)

### Stage 4: Converters

Converters bridge the gap between LLM-generated design models and tool-specific input models. Each output format has dedicated converter functions in `firefly_dworkers.design.converter`:

**Presentation converters:**

| Function | Input → Output |
|----------|---------------|
| `convert_slide_design_to_slide_spec` | `SlideDesign` → `SlideSpec` |
| `convert_resolved_chart_to_chart_spec` | `ResolvedChart` → `ChartSpec` |
| `convert_styled_table_to_table_spec` | `StyledTable` → `TableSpec` |
| `convert_design_spec_to_slide_specs` | `DesignSpec` → `list[SlideSpec]` |

**Document converters:**

| Function | Input → Output |
|----------|---------------|
| `convert_section_design_to_section_spec` | `SectionDesign` → `SectionSpec` |
| `convert_styled_table_to_table_data` | `StyledTable` → `TableData` |
| `convert_design_spec_to_section_specs` | `DesignSpec` → `list[SectionSpec]` |

**Spreadsheet converters:**

| Function | Input → Output |
|----------|---------------|
| `convert_sheet_design_to_sheet_spec` | `SheetDesign` → `SheetSpec` |
| `convert_design_spec_to_sheet_specs` | `DesignSpec` → `list[SheetSpec]` |

Converters handle:
- Resolving `chart_ref` and `image_ref` references from the spec's resolved collections
- Writing image bytes to temporary files for embedding
- Flattening `ContentBlock` lists into tool-expected text/bullet formats
- Sanitizing LLM output (e.g., invalid number format keys)
- Building `ContentZone` with EMU coordinates from `LayoutZone` data

### Stage 5: Rendering

The final stage passes tool-specific specs to rendering tools:

| Format | Tool | Output |
|--------|------|--------|
| Presentation | `PowerPointTool` | `.pptx` bytes |
| Document | `WordTool` | `.docx` bytes |
| Spreadsheet | `ExcelTool` | `.xlsx` bytes |
| PDF | `PDFTool` | `.pdf` bytes |

Rendering tools are registered in the tool registry and follow the port/adapter pattern (see [Tools Overview](tools/overview.md)).

---

## Supported Output Formats

### Presentations (PPTX)

The presentation pipeline was the first format implemented and has the most mature feature set:

- **Template-aware positioning** -- uses `LayoutZone` data to place content in the correct placeholders
- **Chart embedding** -- embeds charts directly in slides using python-pptx
- **Image embedding** -- writes resolved images to temp files and embeds them
- **Speaker notes** -- adds speaker notes to slides
- **Transitions** -- configures slide transitions
- **Title/body styling** -- applies `TextStyle` to titles and body text

Pipeline tool: `DesignPipelineTool` (registry key: `design_pipeline`)

### Documents (DOCX)

The document pipeline supports structured documents with:

- **Heading hierarchy** -- heading levels 1-6
- **Rich content** -- paragraphs, bullet points, numbered lists
- **Tables** -- converted from `StyledTable` to `TableData`
- **Charts** -- embedded as `ResolvedChart` objects
- **Images** -- resolved and embedded via `ImagePlacement`
- **Callouts** -- highlighted text blocks
- **Page breaks** -- explicit page break control
- **PDF export** -- can render via `PDFTool` instead of `WordTool` when `output_format="pdf"`

Pipeline tool: `DocumentPipelineTool` (registry key: `document_design_pipeline`)

### Spreadsheets (XLSX)

The spreadsheet pipeline supports data-oriented output:

- **Multi-sheet workbooks** -- each `SheetDesign` becomes a separate worksheet
- **Header styling** -- font, color, background via `TextStyle`
- **Column widths** -- explicit width control per column
- **Number formats** -- per-column number formatting (sanitized for valid column letters)
- **Charts** -- embedded in worksheets

Pipeline tool: `SpreadsheetPipelineTool` (registry key: `spreadsheet_design_pipeline`)

### PDF

PDF output is handled by the document pipeline with `output_format="pdf"`. The pipeline converts `SectionSpec` objects to HTML, then renders via `PDFTool`.

---

## Pipeline Tools

All pipeline tools follow the same pattern:

1. Build a `ContentBrief` from input parameters
2. Optionally analyze a template to get a `DesignProfile`
3. Run `DesignEngine.design()` to produce a `DesignSpec`
4. Hit autonomy checkpoint: `design_spec_approval`
5. Resolve images (if requested)
6. Convert `DesignSpec` to tool-specific specs
7. Hit autonomy checkpoint: `pre_render`
8. Render using the appropriate tool
9. Save output and hit checkpoint: `deliverable`

### DesignPipelineTool (Presentation)

```python
from firefly_dworkers.tools.registry import tool_registry

pipeline = tool_registry.create(
    "design_pipeline",
    model="anthropic:claude-sonnet-4-5-20250929",
    vlm_model="anthropic:claude-sonnet-4-5-20250929",
)

result = await pipeline.execute(
    title="Q4 Review",
    sections=[{"heading": "Revenue", "content": "Revenue grew 15%..."}],
    template_path="template.pptx",
    output_path="output.pptx",
)
```

### DocumentPipelineTool

```python
pipeline = tool_registry.create(
    "document_design_pipeline",
    model="anthropic:claude-sonnet-4-5-20250929",
)

result = await pipeline.execute(
    title="Annual Report",
    sections=[{"heading": "Executive Summary", "content": "..."}],
    output_format="docx",  # or "pdf"
    output_path="report.docx",
)
```

### SpreadsheetPipelineTool

```python
pipeline = tool_registry.create(
    "spreadsheet_design_pipeline",
    model="anthropic:claude-sonnet-4-5-20250929",
)

result = await pipeline.execute(
    title="Financial Data",
    sections=[{"heading": "Q4 Numbers", "content": "..."}],
    datasets=[{"name": "revenue", "categories": ["Q1", "Q2"], "series": [...]}],
    output_path="data.xlsx",
)
```

### UnifiedDesignPipeline

The unified pipeline dispatches to the correct format-specific pipeline based on `output_type`:

```python
pipeline = tool_registry.create(
    "unified_design_pipeline",
    model="anthropic:claude-sonnet-4-5-20250929",
)

# Presentation
result = await pipeline.execute(output_type="presentation", title="Deck", sections=[...])

# Document
result = await pipeline.execute(output_type="document", title="Report", sections=[...])

# Spreadsheet
result = await pipeline.execute(output_type="spreadsheet", title="Data", sections=[...])
```

Dispatch mapping:

| `output_type` | Registry Key | Pipeline Class |
|--------------|-------------|---------------|
| `"presentation"` | `design_pipeline` | `DesignPipelineTool` |
| `"document"` | `document_design_pipeline` | `DocumentPipelineTool` |
| `"spreadsheet"` | `spreadsheet_design_pipeline` | `SpreadsheetPipelineTool` |

---

## Design Models

All design models are defined in `firefly_dworkers.design.models`:

### Input Models

| Model | Purpose |
|-------|---------|
| `ContentBrief` | Top-level input with content, context, and datasets |
| `ContentSection` | A section of content within a brief |
| `DataSet` | Chart data with categories and series |
| `DataSeries` | A named series of values |
| `ImageRequest` | Request for an image from various sources |
| `KeyMetric` | A KPI with label, value, and optional change indicator |

### Design DNA

| Model | Purpose |
|-------|---------|
| `DesignProfile` | Colors, fonts, layouts, margins extracted from templates |
| `LayoutZone` | Placeholder positions for a single slide layout |
| `PlaceholderZone` | Position and size of a single placeholder |

### Design Output

| Model | Purpose |
|-------|---------|
| `DesignSpec` | Complete blueprint with slides/sections/sheets/charts/images |
| `SlideDesign` | Design for a single slide (layout, title, content blocks) |
| `SectionDesign` | Design for a document section (heading, content, table) |
| `SheetDesign` | Design for a spreadsheet sheet (headers, rows, formatting) |
| `ResolvedChart` | Fully resolved chart with type, data, and colors |
| `ResolvedImage` | Image bytes ready for embedding |

### Shared Models

| Model | Purpose |
|-------|---------|
| `TextStyle` | Typography: font, size, bold, italic, color, alignment |
| `StyledTable` | Table data with header/cell styling |
| `ContentBlock` | Content unit: text, bullets, metric, or callout |
| `ImagePlacement` | Image position and sizing |
| `OutputType` | Enum: PRESENTATION, DOCUMENT, SPREADSHEET, PDF |

---

## Autonomy and Checkpoints

Pipeline tools integrate with the autonomy system to allow human review at critical decision points. Three checkpoints are defined:

| Checkpoint | When | Data Exposed |
|------------|------|-------------|
| `design_spec_approval` | After DesignEngine produces the DesignSpec | Slide/section/sheet count, chart types, layout choices |
| `pre_render` | Before rendering begins | Spec summary, output path |
| `deliverable` | After successful rendering | Output path, file size |

The autonomy level controls checkpoint behavior:

| Level | Behavior |
|-------|----------|
| `AUTONOMOUS` | Skips all checkpoints |
| `SUPERVISED` | Pauses at all checkpoints for approval |
| `INTERACTIVE` | Pauses and allows editing |

See [Autonomy Overview](autonomy/overview.md) for details.

---

## Image Resolution

The `ImageResolver` resolves `ImageRequest` objects to `ResolvedImage` with actual bytes. Four source types are supported:

| Source Type | Description |
|-------------|-------------|
| `file` | Reads bytes from a local file path |
| `url` | Fetches bytes over HTTP |
| `ai_generate` | AI image generation (extensible) |
| `stock` | Stock photo API search (extensible) |

```python
from firefly_dworkers.design.images import ImageResolver

resolver = ImageResolver(ai_api_key="...", stock_api_key="...")
images = await resolver.resolve_all(brief.image_requests)
```

---

## LLM Integration

The design pipeline uses `pydantic_ai` agents for structured LLM output:

- **Profile generation** -- `Agent[None, DesignProfile]` creates design profiles from content context
- **Layout design** -- `Agent[None, DesignSpec]` creates the full layout structure
- **Chart type selection** -- optional `Agent[None, str]` for ambiguous chart cases (heuristics handle most)

The model can be any `pydantic_ai`-compatible model string (e.g., `"anthropic:claude-sonnet-4-5-20250929"`, `"openai:gpt-5.2"`).

---

## Usage Examples

### Full Presentation Pipeline

```python
from firefly_dworkers.tools.registry import tool_registry

# Ensure pipeline tools are imported (triggers registration)
import firefly_dworkers.tools.presentation.pipeline  # noqa
import firefly_dworkers.tools.design_pipeline  # noqa

pipeline = tool_registry.create(
    "unified_design_pipeline",
    model="anthropic:claude-sonnet-4-5-20250929",
    vlm_model="anthropic:claude-sonnet-4-5-20250929",
)

result = await pipeline.execute(
    output_type="presentation",
    title="Q4 Business Review",
    sections=[
        {
            "heading": "Executive Summary",
            "content": "Strong quarter with 15% revenue growth.",
            "key_metrics": [
                {"label": "Revenue", "value": "$4.2M", "change": "+15%"},
                {"label": "Customers", "value": "1,247", "change": "+8%"},
            ],
        },
        {
            "heading": "Market Analysis",
            "content": "Three new markets entered successfully.",
            "bullet_points": ["LATAM: $800K", "APAC: $1.2M"],
            "chart_ref": "market_data",
        },
    ],
    datasets=[
        {
            "name": "market_data",
            "categories": ["LATAM", "APAC", "EMEA"],
            "series": [{"name": "Revenue", "values": [800, 1200, 600]}],
        },
    ],
    template_path="brand_template.pptx",
    output_path="q4_review.pptx",
)
```

### Document with PDF Output

```python
result = await pipeline.execute(
    output_type="document",
    title="Annual Report 2025",
    sections=[
        {"heading": "Letter to Shareholders", "content": "..."},
        {"heading": "Financial Highlights", "content": "...", "chart_ref": "financials"},
    ],
    output_format="pdf",
    output_path="annual_report.pdf",
)
```

### Spreadsheet with Charts

```python
result = await pipeline.execute(
    output_type="spreadsheet",
    title="Financial Dashboard",
    sections=[
        {"heading": "Revenue by Region", "content": "Regional breakdown..."},
    ],
    datasets=[
        {
            "name": "regions",
            "categories": ["North", "South", "East", "West"],
            "series": [
                {"name": "2024", "values": [1.2, 0.8, 1.5, 0.9]},
                {"name": "2025", "values": [1.4, 1.0, 1.8, 1.1]},
            ],
        },
    ],
    output_path="dashboard.xlsx",
)
```

---

## Related Documentation

- [Architecture](architecture.md) -- Hexagonal architecture and layer overview
- [Tools Overview](tools/overview.md) -- Tool system and port/adapter pattern
- [Tool Registry](tools/registry.md) -- Tool registration and creation
- [Autonomy Overview](autonomy/overview.md) -- Autonomy levels and checkpointing
- [Workers](workers/overview.md) -- Workers that produce ContentBriefs
