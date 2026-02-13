from __future__ import annotations

from dataclasses import dataclass, field

from firefly_dworkers.exceptions import VerticalNotFoundError

_REGISTRY: dict[str, VerticalConfig] = {}


@dataclass(frozen=True)
class VerticalConfig:
    name: str
    display_name: str
    focus_areas: list[str]
    system_prompt_fragment: str
    keywords: list[str] = field(default_factory=list)


def register_vertical(config: VerticalConfig) -> None:
    _REGISTRY[config.name] = config


def get_vertical(name: str) -> VerticalConfig:
    if name not in _REGISTRY:
        raise VerticalNotFoundError(
            f"Vertical '{name}' not found. Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_verticals() -> list[str]:
    return sorted(_REGISTRY.keys())
