from __future__ import annotations

import uuid
from typing import Iterable, List, Optional, Sequence, Tuple

from .types import Contour


def generate_asset_id() -> str:
    """Generate a stable identifier for a logical asset."""
    return uuid.uuid4().hex


def get_contour_asset_id(contour: Contour) -> str:
    return getattr(contour, "asset_id", "") or ""


def get_contour_asset_name(contour: Contour) -> str:
    return getattr(contour, "asset_name", "") or ""


def assign_contours_to_asset(
    contours: Sequence[Contour],
    asset_name: str,
    asset_id: Optional[str] = None,
) -> str:
    """Attach a logical asset identity to every contour in the sequence."""
    resolved_asset_id = asset_id or generate_asset_id()
    resolved_asset_name = asset_name.strip() or "Asset"

    for contour in contours:
        contour.asset_id = resolved_asset_id
        contour.asset_name = resolved_asset_name

    return resolved_asset_id


def clear_contours_asset(contours: Iterable[Contour]) -> None:
    """Detach contours from any logical asset container."""
    for contour in contours:
        contour.asset_id = ""
        contour.asset_name = ""


def get_asset_member_indices(contours: Sequence[Contour], asset_id: str) -> List[int]:
    if not asset_id:
        return []

    return [
        index for index, contour in enumerate(contours)
        if get_contour_asset_id(contour) == asset_id
    ]


def get_asset_member_indices_for_index(contours: Sequence[Contour], index: int) -> List[int]:
    if not (0 <= index < len(contours)):
        return []

    asset_id = get_contour_asset_id(contours[index])
    if not asset_id:
        return [index]

    members = get_asset_member_indices(contours, asset_id)
    return members if members else [index]


def get_shared_asset_metadata(contours: Sequence[Contour]) -> Optional[Tuple[str, str]]:
    """Return the shared asset metadata when every contour belongs to one asset."""
    if not contours:
        return None

    asset_id = get_contour_asset_id(contours[0])
    if not asset_id:
        return None

    asset_name = get_contour_asset_name(contours[0])
    for contour in contours[1:]:
        if get_contour_asset_id(contour) != asset_id:
            return None
        if not asset_name:
            asset_name = get_contour_asset_name(contour)

    return asset_id, asset_name
