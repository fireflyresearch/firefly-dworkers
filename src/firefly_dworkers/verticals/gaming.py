from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

GAMING = VerticalConfig(
    name="gaming",
    display_name="Gaming & Entertainment",
    focus_areas=[
        "Market entry and competitive analysis",
        "Consumer behavior and player analytics",
        "User engagement and retention strategy",
        "Monetization strategy and optimization",
        "Content strategy and IP development",
    ],
    system_prompt_fragment=(
        "You are working in the Gaming & Entertainment consulting vertical. "
        "Focus on market entry, consumer behavior analysis, user engagement, "
        "monetization strategy, and content strategy. Reference gaming industry "
        "metrics (DAU, MAU, ARPU, LTV, retention curves) and platform-specific "
        "considerations. Use terminology appropriate for gaming executives "
        "(Head of Product, VP Publishing, Creative Director) and stay current "
        "with industry trends in mobile, console, and PC gaming."
    ),
    keywords=[
        "user engagement",
        "monetization",
        "player analytics",
        "game design",
        "live ops",
        "esports",
        "content strategy",
    ],
)
register_vertical(GAMING)
