"""Test DworkersApp shell."""

from firefly_dworkers_cli.tui.app import DworkersApp


class TestDworkersApp:
    def test_app_instantiates(self):
        app = DworkersApp()
        assert app.TITLE == "dworkers"
        assert app.current_screen_id == "conversations"

    def test_sections_defined(self):
        app = DworkersApp()
        assert "WORKSPACE" in app.SECTIONS
        assert "TEMPLATES" in app.SECTIONS
        assert "MANAGE" in app.SECTIONS
