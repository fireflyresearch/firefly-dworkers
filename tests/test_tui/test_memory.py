"""Tests for conversation-scoped memory."""
from __future__ import annotations


class TestConversationMemory:
    def test_set_and_get_fact(self):
        from firefly_dworkers_cli.tui.backend.memory import ConversationMemory
        mem = ConversationMemory("conv_test")
        mem.set_fact("key1", "value1")
        assert mem.get_fact("key1") == "value1"

    def test_get_fact_default(self):
        from firefly_dworkers_cli.tui.backend.memory import ConversationMemory
        mem = ConversationMemory("conv_test")
        assert mem.get_fact("missing", "default") == "default"

    def test_snapshot_and_restore(self):
        from firefly_dworkers_cli.tui.backend.memory import ConversationMemory
        mem1 = ConversationMemory("conv_test")
        mem1.set_fact("analysis", "Q1 revenue grew 12%")
        snapshot = mem1.snapshot()
        mem2 = ConversationMemory("conv_test2")
        mem2.restore(snapshot)
        assert mem2.get_fact("analysis") == "Q1 revenue grew 12%"

    def test_get_all_facts(self):
        from firefly_dworkers_cli.tui.backend.memory import ConversationMemory
        mem = ConversationMemory("conv_test")
        mem.set_fact("a", "1")
        mem.set_fact("b", "2")
        facts = mem.get_all_facts()
        assert facts["a"] == "1"
        assert facts["b"] == "2"
