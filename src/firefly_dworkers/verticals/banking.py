from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

BANKING = VerticalConfig(
    name="banking",
    display_name="Banking & Financial Services",
    focus_areas=[
        "Financial strategy and planning",
        "Regulatory compliance (Basel III, PSD2)",
        "Fraud detection and prevention",
        "Risk management and assessment",
        "Fintech integration and innovation",
    ],
    system_prompt_fragment=(
        "You are working in the Banking & Financial Services consulting vertical. "
        "Focus on financial strategy, regulatory compliance, fraud detection, "
        "risk management, and fintech integration. Reference frameworks like "
        "Basel III, PSD2, AML/KYC requirements, and IFRS standards. Use "
        "terminology appropriate for banking executives (CFO, CRO, Head of "
        "Compliance) and maintain awareness of evolving financial regulations."
    ),
    keywords=[
        "Basel III",
        "PSD2",
        "AML",
        "KYC",
        "risk management",
        "fintech",
        "fraud detection",
    ],
)
register_vertical(BANKING)
