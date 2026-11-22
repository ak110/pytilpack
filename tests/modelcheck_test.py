import threading
import typing

import pytest

import pytilpack.modelcheck as mc


def _counter_actors(env: dict[str, int], locked: bool) -> dict[str, typing.Callable[[], None]]:
    def increment() -> None:
        if locked:
            mc.acquire("L")
        mc.step("x", write=False, label="read")
        value = env["x"]
        mc.step("x", write=True, label="write")
        env["x"] = value + 1
        if locked:
            mc.release("L")

    return {"a": increment, "b": increment}


def test_lost_update() -> None:
    env = {"x": 0}

    def setup() -> None:
        env["x"] = 0

    explorer = mc.ThreadExplorer(_counter_actors(env, locked=False), setup)
    lost = []
    for run in explorer:
        if env["x"] != 2:
            lost.append(run)
    assert explorer.outcome == mc.Outcome.EXHAUSTIVE
    assert lost
    schedule = lost[0].schedule
    assert [(s.actor, s.write) for s in lost[0].steps] in (
        [("a", False), ("b", False), ("a", True), ("b", True)],
        [("a", False), ("b", False), ("b", True), ("a", True)],
        [("b", False), ("a", False), ("a", True), ("b", True)],
        [("b", False), ("a", False), ("b", True), ("a", True)],
    )

    replayed = explorer.replay(schedule)
    assert replayed.schedule == schedule
    assert env["x"] == 1


def test_lock_prevents_lost_update() -> None:
    env = {"x": 0}

    def setup() -> None:
        env["x"] = 0

    explorer = mc.ThreadExplorer(_counter_actors(env, locked=True), setup)
    finals = []
    for run in explorer:
        assert not run.deadlock
        assert not run.exceptions
        finals.append(env["x"])
    assert explorer.outcome == mc.Outcome.EXHAUSTIVE
    assert finals
    assert all(v == 2 for v in finals)


def test_independent_resources_marked_equivalent() -> None:
    explorer = mc.ThreadExplorer(
        {
            "a": lambda: mc.step("r1", write=True),
            "b": lambda: mc.step("r2", write=True),
        }
    )
    runs = list(explorer)
    assert len(runs) == 2
    assert [r.equivalent for r in runs].count(True) == 1
    assert {r.schedule for r in runs} == {("a", "b"), ("b", "a")}
    assert explorer.equivalent_runs == 1


@pytest.mark.parametrize("report", [False, True])
def test_same_resource_writes_not_reduced_by_report(report: bool) -> None:
    def writer() -> None:
        mc.step("r", write=True)
        if report:
            mc.report_write(False)

    runs = list(mc.ThreadExplorer({"a": writer, "b": writer}))
    assert len(runs) == 2
    assert not any(r.equivalent for r in runs)
    if report:
        assert all(s.wrote is False for r in runs for s in r.steps)


def _report_target(report: bool) -> tuple[int, set[int]]:
    env = {"c": 0}

    def setup() -> None:
        env["c"] = 0

    def reader() -> None:
        mc.step("r", write=False)

    def checker() -> None:
        mc.step("r", write=True)
        if report:
            mc.report_write(False)

    def increment() -> None:
        mc.step("c", write=False)
        value = env["c"]
        mc.step("c", write=True)
        env["c"] = value + 1

    actors = {"r1": reader, "r2": reader, "w": checker, "i1": increment, "i2": increment}
    unmarked = 0
    finals = set()
    explorer = mc.ThreadExplorer(actors, setup)
    for run in explorer:
        if not run.equivalent:
            unmarked += 1
            finals.add(env["c"])
    assert explorer.outcome == mc.Outcome.EXHAUSTIVE
    return unmarked, finals


def test_report_write_reduces_runs() -> None:
    unmarked_without, finals_without = _report_target(report=False)
    unmarked_with, finals_with = _report_target(report=True)
    assert unmarked_with < unmarked_without
    assert finals_without == finals_with == {1, 2}


def test_deadlock() -> None:
    def first() -> None:
        with mc.lock("A"), mc.lock("B"):
            pass

    def second() -> None:
        with mc.lock("B"), mc.lock("A"):
            pass

    explorer = mc.ThreadExplorer({"first": first, "second": second})
    deadlocks = [run for run in explorer if run.deadlock]
    assert explorer.outcome == mc.Outcome.EXHAUSTIVE
    assert deadlocks
    run = deadlocks[0]
    assert set(run.blocked) == {"first", "second"}
    assert [(s.actor, s.resource, s.kind) for s in run.steps][:2] in (
        [("first", "A", "acquire"), ("second", "B", "acquire")],
        [("second", "B", "acquire"), ("first", "A", "acquire")],
    )


