# -*- coding: utf-8 -*-
"""Audit generate-theme.py coverage for vstheme-tokens.json.

Reports token slots that fall through the explicit Gruber-Darker mapping rules
and land on generic defaults. This version matches the current generator schema:

    color["background"] / color["foreground"] = {
        "type": "CT_RAW",
        "source": "FF...",
        "valid": true,
    }

Run from the src/ directory:
    python audit-theme.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS_PATH = os.path.join(HERE, "vstheme-tokens.json")
GENERATOR_PATH = os.path.join(HERE, "generate-theme.py")

spec = importlib.util.spec_from_file_location("generate_theme", GENERATOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not import {GENERATOR_PATH}")

generate_theme = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generate_theme
spec.loader.exec_module(generate_theme)


@dataclass(frozen=True)
class SlotAudit:
    category: str
    name: str
    slot: str
    reason: str
    role: str

    @property
    def display(self) -> str:
        return f"{self.category} / {self.name} / {self.slot} -> {self.role} ({self.reason})"


def slot_is_colourable_raw(slot: dict[str, Any] | None) -> bool:
    """Return true only for slots that generate-theme.py will recolour."""
    if not slot:
        return False
    if not slot.get("valid") or slot.get("type") != "CT_RAW":
        return False

    source = (slot.get("source") or "00000000").upper()
    alpha, _ = generate_theme.split_argb(source)
    return alpha != "00"


def exact_roles(category: str, name: str) -> tuple[str | None, str | None] | None:
    return generate_theme.exact_roles(category, name)


def foreground_mapping(category: str, name: str) -> tuple[str, str]:
    exact = exact_roles(category, name)
    if exact and exact[0]:
        return exact[0], "exact foreground"

    role = generate_theme.pattern_role(
        generate_theme.FOREGROUND_PATTERNS,
        category,
        name,
        include_category=False,
    )
    if role:
        return role, "foreground pattern"

    return "fg", "generic foreground default"


def background_mapping(category: str, name: str) -> tuple[str, str]:
    exact = exact_roles(category, name)
    if exact and exact[1]:
        return exact[1], "exact background"

    role = generate_theme.pattern_role(
        generate_theme.BACKGROUND_PATTERNS,
        category,
        name,
        include_category=True,
    )
    if role:
        return role, "background pattern"

    if generate_theme.is_background_concept(category, name):
        return "bg", "background concept fallback"

    return "bg+1", "generic background default"


def audit_slot(
    category: str,
    name: str,
    slot_name: str,
    slot: dict[str, Any] | None,
    other_slot: dict[str, Any] | None,
) -> SlotAudit | None:
    if not slot_is_colourable_raw(slot):
        return None

    if slot_name == "Foreground":
        role, reason = foreground_mapping(category, name)
        return SlotAudit(category, name, slot_name, reason, role)

    if generate_theme.should_treat_background_as_foreground(
        category,
        name,
        slot,
        other_slot,
    ):
        role, reason = foreground_mapping(category, name)
        return SlotAudit(category, name, slot_name, "background-as-foreground: " + reason, role)

    role, reason = background_mapping(category, name)
    return SlotAudit(category, name, slot_name, reason, role)


def main() -> None:
    with open(TOKENS_PATH, encoding="utf-8") as f:
        categories = json.load(f)

    total_tokens = 0
    colourable_slots = 0
    audits: list[SlotAudit] = []

    for cat in categories:
        category = cat["name"]
        for color in cat["colors"]:
            total_tokens += 1
            name = color["name"]
            background = color.get("background")
            foreground = color.get("foreground")

            for slot_name, slot, other_slot in (
                ("Background", background, foreground),
                ("Foreground", foreground, background),
            ):
                result = audit_slot(category, name, slot_name, slot, other_slot)
                if result is None:
                    continue
                colourable_slots += 1
                audits.append(result)

    by_reason = Counter(a.reason for a in audits)
    generic = [
        a
        for a in audits
        if a.reason in {
            "generic foreground default",
            "generic background default",
            "background-as-foreground: generic foreground default",
        }
    ]

    by_category: dict[str, int] = defaultdict(int)
    for item in generic:
        by_category[item.category] += 1

    print(f"total tokens: {total_tokens}")
    print(f"colourable CT_RAW slots: {colourable_slots}")
    print()

    print("mapping reasons:")
    for reason, count in by_reason.most_common():
        pct = 100.0 * count / colourable_slots if colourable_slots else 0.0
        print(f" - {reason}: {count} ({pct:.1f}%)")

    print()
    print(
        "generic default slots: %d (%.1f%%)"
        % (len(generic), 100.0 * len(generic) / colourable_slots if colourable_slots else 0.0)
    )

    if generic:
        print()
        print("generic defaults by category:")
        for category, count in sorted(by_category.items(), key=lambda x: (-x[1], x[0])):
            print(f" - {category}: {count}")

        print()
        print("generic default slots:")
        for item in generic:
            print(" -", item.display)


if __name__ == "__main__":
    main()

