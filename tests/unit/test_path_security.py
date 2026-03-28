from pathlib import Path

from homeschool.path_security import is_path_within_directory, is_safe_relative_subpath


def test_is_path_within_directory_true(temp_dir):
    root = temp_dir / "vault"
    child = root / "notes" / "a.md"
    assert is_path_within_directory(child, root)


def test_is_path_within_directory_prefix_collision_false(temp_dir):
    root = temp_dir / "vault"
    attacker = temp_dir / "vault_evil" / "note.md"
    assert not is_path_within_directory(attacker, root)


def test_is_safe_relative_subpath():
    assert is_safe_relative_subpath("")
    assert is_safe_relative_subpath("notes/biology")
    assert not is_safe_relative_subpath("../secrets")
    assert not is_safe_relative_subpath("/absolute/path")
