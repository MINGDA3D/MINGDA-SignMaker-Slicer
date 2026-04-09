"""USB dongle guard package."""

from .build_flags import is_code_dog_enabled
from .dongle_guard import DongleGuard

__all__ = ["DongleGuard", "is_code_dog_enabled"]
