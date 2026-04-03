from __future__ import annotations

from typing import Iterator, List, Optional, Tuple

from .types import Contour, Path

LoopTarget = Tuple[int, int]


def iter_loop_targets(contours: List[Contour]) -> Iterator[tuple[LoopTarget, Path]]:
    """Yield every printable outer/hole loop in stable fallback order."""
    for contour_index, contour in enumerate(contours):
        yield (contour_index, -1), contour.outer
        for hole_index, hole in enumerate(contour.holes):
            yield (contour_index, hole_index), hole


def get_loop_path(contours: List[Contour], target: LoopTarget) -> Optional[Path]:
    """Return the path for a loop target, or None when it no longer exists."""
    contour_index, hole_index = target
    if contour_index < 0 or contour_index >= len(contours):
        return None

    contour = contours[contour_index]
    if hole_index < 0:
        return contour.outer
    if hole_index >= len(contour.holes):
        return None
    return contour.holes[hole_index]


def build_loop_order(contours: List[Contour]) -> List[LoopTarget]:
    """Return the stable effective loop order for display and slicing."""
    entries = [
        (target, path.print_order, fallback_index)
        for fallback_index, (target, path) in enumerate(iter_loop_targets(contours))
    ]
    entries.sort(key=lambda item: (item[1], item[2]))
    return [target for target, _print_order, _fallback_index in entries]


def apply_loop_order(contours: List[Contour], ordered_targets: List[LoopTarget]) -> List[LoopTarget]:
    """
    Normalize all loop print orders to a contiguous 1-based sequence.

    Any missing loops are appended in the current stable fallback order so every
    existing outer/hole path always ends up with a valid order token.
    """
    seen: set[LoopTarget] = set()
    normalized_targets: List[LoopTarget] = []

    for target in ordered_targets:
        path = get_loop_path(contours, target)
        if path is None or target in seen:
            continue
        seen.add(target)
        normalized_targets.append(target)

    for target, path in iter_loop_targets(contours):
        if target in seen:
            continue
        seen.add(target)
        normalized_targets.append(target)

    for order, target in enumerate(normalized_targets, start=1):
        path = get_loop_path(contours, target)
        if path is not None:
            path.print_order = order

    return normalized_targets


def migrate_legacy_contour_order_to_loops(contours: List[Contour]) -> List[LoopTarget]:
    """Expand legacy contour-level order into a global outer/hole loop order."""
    ordered_targets: List[LoopTarget] = []
    contour_entries = sorted(
        enumerate(contours),
        key=lambda item: (item[1].print_order, item[0]),
    )

    for contour_index, contour in contour_entries:
        ordered_targets.append((contour_index, -1))
        for hole_index, _hole in enumerate(contour.holes):
            ordered_targets.append((contour_index, hole_index))

    return apply_loop_order(contours, ordered_targets)
