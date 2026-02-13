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
