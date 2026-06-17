from pathlib import Path

from lexo.infra import paths


def _session_with_file(root: Path, size: int) -> Path:
    d = paths.new_session_tmpdir(root)
    (d / "work.bin").write_bytes(b"x" * size)
    return d


def test_stale_excludes_current_session(tmp_path: Path) -> None:
    current = paths.new_session_tmpdir(tmp_path)
    other = _session_with_file(tmp_path, 10)
    stale = paths.stale_session_tmpdirs(current, root=tmp_path)
    assert other in stale
    assert current not in stale


def test_purge_removes_stale_but_keeps_current(tmp_path: Path) -> None:
    current = paths.new_session_tmpdir(tmp_path)
    a = _session_with_file(tmp_path, 100)
    b = _session_with_file(tmp_path, 200)
    removed, freed = paths.purge_session_tmpdirs(current, root=tmp_path)
    assert removed == 2
    assert freed == 300
    assert not a.exists() and not b.exists()
    assert current.exists()  # the live session is preserved


def test_purge_when_nothing_stale(tmp_path: Path) -> None:
    current = paths.new_session_tmpdir(tmp_path)
    assert paths.purge_session_tmpdirs(current, root=tmp_path) == (0, 0)


def test_dir_size_sums_nested_files(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"x" * 50)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b").write_bytes(b"y" * 70)
    assert paths.dir_size(tmp_path) == 120
