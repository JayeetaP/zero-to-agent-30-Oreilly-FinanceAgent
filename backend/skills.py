from functools import lru_cache
from pathlib import Path

from .config import ROOT


@lru_cache(maxsize=8)
def load_skill(name: str) -> str:
    path = Path(ROOT, "skills", name, "SKILL.md")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_rules() -> str:
    rule_dir = Path(ROOT, "rules")
    return "\n\n".join(
        path.read_text(encoding="utf-8") for path in sorted(rule_dir.glob("*.md"))
    )

