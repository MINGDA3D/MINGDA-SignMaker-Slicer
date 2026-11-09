"""Verification exports must preserve all input projects before doing work."""

from pathlib import Path

import pytest

from tools.verify_slot_exports import validate_output_paths


def test_derived_output_cannot_overwrite_a_later_input(tmp_path: Path) -> None:
    """Reject the entire batch before the first project's derived files exist."""
    source = tmp_path / "a.smp"
    later_source = tmp_path / "a_panel_flat.smp"
    source.write_bytes(b"first source")
    later_source.write_bytes(b"second source")
    with pytest.raises(ValueError, match="overwrite a project"):
        validate_output_paths([source, later_source], tmp_path)
    assert source.read_bytes() == b"first source"
    assert later_source.read_bytes() == b"second source"


def test_same_basename_inputs_cannot_overwrite_each_others_results(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="overwrite a project"):
        validate_output_paths([tmp_path / "one/a.smp", tmp_path / "two/a.smp"], tmp_path / "out")


def test_distinct_inputs_allow_separate_verification_directory(tmp_path: Path) -> None:
    validate_output_paths([tmp_path / "test.smp", tmp_path / "e1.smp"], tmp_path / "out")
