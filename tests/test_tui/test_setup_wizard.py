"""Tests for setup wizard screens."""

from __future__ import annotations


class TestWelcomeScreen:
    def test_welcome_screen_exists(self):
        from firefly_dworkers_cli.tui.screens.setup import WelcomeScreen
        screen = WelcomeScreen()
        assert screen is not None


class TestAboutYouScreen:
    def test_about_you_screen_exists(self):
        from firefly_dworkers_cli.tui.screens.setup import AboutYouScreen
        screen = AboutYouScreen()
        assert screen is not None


class TestMeetTheTeamScreen:
    def test_meet_the_team_exists(self):
        from firefly_dworkers_cli.tui.screens.setup import MeetTheTeamScreen
        screen = MeetTheTeamScreen()
        assert screen is not None

    def test_meet_the_team_with_user_name(self):
        from firefly_dworkers_cli.tui.screens.setup import MeetTheTeamScreen
        screen = MeetTheTeamScreen(user_name="Antonio")
        assert screen._user_name == "Antonio"
