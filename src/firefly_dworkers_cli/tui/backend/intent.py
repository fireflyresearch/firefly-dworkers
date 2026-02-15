"""Hybrid intent classification for project vs quick-chat detection."""
from __future__ import annotations

import re

# Heuristic signal patterns
_PROJECT_KEYWORDS = {
    "report", "presentation", "dashboard", "document", "deliverable",
    "analysis", "analyze", "research", "plan", "strategy", "engagement",
    "project", "initiative", "assessment", "audit", "review",
}
_MULTI_STEP_PATTERNS = [
    r"\bfirst\b.*\bthen\b",
    r"\bstep\s*\d",
    r"\band\s+then\b",
    r"\bfinally\b",
    r"\bphase\s*\d",
    r"\bfollow(?:ed)?\s+by\b",
]
_DELIVERABLE_KEYWORDS = {
    "report", "presentation", "spreadsheet", "pdf", "document",
    "dashboard", "brief", "memo", "proposal", "deck",
}
_CHAT_STARTERS = {
    "what", "who", "where", "when", "why", "how", "is", "are",
    "can", "do", "does", "did", "will", "would", "could", "should",
    "hello", "hi", "hey", "thanks", "thank",
}

# Thresholds
_HIGH_THRESHOLD = 3
_LOW_THRESHOLD = -1


class IntentClassifier:
    """Classify user messages as quick-chat or project-worthy."""

    def heuristic_classify(self, text: str) -> str:
        """Fast keyword-based classification.

        Returns: "LOW" (quick chat), "HIGH" (project), or "AMBIGUOUS".
        """
        text_lower = text.lower().strip()
        words = set(re.findall(r"\b\w+\b", text_lower))

        score = 0

        # Project signals
        if words & _PROJECT_KEYWORDS:
            score += 2
        if words & _DELIVERABLE_KEYWORDS:
            score += 2
        if any(re.search(p, text_lower) for p in _MULTI_STEP_PATTERNS):
            score += 2
        if len(text) > 200:
            score += 1

        # Chat signals (reduce score)
        first_word = text_lower.split()[0] if text_lower else ""
        if first_word in _CHAT_STARTERS:
            score -= 1
        if len(text) < 50:
            score -= 1

        if score >= _HIGH_THRESHOLD:
            return "HIGH"
        if score <= _LOW_THRESHOLD:
            return "LOW"
        return "AMBIGUOUS"

    async def llm_classify(self, text: str, *, llm_call=None) -> str:
        """LLM-based classification for ambiguous cases."""
        if llm_call is None:
            return "CHAT"  # Safe fallback

        prompt = (
            "Classify this user request. Respond with exactly one word: CHAT or PROJECT\n\n"
            "CHAT = question, quick task, general conversation, single-step request\n"
            "PROJECT = multi-step work, deliverables, research + analysis, ongoing engagement\n\n"
            f'User request: "{text}"'
        )
        result = await llm_call(prompt)
        result = result.strip().upper()
        return "PROJECT" if "PROJECT" in result else "CHAT"

    async def classify(self, text: str, *, llm_call=None) -> str:
        """Hybrid classification: heuristic first, LLM fallback for ambiguous."""
        tier1 = self.heuristic_classify(text)
        if tier1 == "LOW":
            return "CHAT"
        if tier1 == "HIGH":
            return "PROJECT"
        return await self.llm_classify(text, llm_call=llm_call)
