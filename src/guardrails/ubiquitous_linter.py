"""
Ubiquitous Language Guardrail & Linter for Chilean Water Domain.
Loads official definitions and prevents terminology contamination in agent outputs.
"""

import json
from pathlib import Path
from typing import List, Optional

from src.core.ubiquitous import LintViolation, UbiquitousLanguageRegistry, UbiquitousTerm


class WaterUbiquitousGuard:
    """
    Guardrail that enforces exact terminology from the Chile Water Code and OUA traditions.
    """

    def __init__(self, dataset_path: Optional[str] = None):
        self.registry = UbiquitousLanguageRegistry()
        if not dataset_path:
            # Default to local data path
            dataset_path = str(Path(__file__).parent.parent.parent / "data" / "ubiquitous_chile.json")
        self._load_dataset(dataset_path)

    def _load_dataset(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.exists():
            return
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                term = UbiquitousTerm(**item)
                self.registry.register_term(term)

    def validate(self, text: str, bounded_context: Optional[str] = None) -> List[LintViolation]:
        """Runs the linter and returns any terminology violations."""
        return self.registry.lint_text(text, bounded_context)

    def sanitize_query(self, query: str, bounded_context: Optional[str] = None) -> str:
        """Acts as an Anti-Corruption Layer (ACL) translating informal terms to canonical ones."""
        return self.registry.normalize_text(query, bounded_context)
