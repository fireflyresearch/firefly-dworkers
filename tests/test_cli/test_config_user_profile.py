"""Tests for user profile in ConfigManager."""

from __future__ import annotations

import pytest

from firefly_dworkers_cli.config import ConfigManager


class TestUserProfile:
    def test_build_default_config_has_user_profile(self):
        mgr = ConfigManager()
        config = mgr.build_default_config(
            user_name="Antonio",
            user_role="CTO",
            user_company="Firefly Research",
        )
        assert config["user_profile"]["name"] == "Antonio"
        assert config["user_profile"]["role"] == "CTO"
        assert config["user_profile"]["company"] == "Firefly Research"

    def test_build_default_config_empty_profile(self):
        mgr = ConfigManager()
        config = mgr.build_default_config()
        assert config["user_profile"]["name"] == ""
        assert config["user_profile"]["role"] == ""
        assert config["user_profile"]["company"] == ""
