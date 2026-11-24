import argparse
import dataclasses
import functools
import itertools
import os
import pathlib
import typing

import pytest

import pytilpack.cli.sync
import pytilpack.pathlib

States = typing.Literal[
    "none", "file", "dir", "link_file", "link_dir", "dangling", "link_inside", "link_loop", "dir_with_links"
]
Relation = typing.Literal["disjoint", "same", "dst_in_src", "src_in_dst"]
SRC_STATES: tuple[States, ...] = ("none", "file", "dir", "link_file", "link_dir", "dangling", "link_inside")
DST_STATES: tuple[States, ...] = (*SRC_STATES, "link_loop", "dir_with_links")
RELATIONS: tuple[Relation, ...] = ("disjoint", "same", "dst_in_src", "src_in_dst")

Entry = tuple[str, bytes | str | None, int]
Snapshot = dict[str, Entry]


@dataclasses.dataclass(frozen=True)
class Case:
    entry: str
    relation: Relation
    dst_exists: bool
    delete: bool
    depth: int
    src_state: States
    dst_state: States

    def __str__(self) -> str:
        return (
            f"entry={self.entry} relation={self.relation} dst_exists={self.dst_exists} delete={self.delete}"
            f" depth={self.depth} src={self.src_state} dst={self.dst_state}"
        )


def _snapshot(root: pathlib.Path) -> Snapshot:
    result: Snapshot = {}
    if not os.path.lexists(root):
        return result
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = pathlib.Path(current) / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if path.is_symlink():
                result[rel] = ("link", os.readlink(path), mode)
            elif path.is_dir():
                result[rel] = ("dir", None, mode)
            else:
                result[rel] = ("file", path.read_bytes(), mode)
    return result