def test_actor_results() -> None:
    def ok() -> int:
        mc.step("r", write=False)
        return 42

    def ng() -> None:
        mc.step("r", write=False)
        raise ValueError("boom")

    for run in mc.ThreadExplorer({"ok": ok, "ng": ng}):
        assert run.returns == {"ok": 42}
        assert isinstance(run.exceptions["ng"], ValueError)


def test_step_timeout() -> None:
    gate = threading.Event()
    caught: list[BaseException] = []
    finished = threading.Event()
    setup_calls = []

    def stuck() -> None:
        mc.step("r", write=True, label="first")
        try:
            gate.wait()
            mc.step("r", write=True, label="late")
        except BaseException as e:
            caught.append(e)
            raise
        finally:
            finished.set()

    def other() -> None:
        mc.step("r", write=True)

    explorer = mc.ThreadExplorer({"stuck": stuck, "other": other}, lambda: setup_calls.append(1), step_timeout=0.2)
    with pytest.raises(mc.StepTimeoutError) as excinfo:
        for _ in explorer:
            pass
    error = excinfo.value
    assert error.actor == "stuck"
    assert [s.label for s in error.steps][-1] == "first"
    assert error.unfinished_actors == ("stuck",)
    assert len(setup_calls) == 1
    assert explorer.outcome is None

    gate.set()
    assert finished.wait(5)
    assert len(caught) == 1
    assert isinstance(caught[0], mc.ExplorationAborted)
    assert not isinstance(caught[0], Exception)
    assert len(setup_calls) == 1


def test_max_runs_truncated() -> None:
    def writer() -> None:
        mc.step("r", write=True)
        mc.step("r", write=True)

    explorer = mc.ThreadExplorer({"a": writer, "b": writer}, max_runs=2)
    assert len(list(explorer)) == 2
    assert explorer.outcome == mc.Outcome.TRUNCATED

    full = mc.ThreadExplorer({"a": writer, "b": writer})
    assert len(list(full)) == 6
    assert full.outcome == mc.Outcome.EXHAUSTIVE


def test_nondeterminism() -> None:
    calls = []

    def flaky() -> None:
        calls.append(1)
        mc.step("r" if len(calls) <= 1 else "s", write=True)

    def other() -> None:
        mc.step("r", write=True)

    with pytest.raises(mc.NondeterminismError):
        list(mc.ThreadExplorer({"a": flaky, "b": other}))


def test_step_outside_exploration_is_noop() -> None:
    mc.step("r", write=True)
    mc.report_write(True)
    with mc.lock("L"):
        pass


def test_explore_states_count() -> None:
    def next_states(s: tuple[int, int]) -> list[tuple[str, tuple[int, int]]]:
        a, b = s
        result = []
        if a < 2:
            result.append(("inc_a", (a + 1, b)))
        if b < 2:
            result.append(("inc_b", (a, b + 1)))
        return result

    result = mc.explore_states((0, 0), next_states, lambda s: True, is_terminal=lambda s: s == (2, 2))
    assert result.states == 9
    assert result.outcome == mc.Outcome.EXHAUSTIVE
    assert result.violation is None

    truncated = mc.explore_states((0, 0), next_states, is_terminal=lambda s: True, max_states=4)
    assert truncated.outcome == mc.Outcome.TRUNCATED
    assert truncated.states == 4


def _chain(s: int) -> list[tuple[str, int]]:
    return [(f"to{s + 1}", s + 1)] if s < 3 else []


def test_explore_states_invariant_violation() -> None:
    result = mc.explore_states(0, _chain, lambda s: s != 2, is_terminal=lambda s: True)
    assert result.violation is not None
    assert result.violation.kind == "invariant"
    assert result.violation.trace == ("to1", "to2")
    assert result.violation.states == (0, 1, 2)
    assert result.outcome is None


def test_explore_states_deadlock() -> None:
    result = mc.explore_states(0, _chain)
    assert result.violation is not None
    assert result.violation.kind == "deadlock"
    assert result.violation.trace == ("to1", "to2", "to3")


def test_explore_states_error() -> None:
    def next_states(s: int) -> list[tuple[str, int]]:
        if s == 2:
            raise RuntimeError("mismatch")
        return _chain(s)

    result = mc.explore_states(0, next_states, is_terminal=lambda s: True)
    assert result.violation is not None
    assert result.violation.kind == "error"
    assert result.violation.trace == ("to1", "to2")
    assert isinstance(result.violation.exception, RuntimeError)
