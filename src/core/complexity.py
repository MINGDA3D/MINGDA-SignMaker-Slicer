"""UI complexity levels and project feature detection.

The selected level is a user-interface preference.  It never participates in
project serialization or slicing parameter normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Optional

from .types import Contour, EdgeProfileType, EdgeType, SliceParams


class ComplexityLevel(IntEnum):
    """Progressive UI complexity levels."""

    BASIC = 0
    ADVANCED = 1
    EXPERT = 2

    @property
    def storage_value(self) -> str:
        """Return the stable value stored in QSettings."""
        return self.name.lower()


def normalize_complexity_level(
    value: object,
    default: ComplexityLevel = ComplexityLevel.BASIC,
) -> ComplexityLevel:
    """Normalize enum, integer, or string input to a complexity level."""
    if isinstance(value, ComplexityLevel):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        for level in ComplexityLevel:
            if normalized in {level.name.lower(), level.storage_value}:
                return level
        return default
    try:
        return ComplexityLevel(int(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ComplexityRequirement:
    """Minimum level and opt-in features that require it."""

    level: ComplexityLevel = ComplexityLevel.BASIC
    features: tuple[str, ...] = ()


def required_complexity_for_project(
    params: SliceParams,
    contours: Optional[Iterable[Contour]] = None,
) -> ComplexityRequirement:
    """Return the minimum level required to edit active opt-in features.

    Numeric tuning values are deliberately excluded.  Printer profiles and
    their normal defaults would otherwise make every project look customized.
    """
    advanced: list[str] = []
    expert: list[str] = []

    if params.shell.edge_type == EdgeType.CUSTOM:
        profile = params.shell.edge_profile
        if profile is not None and (
            profile.profile_type == EdgeProfileType.CUSTOM
            or bool(profile.source_file)
        ):
            expert.append("Imported custom edge")
        else:
            advanced.append("Custom edge")

    if params.step.panel_step_enabled and params.step.panel_step_is_v_groove:
        advanced.append("Acrylic face V-groove")
    if params.step.baseplate_step_enabled and params.step.baseplate_step_is_v_groove:
        advanced.append("Back plate V-groove")
    if params.light_slot.enabled:
        advanced.append("LED strip slot")
    if params.edge_wrap.wrap_enabled:
        advanced.append("Bottom edge wrap")
    if params.edge_wrap.outline_enabled:
        advanced.append("Bottom outline")
    if params.skirt.enabled:
        advanced.append("Anti-warp brim")
    if params.connected.enabled:
        advanced.append("Letter bridges")
    if params.color.enabled:
        advanced.append("Color change")
    if params.prime_tower.enabled:
        expert.append("Prime tower")

    has_manual_screw_holes = False
    has_custom_print_order = False
    for contour in contours or ():
        if contour.screw_hole_centers:
            has_manual_screw_holes = True
        if contour.outer.print_order != 0 or any(
            hole.print_order != 0 for hole in contour.holes
        ):
            has_custom_print_order = True

    if has_manual_screw_holes:
        advanced.append("Manual screw holes")
    if has_custom_print_order:
        expert.append("Custom print order")

    if expert:
        return ComplexityRequirement(
            level=ComplexityLevel.EXPERT,
            features=tuple(dict.fromkeys((*expert, *advanced))),
        )
    if advanced:
        return ComplexityRequirement(
            level=ComplexityLevel.ADVANCED,
            features=tuple(dict.fromkeys(advanced)),
        )
    return ComplexityRequirement()
