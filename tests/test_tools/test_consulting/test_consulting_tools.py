"""Tests for consulting tools."""

from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.consulting.documentation import DocumentationTool
from firefly_dworkers.tools.consulting.gap_analysis import GapAnalysisTool
from firefly_dworkers.tools.consulting.process_mapping import ProcessMappingTool
from firefly_dworkers.tools.consulting.report_generation import ReportGenerationTool
from firefly_dworkers.tools.consulting.requirement_gathering import RequirementGatheringTool

# ---------------------------------------------------------------------------
# RequirementGatheringTool
# ---------------------------------------------------------------------------


class TestRequirementGatheringTool:
    def test_instantiation(self):
        tool = RequirementGatheringTool()
        assert tool is not None

    def test_name(self):
        assert RequirementGatheringTool().name == "requirement_gathering"

    def test_tags(self):
        tags = RequirementGatheringTool().tags
        assert "consulting" in tags
        assert "requirements" in tags

    def test_is_base_tool(self):
        assert isinstance(RequirementGatheringTool(), BaseTool)

    async def test_extract_functional_requirement(self):
        tool = RequirementGatheringTool()
        notes = "The system must allow users to log in. Users should be able to reset passwords."
        result = await tool.execute(notes=notes, project_name="Auth System")
        assert result["project"] == "Auth System"
        assert result["total_count"] >= 1
        assert "functional" in result["requirements"]
        assert len(result["requirements"]["functional"]) >= 1

    async def test_extract_non_functional_requirement(self):
        tool = RequirementGatheringTool()
        notes = "The system must have 99.9% uptime. Performance should be under 200ms."
        result = await tool.execute(notes=notes)
        assert result["total_count"] >= 1
        assert len(result["requirements"]["non-functional"]) >= 1

    async def test_extract_constraints(self):
        tool = RequirementGatheringTool()
        notes = "Budget cannot exceed $50k. The deadline is Q4 2026."
        result = await tool.execute(notes=notes)
        assert len(result["requirements"]["constraints"]) >= 1

    async def test_structured_output(self):
        tool = RequirementGatheringTool()
        result = await tool.execute(notes="Some notes without requirements.")
        assert "requirements" in result
        assert "total_count" in result
        assert "source_sentences" in result
        assert "categories" in result

    def test_parameters(self):
        tool = RequirementGatheringTool()
        param_names = [p.name for p in tool.parameters]
        assert "notes" in param_names
        assert "project_name" in param_names
        assert "categories" in param_names

    def test_config_params(self):
        tool = RequirementGatheringTool(
            default_categories="must-have,nice-to-have",
            functional_keywords=["must", "shall"],
            nonfunctional_keywords=["performance"],
            constraint_keywords=["budget"],
            sentence_split_pattern=r"[;\n]",
        )
        assert tool._default_categories == "must-have,nice-to-have"
        assert tool._functional_kw == ("must", "shall")
        assert tool._nonfunctional_kw == ("performance",)
        assert tool._constraint_kw == ("budget",)
        assert tool._split_pattern == r"[;\n]"

    async def test_custom_keywords(self):
        tool = RequirementGatheringTool(
            functional_keywords=["critical"],
            constraint_keywords=["forbidden"],
        )
        notes = "This feature is critical for launch. Using Java is forbidden."
        result = await tool.execute(notes=notes)
        assert result["total_count"] >= 1

    async def test_custom_split_pattern(self):
        tool = RequirementGatheringTool(sentence_split_pattern=r";")
        notes = "System must handle 1000 users;Budget cannot exceed $10k"
        result = await tool.execute(notes=notes)
        assert result["source_sentences"] == 2


# ---------------------------------------------------------------------------
# ProcessMappingTool
# ---------------------------------------------------------------------------


class TestProcessMappingTool:
    def test_instantiation(self):
        tool = ProcessMappingTool()
        assert tool is not None

    def test_name(self):
        assert ProcessMappingTool().name == "process_mapping"

    def test_tags(self):
        tags = ProcessMappingTool().tags
        assert "consulting" in tags
        assert "process" in tags

    def test_is_base_tool(self):
        assert isinstance(ProcessMappingTool(), BaseTool)

    async def test_extract_steps(self):
        tool = ProcessMappingTool()
        desc = "The manager reviews the request. The team performs the analysis. The client approves the result."
        result = await tool.execute(description=desc, process_name="Review Process")
        assert result["process_name"] == "Review Process"
        assert result["step_count"] >= 3
        assert len(result["steps"]) >= 3

    async def test_extract_actors(self):
        tool = ProcessMappingTool()
        desc = "The manager reviews the proposal. The engineer creates the design."
        result = await tool.execute(description=desc)
        assert len(result["actors"]) >= 1

    async def test_structured_output(self):
        tool = ProcessMappingTool()
        result = await tool.execute(description="Step one. Step two.")
        assert "steps" in result
        assert "step_count" in result
        assert "actors" in result
        assert "process_name" in result

    def test_parameters(self):
        tool = ProcessMappingTool()
        param_names = [p.name for p in tool.parameters]
        assert "description" in param_names
        assert "process_name" in param_names

    def test_config_params(self):
        tool = ProcessMappingTool(
            actor_verbs=["runs", "handles"],
            step_split_pattern=r";",
            default_process_name="Default Flow",
        )
        assert tool._actor_verbs == ("runs", "handles")
        assert tool._step_split_pattern == ";"
        assert tool._default_process_name == "Default Flow"

    async def test_custom_actor_verbs(self):
        tool = ProcessMappingTool(actor_verbs=["handles", "manages"])
        desc = "The coordinator handles intake. The lead manages delivery."
        result = await tool.execute(description=desc)
        assert len(result["actors"]) >= 1

    async def test_custom_split_pattern(self):
        tool = ProcessMappingTool(step_split_pattern=r";")
        desc = "Step A;Step B;Step C"
        result = await tool.execute(description=desc)
        assert result["step_count"] == 3


