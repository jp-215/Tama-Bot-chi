"""
Conversation Store - Tracks all iMessage conversations for the desktop pet summary system.
Stores conversation data in a local JSON file so the pet can display summaries.
"""
import json
import os
import time
import logging
from typing import Dict
from threading import Lock

logger = logging.getLogger(__name__)

STORE_PATH = os.path.join(os.path.dirname(__file__), "data", "conversations.json")
_lock = Lock()


def _ensure_store() -> Dict:
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    if not os.path.exists(STORE_PATH):
        _write_store({"conversations": {}})
    try:
        with open(STORE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        _write_store({"conversations": {}})
        return {"conversations": {}}


def _write_store(data: Dict) -> None:
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def log_message(sender: str, message: str, is_from_agent: bool, conversation_id: str) -> None:
    with _lock:
        store = _ensure_store()
        convos = store.get("conversations", {})

        if conversation_id not in convos:
            convos[conversation_id] = {
                "sender": sender,
                "conversation_id": conversation_id,
                "started_at": time.time(),
                "last_activity": time.time(),
                "messages": [],
                "read": False,
                "summary": None,
            }

        convos[conversation_id]["last_activity"] = time.time()
        convos[conversation_id]["messages"].append({
            "from": "agent" if is_from_agent else sender,
            "text": message,
            "timestamp": time.time(),
        })
        convos[conversation_id]["read"] = False

        store["conversations"] = convos
        _write_store(store)


def update_summary(conversation_id: str, summary: Dict) -> None:
    with _lock:
        store = _ensure_store()
        convos = store.get("conversations", {})
        if conversation_id in convos:
            convos[conversation_id]["summary"] = summary
            store["conversations"] = convos
            _write_store(store)


def mark_read(conversation_id: str) -> None:
    with _lock:
        store = _ensure_store()
        convos = store.get("conversations", {})
        if conversation_id in convos:
            convos[conversation_id]["read"] = True
            store["conversations"] = convos
            _write_store(store)


def mark_all_read() -> None:
    with _lock:
        store = _ensure_store()
        convos = store.get("conversations", {})
        for cid in convos:
            convos[cid]["read"] = True
        store["conversations"] = convos
        _write_store(store)


def get_all_conversations() -> Dict:
    with _lock:
        store = _ensure_store()
        return store.get("conversations", {})


def get_unread_conversations() -> Dict:
    with _lock:
        store = _ensure_store()
        convos = store.get("conversations", {})
        return {cid: c for cid, c in convos.items() if not c.get("read", True)}


def get_unread_count() -> int:
    return len(get_unread_conversations())


def clear_conversations() -> None:
    with _lock:
        _write_store({"conversations": {}})
