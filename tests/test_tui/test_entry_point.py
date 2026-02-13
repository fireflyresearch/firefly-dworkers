"""Test TUI entry point integration."""

from firefly_dworkers_cli.tui import DworkersApp


def test_tui_importable():
    """The TUI app can be imported from the package."""
    assert DworkersApp is not None
    app = DworkersApp()
    assert app.TITLE == "dworkers"
