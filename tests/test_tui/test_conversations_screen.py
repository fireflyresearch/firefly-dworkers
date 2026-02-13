"""Test ConversationsScreen."""

from firefly_dworkers_cli.tui.screens.conversations import (
    ConversationsScreen,
    OpenConversation,
)


class TestConversationsScreen:
    def test_instantiates(self):
        screen = ConversationsScreen()
        assert screen._conversations == []

    def test_store_created(self):
        screen = ConversationsScreen()
        assert screen._store is not None


class TestOpenConversation:
    def test_message_with_id(self):
        msg = OpenConversation("conv_abc123")
        assert msg.conversation_id == "conv_abc123"

    def test_message_empty_id_for_new(self):
        msg = OpenConversation("")
        assert msg.conversation_id == ""
