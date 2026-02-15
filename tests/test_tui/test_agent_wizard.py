"""Tests for agent creation wizard screens."""
from __future__ import annotations


class TestAgentWizardScreens:
    def test_identity_screen_imports(self):
        from firefly_dworkers_cli.tui.screens.agent_wizard import AgentIdentityScreen
        screen = AgentIdentityScreen()
        assert screen is not None

    def test_mission_screen_imports(self):
        from firefly_dworkers_cli.tui.screens.agent_wizard import AgentMissionScreen
        screen = AgentMissionScreen()
        assert screen is not None

    def test_skills_screen_imports(self):
        from firefly_dworkers_cli.tui.screens.agent_wizard import AgentSkillsScreen
        screen = AgentSkillsScreen()
        assert screen is not None

    def test_confirm_screen_imports(self):
        from firefly_dworkers_cli.tui.screens.agent_wizard import AgentConfirmScreen
        assert AgentConfirmScreen is not None
