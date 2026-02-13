from __future__ import annotations

import pytest

from firefly_dworkers.verticals.base import get_vertical, list_verticals


class TestVerticals:
    def test_list_verticals(self):
        names = list_verticals()
        assert "technology" in names
        assert "healthcare" in names
        assert "banking" in names
        assert "legal" in names
        assert "gaming" in names
        assert "consumer" in names
        assert len(names) == 6

    def test_get_vertical(self):
        v = get_vertical("technology")
        assert v.name == "technology"
        assert v.display_name != ""
        assert len(v.focus_areas) > 0
        assert v.system_prompt_fragment != ""

    def test_get_unknown_vertical(self):
        from firefly_dworkers.exceptions import VerticalNotFoundError

        with pytest.raises(VerticalNotFoundError):
            get_vertical("nonexistent")

    def test_vertical_prompt_fragments_nonempty(self):
        for name in list_verticals():
            v = get_vertical(name)
            assert v.system_prompt_fragment, f"Vertical '{name}' has empty prompt fragment"
