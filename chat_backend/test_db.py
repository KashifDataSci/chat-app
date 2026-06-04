import sys
sys.path.append('.')
from app.db.database import session_local
from app.models.chat import MessageModel, ConversationModel

db = session_local()
msgs = db.query(MessageModel).all()
print(f"Total messages: {len(msgs)}")
for m in msgs:
    print(f"Msg ID: {m.uuid} | Content: {m.content}")
