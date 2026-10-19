"""
Ubiquitous Language (Lenguaje Ubicuo) Registry & Linter.
Ensures semantic purity and prevents vocabulary drift or forbidden colloquialisms.
"""

import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UbiquitousTerm(BaseModel):
    """
    Formal specification of a domain concept in the Ubiquitous Language.
    """
    canonical_name: str = Field(description="Official name in the domain")
    bounded_context: str = Field(description="Context where this term is primary")
    definition: str = Field(description="Rigorous business/legal definition")
    forbidden_synonyms: List[str] = Field(
        default_factory=list,
        description="Informal, obsolete or misleading terms that must be rejected"
    )
    allowed_abbreviations: List[str] = Field(
        default_factory=list,
        description="Standard acronyms permitted (e.g. 'JV', 'DAA', 'OUA')"
    )
    related_terms: List[str] = Field(default_factory=list)


class LintViolation(BaseModel):
    forbidden_term_found: str
    suggested_canonical_term: str
    bounded_context: str
    reason: str
    position_hint: Optional[str] = None


class UbiquitousLanguageRegistry:
    """
    Registry that catalogs canonical terms and provides semantic linting.
    """

    def __init__(self):
        self._terms: Dict[str, UbiquitousTerm] = {}
        self._forbidden_index: Dict[str, UbiquitousTerm] = {}

    def register_term(self, term: UbiquitousTerm) -> None:
        self._terms[term.canonical_name.lower()] = term
        for syn in term.forbidden_synonyms:
            self._forbidden_index[syn.lower()] = term

    def get_term(self, name: str) -> Optional[UbiquitousTerm]:
        return self._terms.get(name.lower())

    def lint_text(self, text: str, bounded_context: Optional[str] = None) -> List[LintViolation]:
        """
        Scans text for forbidden/misleading synonyms and reports violations.
        """
        violations: List[LintViolation] = []
        text_lower = text.lower()

        for forbidden_syn, canonical_term in self._forbidden_index.items():
            if bounded_context and canonical_term.bounded_context != bounded_context:
                continue

            # Word boundary regex to avoid partial substring false positives
            pattern = rf"\b{re.escape(forbidden_syn)}\b"
            if re.search(pattern, text_lower):
                violations.append(
                    LintViolation(
                        forbidden_term_found=forbidden_syn,
                        suggested_canonical_term=canonical_term.canonical_name,
                        bounded_context=canonical_term.bounded_context,
                        reason=f"El término '{forbidden_syn}' viola el Lenguaje Ubicuo. Usar '{canonical_term.canonical_name}'.",
                    )
                )
        return violations

    def normalize_text(self, text: str, bounded_context: Optional[str] = None) -> str:
        """
        Replaces forbidden synonyms with their canonical term.
        Acts as an automated Anti-Corruption Layer (ACL) for queries.
        """
        normalized = text
        for forbidden_syn, canonical_term in self._forbidden_index.items():
            if bounded_context and canonical_term.bounded_context != bounded_context:
                continue
            pattern = re.compile(rf"\b{re.escape(forbidden_syn)}\b", re.IGNORECASE)
            normalized = pattern.sub(canonical_term.canonical_name, normalized)
        return normalized

    def list_all_terms(self, bounded_context: Optional[str] = None) -> List[UbiquitousTerm]:
        if not bounded_context:
            return list(self._terms.values())
        return [t for t in self._terms.values() if t.bounded_context == bounded_context]
