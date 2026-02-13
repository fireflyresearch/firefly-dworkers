"""Prompt loader -- scans .j2 files and registers them with the framework PromptRegistry."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fireflyframework_genai.prompts.registry import prompt_registry
from fireflyframework_genai.prompts.template import PromptTemplate

logger = logging.getLogger(__name__)

# Directory containing the .j2 template files (sibling to this module)
_PROMPTS_DIR = Path(__file__).resolve().parent

# Mapping from directory name (plural) to registry prefix (singular)
_CATEGORY_PREFIX: dict[str, str] = {
    "workers": "worker",
}


def _path_to_registry_key(path: Path, base_dir: Path) -> str:
    """Convert a .j2 file path to a registry key.

    ``workers/analyst.j2`` relative to *base_dir* becomes ``worker/analyst``.
    """
    relative = path.relative_to(base_dir)
    parts = list(relative.parts)

    # Replace the top-level directory with its singular form if mapped
    if parts and parts[0] in _CATEGORY_PREFIX:
        parts[0] = _CATEGORY_PREFIX[parts[0]]

    # Remove the .j2 extension from the final part
    parts[-1] = re.sub(r"\.j2$", "", parts[-1])

    return "/".join(parts)


class PromptLoader:
    """Scans the prompts directory for .j2 files and registers them.

    The loader is idempotent -- calling :meth:`load` multiple times will
    silently re-register templates without raising errors.
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._loaded = False
        self._keys: list[str] = []

    def load(self) -> list[str]:
        """Scan for .j2 files, register each as a PromptTemplate, and return the keys."""
        if self._loaded:
            return list(self._keys)

        registered: list[str] = []

        for j2_path in sorted(self._prompts_dir.rglob("*.j2")):
            if not j2_path.is_file():
                continue

            key = _path_to_registry_key(j2_path, self._prompts_dir)
            template_str = j2_path.read_text(encoding="utf-8")

            template = PromptTemplate(
                name=key,
                template_str=template_str,
                description=f"Prompt template loaded from {j2_path.name}",
            )
            prompt_registry.register(template)
            registered.append(key)
            logger.debug("Registered prompt template '%s' from %s", key, j2_path)

        self._keys = registered
        self._loaded = True
        logger.info("Loaded %d prompt templates", len(registered))
        return registered
