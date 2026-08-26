import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from agno.db.schemas import UserMemory
from agno.db.sqlite import SqliteDb
from agno.memory import MemoryManager

from .config import LEGACY_MEMORY_FILE, MEMORY_DB_FILE
from .models import PreferencePatch


MEMORY_USER_ID = "local-demo"
ACTIVE_MEMORY_ID = "briefing-preferences-active"
HISTORY_PREFIX = "briefing-preferences-v"

PREFERENCE_FIELDS = (
    ("research.preferred_sources", "Research", "Preferred sources"),
    ("research.excluded_topics", "Research", "Excluded topics"),
    ("editorial.tone", "Editorial", "Tone"),
    ("editorial.lead_with_implication", "Editorial", "Lead with implication"),
    ("editorial.jargon_level", "Editorial", "Jargon level"),
    ("display.currency_style", "Display", "Currency style"),
    ("display.date_style", "Display", "Date style"),
)


@lru_cache(maxsize=8)
def _manager_for(db_file: str) -> MemoryManager:
    database = SqliteDb(db_file=db_file, memory_table="briefing_preferences")
    return MemoryManager(
        db=database,
        add_memories=True,
        update_memories=True,
        delete_memories=False,
        clear_memories=False,
    )


def _manager() -> MemoryManager:
    MEMORY_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    return _manager_for(str(MEMORY_DB_FILE))


def _nested_value(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        value = value[part]
    return value


def preference_changes(before: PreferencePatch, after: PreferencePatch) -> list[dict[str, Any]]:
    before_data = before.model_dump(mode="json")
    after_data = after.model_dump(mode="json")
    changes: list[dict[str, Any]] = []
    for path, group, label in PREFERENCE_FIELDS:
        old_value = _nested_value(before_data, path)
        new_value = _nested_value(after_data, path)
        if old_value != new_value:
            changes.append(
                {
                    "path": path,
                    "group": group,
                    "label": label,
                    "before": old_value,
                    "after": new_value,
                }
            )
    return changes


def _decode(record: UserMemory) -> dict[str, Any] | None:
    try:
        data = json.loads(record.memory)
        PreferencePatch.model_validate(data["preferences"])
        return data
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _records() -> list[UserMemory]:
    return _manager().get_user_memories(user_id=MEMORY_USER_ID) or []


def _save_record(memory_id: str, data: dict[str, Any], topics: list[str], feedback: str) -> None:
    _manager().add_user_memory(
        UserMemory(
            memory_id=memory_id,
            user_id=MEMORY_USER_ID,
            memory=json.dumps(data, separators=(",", ":")),
            topics=topics,
            input=feedback,
        ),
        user_id=MEMORY_USER_ID,
    )


def _snapshot(
    version: int,
    preferences: PreferencePatch,
    feedback: str,
    changes: list[dict[str, Any]],
    approved_at: str | None = None,
) -> dict[str, Any]:
    return {
        "version": version,
        "preferences": preferences.model_dump(mode="json"),
        "approved_at": approved_at or datetime.now(UTC).isoformat(),
        "feedback": feedback,
        "changes": changes,
    }


def _migrate_legacy_memory() -> None:
    if _records() or not LEGACY_MEMORY_FILE.exists():
        return
    try:
        legacy = json.loads(LEGACY_MEMORY_FILE.read_text(encoding="utf-8"))
        preferences = PreferencePatch.model_validate(legacy["preferences"])
        if preferences.editorial.tone == "direct, calm, beginner-friendly":
            preferences.editorial.tone = "direct, professional, analyst-oriented"
        version = max(1, int(legacy.get("version", 1)))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return

    feedback = "Imported previously approved preferences"
    snapshot = _snapshot(
        version=version,
        preferences=preferences,
        feedback=feedback,
        changes=preference_changes(PreferencePatch(), preferences),
        approved_at=legacy.get("approved_at"),
    )
    _save_record(
        f"{HISTORY_PREFIX}{version}",
        snapshot,
        ["briefing-preferences", "history", "imported"],
        feedback,
    )
    _save_record(
        ACTIVE_MEMORY_ID,
        snapshot,
        ["briefing-preferences", "active"],
        feedback,
    )


def load_memory() -> dict[str, Any]:
    _migrate_legacy_memory()
    active: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []
    for record in _records():
        decoded = _decode(record)
        if not decoded:
            continue
        if record.memory_id == ACTIVE_MEMORY_ID:
            active = decoded
        elif record.memory_id and record.memory_id.startswith(HISTORY_PREFIX):
            history.append(decoded)

    history.sort(key=lambda item: int(item.get("version", 0)), reverse=True)
    latest_version = max((int(item["version"]) for item in history), default=0)
    if not active:
        defaults = PreferencePatch().model_dump(mode="json")
        return {
            "version": 0,
            "active_version": 0,
            "latest_version": latest_version,
            "preferences": defaults,
            "approved_at": None,
            "history": history,
        }
    return {
        "version": int(active["version"]),
        "active_version": int(active["version"]),
        "latest_version": latest_version,
        "preferences": active["preferences"],
        "approved_at": active.get("approved_at"),
        "feedback": active.get("feedback"),
        "history": history,
    }


def approve_memory(patch: PreferencePatch, feedback: str = "Approved preference update") -> dict[str, Any]:
    current = load_memory()
    before = PreferencePatch.model_validate(current["preferences"])
    next_version = int(current.get("latest_version", 0)) + 1
    snapshot = _snapshot(
        version=next_version,
        preferences=patch,
        feedback=feedback.strip() or "Approved preference update",
        changes=preference_changes(before, patch),
    )
    _save_record(
        f"{HISTORY_PREFIX}{next_version}",
        snapshot,
        ["briefing-preferences", "history"],
        snapshot["feedback"],
    )
    _save_record(
        ACTIVE_MEMORY_ID,
        snapshot,
        ["briefing-preferences", "active"],
        snapshot["feedback"],
    )
    return load_memory()


def activate_memory(version: int) -> dict[str, Any]:
    target: dict[str, Any] | None = None
    for record in _records():
        if record.memory_id == f"{HISTORY_PREFIX}{version}":
            target = _decode(record)
            break
    if not target:
        raise ValueError(f"Memory version {version} was not found.")
    _save_record(
        ACTIVE_MEMORY_ID,
        target,
        ["briefing-preferences", "active"],
        f"Activated approved preferences v{version}",
    )
    return load_memory()


def active_preferences() -> tuple[int, PreferencePatch]:
    memory = load_memory()
    return int(memory["active_version"]), PreferencePatch.model_validate(memory["preferences"])
