from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

HEALTHCARE = VerticalConfig(
    name="healthcare",
    display_name="Healthcare",
    focus_areas=[
        "Strategy and policy consulting",
        "Patient data analysis and outcomes",
        "Operational efficiency and workflow optimization",
        "Regulatory compliance (HIPAA, FDA)",
        "Clinical workflow improvement",
    ],
    system_prompt_fragment=(
        "You are working in the Healthcare consulting vertical. "
        "Focus on healthcare strategy, patient outcomes, operational efficiency, "
        "and regulatory compliance. Reference HIPAA, FDA regulations, and "
        "clinical best practices. Use terminology appropriate for healthcare "
        "executives (CMO, CNO, VP Clinical Operations) and ensure sensitivity "
        "to patient privacy and safety considerations."
    ),
    keywords=[
        "HIPAA",
        "FDA",
        "patient outcomes",
        "clinical workflows",
        "EHR",
        "telehealth",
        "population health",
    ],
)
register_vertical(HEALTHCARE)
