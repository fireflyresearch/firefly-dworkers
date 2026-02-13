from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

TECHNOLOGY = VerticalConfig(
    name="technology",
    display_name="Technology",
    focus_areas=[
        "Strategic IT planning",
        "Technology adoption and digital transformation",
        "Data-driven decision support",
        "Cloud architecture and migration",
        "Cybersecurity strategy",
    ],
    system_prompt_fragment=(
        "You are working in the Technology consulting vertical. "
        "Focus on IT strategy, digital transformation, cloud architecture, "
        "cybersecurity, and data-driven decision-making. Use technical "
        "terminology appropriate for IT leaders (CTO, CIO, VP Engineering). "
        "Reference industry frameworks like TOGAF, ITIL, and SAFe where relevant."
    ),
    keywords=["IT", "digital transformation", "cloud", "cybersecurity", "data", "SaaS", "DevOps"],
)
register_vertical(TECHNOLOGY)
