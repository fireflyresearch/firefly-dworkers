"""Jinja2 prompt management system for firefly-dworkers.

Public API
----------
- :func:`load_prompts` -- scan and register all .j2 templates
- :func:`get_worker_prompt` -- render a worker prompt by role name
- :func:`get_skill_prompt` -- render a skill prompt by name
"""

from __future__ import annotations

from fireflyframework_genai.prompts.registry import prompt_registry

from firefly_dworkers.prompts.loader import PromptLoader

__all__ = ["get_skill_prompt", "get_worker_prompt", "load_prompts"]

_loader = PromptLoader()


def load_prompts() -> list[str]:
    """Scan the prompts directory and register all .j2 templates.

    This function is idempotent -- calling it multiple times will silently
    re-register templates without raising errors.

    Returns a list of registered template keys.
    """
    return _loader.load()


def get_worker_prompt(role: str, **kwargs: str) -> str:
    """Render and return the worker prompt for *role*.

    Parameters
    ----------
    role:
        Worker role name (e.g. ``"analyst"``, ``"researcher"``).
    **kwargs:
        Template variables such as ``company_name``, ``verticals``,
        ``custom_instructions``, ``skills``, ``tools``.

    Raises
    ------
    KeyError
        If no template is registered for the given role.
    """
    key = f"worker/{role}"
    if not prompt_registry.has(key):
        raise KeyError(f"No worker prompt template registered for role '{role}' (key='{key}')")
    template = prompt_registry.get(key)
    return template.render(**kwargs)


def get_skill_prompt(skill_name: str, **kwargs: str) -> str:
    """Render and return a skill prompt by name.

    Parameters
    ----------
    skill_name:
        Skill name (e.g. ``"powerpoint"``, ``"word"``).
    **kwargs:
        Template variables.

    Raises
    ------
    KeyError
        If no skill prompt template is registered for the given name.
    """
    key = f"skill/{skill_name}"
    if not prompt_registry.has(key):
        raise KeyError(f"No skill prompt template registered for '{skill_name}' (key='{key}')")
    template = prompt_registry.get(key)
    return template.render(**kwargs)