def _make(path: pathlib.Path, root: pathlib.Path, state: States, content: str, base: pathlib.Path, old: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if state == "file":
        path.write_text(content)
        if old:
            os.utime(path, ns=(1, 1))
    elif state == "dir":
        path.mkdir()
        (path / "c").write_text(f"{content}-c")
        if old:
            os.utime(path / "c", ns=(1, 1))
    elif state == "link_file":
        path.symlink_to(base / "outside_file")
    elif state == "link_dir":
        path.symlink_to(base / "outside_dir", target_is_directory=True)
    elif state == "dangling":
        path.symlink_to(base / "nonexistent")
    elif state == "link_inside":
        path.symlink_to(root / "inside.txt")
    elif state == "link_loop":
        path.symlink_to(root, target_is_directory=True)
    elif state == "dir_with_links":
        path.mkdir()
        (path / "lf").symlink_to(base / "outside_file")
        (path / "ld").symlink_to(base / "outside_dir", target_is_directory=True)


def _read_followed(path: pathlib.Path, rel: str, out: Snapshot) -> None:
    if path.is_file():
        out[rel] = ("file", path.read_bytes(), path.stat().st_mode)
    elif path.is_dir():
        out[rel] = ("dir", None, path.stat().st_mode)
        for child in path.iterdir():
            _read_followed(child, f"{rel}/{child.name}", out)


def _expected_dst(src: pathlib.Path, dst_before: Snapshot, delete: bool) -> Snapshot:
    expected: Snapshot = {}

    def subtree(rel: str) -> Snapshot:
        return {k: v for k, v in dst_before.items() if k == rel or k.startswith(f"{rel}/")}

    def walk(src_dir: pathlib.Path, prefix: str) -> None:
        before_names = {k[len(prefix) :].split("/")[0] for k in dst_before if k.startswith(prefix)}
        for name in {p.name for p in src_dir.iterdir()} | before_names:
            rel = f"{prefix}{name}"
            src_child = src_dir / name
            if not src_child.exists():
                if not delete:
                    expected.update(subtree(rel))
            elif src_child.is_dir() and rel in dst_before and dst_before[rel][0] == "dir":
                expected[rel] = dst_before[rel]
                walk(src_child, f"{rel}/")
            else:
                _read_followed(src_child, rel, expected)

    walk(src, "")
    return expected


@functools.cache
def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    pytilpack.cli.sync.add_parser(parser.add_subparsers(dest="command"))
    return parser


def _outside(snapshot: Snapshot, dst_rel: str) -> Snapshot:
    return {k: v for k, v in snapshot.items() if k != dst_rel and not k.startswith(f"{dst_rel}/")}


def _outside_violations(before: Snapshot, after: Snapshot, allowed_new: set[str]) -> list[str]:
    violations = [
        f"コピー先の外が変わった: {key}: {value!r} -> {after.get(key)!r}"
        for key, value in before.items()
        if after.get(key) != value
    ]
    violations.extend(
        f"コピー先の外に作られた: {key}"
        for key in sorted(after.keys() - before.keys())
        if key not in allowed_new or after[key][0] != "dir"
    )
    return violations


@pytest.mark.parametrize(
    ("after", "count"),
    [
        ({"keep": ("file", b"before", 0o100644), "parent": ("dir", None, 0o40755)}, 0),
        ({"keep": ("file", b"changed", 0o100644)}, 1),
        ({}, 1),
        ({"keep": ("file", b"before", 0o100644), "parent": ("file", b"unexpected", 0o100644)}, 1),
    ],
    ids=["unchanged", "modified", "removed", "invalid-ancestor"],
)
def test_outside_checker_detects_synthetic_violations(after: Snapshot, count: int) -> None:
    before: Snapshot = {"keep": ("file", b"before", 0o100644)}
    assert len(_outside_violations(before, after, {"parent"})) == count


def _run(case: Case, base: pathlib.Path) -> str | None:
    (base / "outside_file").write_text("outside")
    (base / "outside_dir").mkdir()
    (base / "outside_dir" / "keep").write_text("keep")

    if case.relation == "disjoint":
        src = base / "src"
        dst = base / "dst" if case.dst_exists else base / "missing_parent" / "dst"
    elif case.relation == "same":
        src = dst = base / "both"
    elif case.relation == "dst_in_src":
        src = base / "src"
        dst = src / "inner" if case.dst_exists else src / "missing_parent" / "inner"
    else:
        dst = base / "dst"
        src = dst / "inner"

    src.mkdir(parents=True, exist_ok=True)
    (src / "s.txt").write_text("src-s")
    (src / "inside.txt").write_text("src-inside")
    if case.dst_exists:
        dst.mkdir(parents=True, exist_ok=True)
        if case.relation != "same":
            (dst / "inside.txt").write_text("dst-inside")
            os.utime(dst / "inside.txt", ns=(1, 1))
    slot = "a" if case.depth == 1 else "d/a"
    if case.depth == 2:
        (src / "d").mkdir(exist_ok=True)
        if case.dst_exists:
            (dst / "d").mkdir(exist_ok=True)
    _make(src / slot, src, case.src_state, "src-a", base, old=False)
    if case.relation != "same":
        _make(dst / slot, dst, case.dst_state, "dst-a", base, old=True)

    dst_rel = dst.relative_to(base).as_posix()
    before = _snapshot(base)
    dst_before = _snapshot(dst)
    rejected = case.relation in ("dst_in_src", "src_in_dst")
    expected = None if rejected or case.relation == "same" else _expected_dst(src, dst_before, case.delete)

    error: Exception | None = None
    try:
        if case.entry == "api":
            pytilpack.pathlib.sync(src, dst, delete=case.delete)
        else:
            args = _cli_parser().parse_args(["sync", str(src), str(dst), *(["--delete"] if case.delete else [])])
            pytilpack.cli.sync.run(args)
    except Exception as e:
        error = e

    after = _snapshot(base)
    if rejected or case.relation == "same":
        if rejected and not isinstance(error, ValueError):
            return f"拒否されなかった: {error!r}"
        if not rejected and error is not None:
            return f"想定外の例外: {error!r}"
        if after != before:
            return "拒否・同一なのに変更された"
        return None
    if error is not None:
        return f"想定外の例外: {error!r}"

    outside_before = _outside(before, dst_rel)
    outside_after = _outside(after, dst_rel)
    allowed_new = {p.relative_to(base).as_posix() for p in dst.parents if p.is_relative_to(base) and p != base}
    violations = _outside_violations(outside_before, outside_after, allowed_new)
    if violations:
        return "; ".join(violations)
    dst_after = _snapshot(dst)
    if dst_after != expected:
        return f"同期の結果が違う: 期待={expected!r} 実際={dst_after!r}"
    return None


def _cases(entry: str, relation: Relation) -> list[Case]:
    cases = []
    for dst_exists, delete, depth, src_state, dst_state in itertools.product(
        (True, False), (False, True), (1, 2), SRC_STATES, DST_STATES
    ):
        if relation in ("same", "src_in_dst") and not dst_exists:
            continue
        if (not dst_exists or relation == "same") and dst_state != "none":
            continue
        cases.append(Case(entry, relation, dst_exists, delete, depth, src_state, dst_state))
    return cases


def _symlinks_available(tmp_path: pathlib.Path) -> bool:
    try:
        (tmp_path / "probe").symlink_to(tmp_path / "probe-target")
    except OSError:
        return False
    (tmp_path / "probe").unlink()
    return True


@pytest.mark.parametrize("relation", RELATIONS)
@pytest.mark.parametrize("entry", ["api", "cli"])
def test_sync_never_changes_outside_destination(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, entry: str, relation: Relation
) -> None:
    monkeypatch.setattr(pytilpack.pathlib.logger, "disabled", True)
    base_root = tmp_path.resolve()
    if not _symlinks_available(base_root):
        pytest.skip("シンボリックリンクを作成できない環境のため")
    cases = _cases(entry, relation)
    failures = []
    for i, case in enumerate(cases):
        base = base_root / f"case{i}"
        base.mkdir()
        message = _run(case, base)
        if message is not None:
            failures.append(f"{case}: {message}")
    assert not failures, f"{len(failures)}/{len(cases)}件が性質を破った:\n" + "\n".join(failures[:20])


@pytest.mark.parametrize("dst_state", ["none", "file", "dir"])
def test_sync_file_root(tmp_path: pathlib.Path, dst_state: str) -> None:
    base = tmp_path.resolve()
    (base / "outside_file").write_text("outside")
    src = base / "src.txt"
    src.write_text("src")
    dst = base / "dst.txt" if dst_state != "none" else base / "missing_parent" / "dst.txt"
    if dst_state == "file":
        dst.write_text("dst")
        os.utime(dst, ns=(1, 1))
    elif dst_state == "dir":
        dst.mkdir()
        (dst / "c").write_text("c")
    before = _outside(_snapshot(base), dst.relative_to(base).as_posix())

    pytilpack.pathlib.sync(src, dst)

    after = _outside(_snapshot(base), dst.relative_to(base).as_posix())
    after.pop("missing_parent", None)
    assert after == before
    assert dst.read_text() == "src"


def test_sync_file_root_inside_destination_is_rejected(tmp_path: pathlib.Path) -> None:
    dst = tmp_path / "dst"
    dst.mkdir()
    src = dst / "src.txt"
    src.write_text("src")
    before = _snapshot(tmp_path)

    with pytest.raises(ValueError, match="コピー元がコピー先の内側"):
        pytilpack.pathlib.sync(src, dst)

    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("delete", [False, True])
def test_sync_follows_destination_root_link(tmp_path: pathlib.Path, delete: bool) -> None:
    base = tmp_path.resolve()
    if not _symlinks_available(base):
        pytest.skip("シンボリックリンクを作成できない環境のため")
    src = base / "src"
    src.mkdir()
    (src / "a").write_text("a")
    real_root = base / "real_root"
    real_root.mkdir()
    (real_root / "extra").write_text("extra")
    (base / "other").write_text("other")
    link_root = base / "link_root"
    link_root.symlink_to(real_root, target_is_directory=True)
    before = _outside(_snapshot(base), "real_root")

    pytilpack.pathlib.sync(src, link_root, delete=delete)

    assert _outside(_snapshot(base), "real_root") == before
    assert link_root.is_symlink()
    assert (real_root / "a").read_text() == "a"
    assert (real_root / "extra").exists() is not delete


def test_sync_keeps_regular_file_with_matching_mtime(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("src")
    dst.write_text("dst")
    os.utime(dst, ns=(src.stat().st_atime_ns, src.stat().st_mtime_ns))

    pytilpack.pathlib.sync(src, dst)

    assert src.read_text() == "src"
    assert dst.read_text() == "dst"
