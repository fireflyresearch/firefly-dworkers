from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

CONSUMER = VerticalConfig(
    name="consumer",
    display_name="Consumer Products & Retail",
    focus_areas=[
        "Market entry and growth strategy",
        "Consumer behavior and trend analysis",
        "Brand management and positioning",
        "Retail strategy and channel optimization",
        "E-commerce and direct-to-consumer",
    ],
    system_prompt_fragment=(
        "You are working in the Consumer Products & Retail consulting vertical. "
        "Focus on market entry, consumer behavior, brand management, retail "
        "strategy, and e-commerce optimization. Reference industry metrics "
        "(market share, NPS, CAC, CLV, basket size) and retail frameworks. "
        "Use terminology appropriate for consumer executives (CMO, VP Marketing, "
        "Head of Retail) and maintain awareness of consumer trends, omnichannel "
        "strategies, and direct-to-consumer models."
    ),
    keywords=[
        "market entry",
        "consumer behavior",
        "brand management",
        "retail",
        "e-commerce",
        "DTC",
        "omnichannel",
    ],
)
register_vertical(CONSUMER)