# ---------------------------------------------------------------------------
# GapAnalysisTool
# ---------------------------------------------------------------------------


class TestGapAnalysisTool:
    def test_instantiation(self):
        tool = GapAnalysisTool()
        assert tool is not None

    def test_name(self):
        assert GapAnalysisTool().name == "gap_analysis"

    def test_tags(self):
        tags = GapAnalysisTool().tags
        assert "consulting" in tags
        assert "analysis" in tags

    def test_is_base_tool(self):
        assert isinstance(GapAnalysisTool(), BaseTool)

    async def test_identify_gaps(self):
        tool = GapAnalysisTool()
        result = await tool.execute(
            current_state="Manual data entry\nBasic reporting",
            desired_state="Automated data entry\nAdvanced analytics\nBasic reporting",
            domain="operations",
        )
        assert result["domain"] == "operations"
        assert result["gap_count"] >= 1
        assert result["covered_count"] >= 1

    async def test_structured_output(self):
        tool = GapAnalysisTool()
        result = await tool.execute(current_state="A", desired_state="B")
        assert "gaps" in result
        assert "gap_count" in result
        assert "covered_count" in result
        assert "surplus_count" in result
        assert "domain" in result

    def test_parameters(self):
        tool = GapAnalysisTool()
        param_names = [p.name for p in tool.parameters]
        assert "current_state" in param_names
        assert "desired_state" in param_names
        assert "domain" in param_names

    def test_config_params(self):
        tool = GapAnalysisTool(
            default_severity="critical",
            default_domain="infrastructure",
            recommendation_template="Fix: {item}",
            item_split_pattern=r";",
            case_sensitive=True,
        )
        assert tool._default_severity == "critical"
        assert tool._default_domain == "infrastructure"
        assert tool._recommendation_template == "Fix: {item}"
        assert tool._split_pattern == ";"
        assert tool._case_sensitive is True

    async def test_custom_severity(self):
        tool = GapAnalysisTool(default_severity="high")
        result = await tool.execute(current_state="A", desired_state="B")
        if result["gaps"]:
            assert result["gaps"][0]["severity"] == "high"

    async def test_custom_recommendation_template(self):
        tool = GapAnalysisTool(recommendation_template="TODO: resolve {item}")
        result = await tool.execute(current_state="A", desired_state="B")
        if result["gaps"]:
            assert result["gaps"][0]["recommendation"].startswith("TODO: resolve")

    async def test_case_sensitive_comparison(self):
        tool = GapAnalysisTool(case_sensitive=True)
        result = await tool.execute(current_state="Item A", desired_state="item a")
        # Case-sensitive: "Item A" != "item a", so both appear as gaps/surplus
        assert result["gap_count"] >= 1
        assert result["surplus_count"] >= 1


# ---------------------------------------------------------------------------
# ReportGenerationTool
# ---------------------------------------------------------------------------


