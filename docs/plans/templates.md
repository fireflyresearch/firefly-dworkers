# Plan Templates

firefly-dworkers includes four built-in plan templates for common consulting engagements. Each template defines a DAG of steps with worker role assignments and dependency chains.

All templates are registered automatically when importing `firefly_dworkers.plans.templates`.

---

## Market Analysis

**Name:** `market-analysis`
**Module:** `firefly_dworkers.plans.templates.market_analysis`
**Description:** Research competitors, analyze market size, and generate strategy report.

### Steps

| Step | Worker | Dependencies | Description |
|------|--------|-------------|-------------|
| `define-scope` | Analyst | — | Define target markets, geographies, and competitive landscape boundaries |
| `research-competitors` | Researcher | define-scope | Research key competitors, their offerings, strengths, and weaknesses |
| `analyze-market-data` | Data Analyst | define-scope | Analyze market size, growth rates, and demographic trends |
| `assess-opportunities` | Analyst | research-competitors, analyze-market-data | Identify market gaps and strategic opportunities |
| `strategy-report` | Analyst | assess-opportunities | Compile findings into a comprehensive market strategy report |
| `executive-review` | Manager | strategy-report | Review strategy report and coordinate executive presentation |

### DAG

```
define-scope
    ├── research-competitors ──┐
    └── analyze-market-data ───┤
                               ▼
                    assess-opportunities
                               │
                        strategy-report
                               │
                      executive-review
```

---

## Customer Segmentation

**Name:** `customer-segmentation`
**Module:** `firefly_dworkers.plans.templates.customer_segmentation`
**Description:** Analyze customer data to identify segments and develop targeting strategies.

### Steps

| Step | Worker | Dependencies | Description |
|------|--------|-------------|-------------|
| `gather-requirements` | Analyst | — | Collect business objectives, data sources, and segmentation criteria |
| `research-market` | Researcher | gather-requirements | Research industry benchmarks and segmentation best practices |
| `analyze-data` | Data Analyst | gather-requirements | Analyze customer data, build segments, generate statistical profiles |
| `synthesize-report` | Analyst | research-market, analyze-data | Combine market research and data analysis into actionable recommendations |
| `project-review` | Manager | synthesize-report | Review deliverables and coordinate stakeholder feedback |

### DAG

```
gather-requirements
    ├── research-market ──┐
    └── analyze-data ─────┤
                          ▼
                 synthesize-report
                          │
                    project-review
```

---

## Process Improvement

**Name:** `process-improvement`
**Module:** `firefly_dworkers.plans.templates.process_improvement`
**Description:** Map current processes, identify gaps, and propose improvements.

### Steps

| Step | Worker | Dependencies | Description |
|------|--------|-------------|-------------|
| `map-current-processes` | Analyst | — | Document existing workflows, inputs/outputs, and process flows |
| `research-best-practices` | Researcher | map-current-processes | Research industry best practices and benchmark against peers |
| `analyze-process-data` | Data Analyst | map-current-processes | Analyze cycle times, throughput, error rates, and bottleneck metrics |
| `identify-improvements` | Analyst | research-best-practices, analyze-process-data | Synthesize research and data to identify improvement opportunities |
| `improvement-report` | Analyst | identify-improvements | Compile recommendations with ROI projections and implementation roadmap |
| `stakeholder-review` | Manager | improvement-report | Present findings, gather feedback, and coordinate implementation |

### DAG

```
map-current-processes
    ├── research-best-practices ──┐
    └── analyze-process-data ─────┤
                                  ▼
                      identify-improvements
                                  │
                        improvement-report
                                  │
                       stakeholder-review
```

---

## Technology Assessment

**Name:** `technology-assessment`
**Module:** `firefly_dworkers.plans.templates.technology_assessment`
**Description:** Assess current technology, research alternatives, and build recommendations.

### Steps

| Step | Worker | Dependencies | Description |
|------|--------|-------------|-------------|
| `assess-current-tech` | Analyst | — | Audit existing technology stack, integrations, and capabilities |
| `research-alternatives` | Researcher | assess-current-tech | Research alternative technologies, vendors, and emerging solutions |
| `analyze-tech-data` | Data Analyst | assess-current-tech | Analyze performance metrics, cost data, and usage patterns |
| `build-recommendations` | Analyst | research-alternatives, analyze-tech-data | Synthesize research and data into technology recommendations |
| `assessment-report` | Analyst | build-recommendations | Compile findings into a technology assessment report with migration plan |
| `governance-review` | Manager | assessment-report | Review assessment with governance board and coordinate approval |

### DAG

```
assess-current-tech
    ├── research-alternatives ──┐
    └── analyze-tech-data ──────┤
                                ▼
                    build-recommendations
                                │
                       assessment-report
                                │
                       governance-review
```

---

## Common Patterns

All four templates share a consistent three-phase structure:

1. **Discovery** — An Analyst scopes the work, then Researcher and Data Analyst work in parallel
2. **Synthesis** — An Analyst combines the parallel findings into recommendations
3. **Review** — A Manager reviews the final deliverable and coordinates stakeholders

This pattern maximizes parallelism during the discovery phase while maintaining quality through convergence and management review.
