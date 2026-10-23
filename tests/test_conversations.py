import tempfile
from pathlib import Path
from src.macro_expert.conversations import ConversationManager
from src.macro_expert.database import Database

def test_conversation_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test_conv.db"))
        mgr = ConversationManager(db)

        # Create
        cid = mgr.create_conversation("美债研判研讨")
        assert cid.startswith("conv_")

        # List
        convs = mgr.list_conversations()
        assert len(convs) == 1
        assert convs[0]["title"] == "美债研判研讨"

        # Add messages
        m1 = mgr.add_message(cid, "user", "请问期限溢价对美债有何影响？")
        m2 = mgr.add_message(cid, "assistant", "期限溢价上升将直接推升长端收益率。", model_name="gemini-3.8-flash")
        assert m1.startswith("msg_")
        assert m2.startswith("msg_")

        msgs = mgr.get_messages(cid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

        # Export markdown
        md = mgr.export_conversation_markdown(cid)
        assert "美债研判研讨" in md
        assert "请问期限溢价对美债有何影响？" in md

        # Delete
        assert mgr.delete_conversation(cid) is True
        assert len(mgr.list_conversations()) == 0
