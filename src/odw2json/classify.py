"""Load the document types from config/types/*.yaml and find the type of a document."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from odw2json.common import despace_caps

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "types"


@dataclass
class Rule:
    pattern: re.Pattern
    weight: float
    where: str  # "start" (the first 300 characters), "head" (the first head_chars) or "all"


@dataclass
class DocType:
    name: str
    label: str
    template: dict
    extractor: str
    head_chars: int
    min_score: float
    rules: list[Rule]
    fields: list[dict] = field(default_factory=list)
    order: int = 0
    raw: dict = field(default_factory=dict)  # the whole YAML configuration

    def empty(self) -> dict:
        return copy.deepcopy(self.template)

    def score(self, head: str, text: str) -> tuple[float, list[str]]:
        total, hits = 0.0, []
        for rule in self.rules:
            scope = {"start": text[:300], "head": head}.get(rule.where, text)
            if rule.pattern.search(scope):
                total += rule.weight
                hits.append(f"{rule.weight:+g} {rule.pattern.pattern}")
        return total, hits


def _rules(items: list[dict]) -> list[Rule]:
    flags = re.IGNORECASE | re.MULTILINE
    return [Rule(re.compile(r["pattern"], flags), float(r.get("weight", 1)), r.get("where", "all")) for r in items]


@cache
def load_types(config_dir: Path = CONFIG_DIR) -> list[DocType]:
    types = []
    for path in sorted(config_dir.glob("*.yaml")):
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        c = cfg.get("classify", {})
        types.append(
            DocType(
                name=cfg["name"],
                label=cfg.get("label", cfg["name"]),
                template=cfg["template"],
                extractor=cfg.get("extractor", "generic"),
                head_chars=int(c.get("head_chars", 1500)),
                min_score=float(c.get("min_score", 3)),
                rules=_rules(c.get("rules", [])),
                fields=cfg.get("fields", []),
                order=int(cfg.get("order", 0)),
                raw=cfg,
            )
        )
    return sorted(types, key=lambda t: t.order)


@dataclass
class Classification:
    doc_type: DocType | None
    scores: dict[str, float]
    hits: dict[str, list[str]]


def classify(text: str) -> Classification:
    """Give the type with the highest score. If no type has its minimum score, give None."""
    text = despace_caps(text)
    scores, hits, best = {}, {}, None
    for t in load_types():
        s, h = t.score(text[: t.head_chars], text)
        scores[t.name], hits[t.name] = s, h
        if s >= t.min_score and (best is None or s > scores[best.name]):
            best = t
    return Classification(best, scores, hits)
