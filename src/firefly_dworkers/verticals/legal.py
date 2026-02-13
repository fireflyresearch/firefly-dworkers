from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

LEGAL = VerticalConfig(
    name="legal",
    display_name="Legal",
    focus_areas=[
        "Legal compliance and governance",
        "Contract management and analysis",
        "Regulatory research and monitoring",
        "Intellectual property strategy",
        "Litigation support and case analysis",
    ],
    system_prompt_fragment=(
        "You are working in the Legal consulting vertical. "
        "Focus on legal compliance, contract management, regulatory research, "
        "IP strategy, and litigation support. Reference relevant legal frameworks, "
        "case law precedents, and regulatory bodies. Use terminology appropriate "
        "for legal executives (General Counsel, CLO, Head of Legal) and maintain "
        "precision in legal language and citations."
    ),
    keywords=[
        "compliance",
        "contracts",
        "regulatory",
        "intellectual property",
        "litigation",
        "governance",
        "legal tech",
    ],
)
register_vertical(LEGAL)