class TestReportGenerationTool:
    def test_instantiation(self):
        tool = ReportGenerationTool()
        assert tool is not None

    def test_name(self):
        assert ReportGenerationTool().name == "report_generation"

    def test_tags(self):
        tags = ReportGenerationTool().tags
        assert "consulting" in tags
        assert "reporting" in tags

    def test_is_base_tool(self):
        assert isinstance(ReportGenerationTool(), BaseTool)

    async def test_markdown_format(self):
        tool = ReportGenerationTool()
        result = await tool.execute(title="Executive Summary", data="The project is on track.")
        assert result["format"] == "markdown"
        assert "## Executive Summary" in result["content"]
        assert "The project is on track." in result["content"]

    async def test_json_format(self):
        tool = ReportGenerationTool()
        result = await tool.execute(title="Summary", data="All good.", format="json")
        assert result["format"] == "json"
        assert result["content"]["title"] == "Summary"
        assert result["content"]["body"] == "All good."

    async def test_text_format(self):
        tool = ReportGenerationTool()
        result = await tool.execute(title="Summary", data="Content here.", format="text")
        assert result["format"] == "text"
        assert "Summary" in result["content"]
        assert "=" in result["content"]

    def test_parameters(self):
        tool = ReportGenerationTool()
        param_names = [p.name for p in tool.parameters]
        assert "title" in param_names
        assert "data" in param_names
        assert "format" in param_names

    def test_config_params(self):
        tool = ReportGenerationTool(
            default_format="text",
            markdown_heading_level=3,
            text_underline_char="-",
        )
        assert tool._default_format == "text"
        assert tool._md_heading_level == 3
        assert tool._text_underline_char == "-"

    async def test_custom_heading_level(self):
        tool = ReportGenerationTool(markdown_heading_level=3)
        result = await tool.execute(title="Summary", data="Content")
        assert result["content"].startswith("### Summary")

    async def test_custom_underline_char(self):
        tool = ReportGenerationTool(text_underline_char="-")
        result = await tool.execute(title="Summary", data="Content", format="text")
        assert "-------" in result["content"]

    async def test_heading_level_clamped(self):
        """Heading level should be clamped between 1 and 6."""
        tool = ReportGenerationTool(markdown_heading_level=10)
        assert tool._md_heading_level == 6
        tool2 = ReportGenerationTool(markdown_heading_level=0)
        assert tool2._md_heading_level == 1


# ---------------------------------------------------------------------------
# DocumentationTool
# ---------------------------------------------------------------------------


class TestDocumentationTool:
    def test_instantiation(self):
        tool = DocumentationTool()
        assert tool is not None

    def test_name(self):
        assert DocumentationTool().name == "documentation"

    def test_tags(self):
        tags = DocumentationTool().tags
        assert "consulting" in tags
        assert "documentation" in tags

    def test_is_base_tool(self):
        assert isinstance(DocumentationTool(), BaseTool)

    async def test_generate_charter(self):
        tool = DocumentationTool()
        result = await tool.execute(
            doc_type="charter",
            title="Project Alpha",
            sections="Build the platform|Deliver MVP by Q3",
            author="Jane Doe",
        )
        assert result["doc_type"] == "charter"
        assert result["title"] == "Project Alpha"
        assert result["section_count"] == 2
        assert result["format"] == "markdown"
        assert "# Project Alpha" in result["document"]
        assert "**Author:** Jane Doe" in result["document"]
        assert "## Overview" in result["document"]

    async def test_generate_sow(self):
        tool = DocumentationTool()
        result = await tool.execute(
            doc_type="sow",
            title="SOW: Data Migration",
            sections="Migrate legacy DB|New schema design|Data validation",
        )
        assert result["section_count"] == 3
        assert "## Introduction" in result["document"]

    async def test_generate_unknown_type(self):
        tool = DocumentationTool()
        result = await tool.execute(
            doc_type="custom",
            title="Custom Doc",
            sections="First|Second",
        )
        assert result["section_count"] == 2
        assert "## Section 1" in result["document"]
        assert "## Section 2" in result["document"]

    async def test_structured_output(self):
        tool = DocumentationTool()
        result = await tool.execute(doc_type="meeting_notes", title="Standup", sections="Team met")
        assert "document" in result
        assert "doc_type" in result
        assert "title" in result
        assert "section_count" in result
        assert "format" in result

    def test_parameters(self):
        tool = DocumentationTool()
        param_names = [p.name for p in tool.parameters]
        assert "doc_type" in param_names
        assert "title" in param_names
        assert "sections" in param_names
        assert "author" in param_names

    def test_config_params(self):
        tool = DocumentationTool(
            section_templates={"custom_type": ["Intro", "Details", "Wrap-up"]},
            section_separator=";",
            default_author="System",
            heading_level=3,
        )
        assert "custom_type" in tool._templates
        assert tool._templates["custom_type"] == ["Intro", "Details", "Wrap-up"]
        # Built-in templates are preserved
        assert "charter" in tool._templates
        assert tool._separator == ";"
        assert tool._default_author == "System"
        assert tool._heading_level == 3

    async def test_custom_section_separator(self):
        tool = DocumentationTool(section_separator=";")
        result = await tool.execute(
            doc_type="charter",
            title="Test",
            sections="Overview here;Goals here",
        )
        assert result["section_count"] == 2

    async def test_custom_templates(self):
        tool = DocumentationTool(
            section_templates={"proposal": ["Background", "Approach", "Budget"]},
        )
        result = await tool.execute(
            doc_type="proposal",
            title="My Proposal",
            sections="Context|Our plan|$100k",
        )
        assert "## Background" in result["document"]
        assert "## Approach" in result["document"]
        assert "## Budget" in result["document"]

    async def test_custom_heading_level(self):
        tool = DocumentationTool(heading_level=3)
        result = await tool.execute(
            doc_type="charter",
            title="Test",
            sections="Intro content",
        )
        assert "### Overview" in result["document"]

    async def test_default_author_config(self):
        tool = DocumentationTool(default_author="Bot")
        result = await tool.execute(
            doc_type="charter",
            title="Test",
            sections="Content",
        )
        assert "**Author:** Bot" in result["document"]
