__lazy_modules__ = ["collections", "collections.abc", "contextlib", "dataclasses", "enum", "threading", "time", "typing"]

import collections
import collections.abc
import contextlib
import dataclasses
import enum
import threading
import time
import typing

__all__ = [
    "ExplorationAborted",
    "NondeterminismError",
    "Outcome",
    "StateExploration",
    "StateViolation",
    "Step",
    "StepTimeoutError",
    "ThreadExplorer",
    "ThreadRun",
    "acquire",
    "explore_states",
    "independent_by_resource",
    "lock",
    "release",
    "report_write",
    "step",
]


class Outcome(enum.Enum):
    EXHAUSTIVE = "exhaustive"
    TRUNCATED = "truncated"


class ExplorationAborted(BaseException):  # noqa: N818
    pass


class NondeterminismError(Exception):
    pass


class StepTimeoutError(Exception):
    def __init__(self, actor: str, steps: typing.Sequence["Step"], unfinished_actors: typing.Sequence[str]) -> None:
        self.actor = actor
        self.steps = tuple(steps)
        self.unfinished_actors = tuple(unfinished_actors)
        super().__init__(
            f"主体 {actor!r} が上限時間内に次の通知へ達しなかった。"
            f"手順の列: {[_format_step(s) for s in self.steps]}。"
            f"終了を確認できなかった主体: {list(self.unfinished_actors)}。"
            "同じプロセスの状態は時間切れした主体がまだ触れうるため、このプロセスで検査を続けない"
        )


@dataclasses.dataclass(frozen=True)
class Step:
    actor: str
    resource: collections.abc.Hashable
    write: bool
    label: str | None = None
    kind: typing.Literal["access", "acquire"] = "access"
    wrote: bool | None = None

    @property
    def effective_write(self) -> bool:
        return self.write if self.wrote is None else self.wrote


def independent_by_resource(a: Step, b: Step) -> bool:
    return a.resource != b.resource or (not a.effective_write and not b.effective_write)


@dataclasses.dataclass(frozen=True)
class ThreadRun:
    steps: tuple[Step, ...]
    returns: dict[str, typing.Any]
    exceptions: dict[str, BaseException]
    deadlock: bool
    blocked: tuple[str, ...]
    equivalent: bool

    @property
    def schedule(self) -> tuple[str, ...]:
        return tuple(s.actor for s in self.steps)


_local = threading.local()


def step(resource: collections.abc.Hashable, *, write: bool, label: str | None = None) -> None:
    binding = getattr(_local, "binding", None)
    if binding is not None:
        binding[0].park(binding[1], Step(binding[1], resource, write, label, "access"))


def acquire(lock_id: collections.abc.Hashable, *, label: str | None = None) -> None:
    binding = getattr(_local, "binding", None)
    if binding is not None:
        binding[0].park(binding[1], Step(binding[1], lock_id, True, label, "acquire"))


def release(lock_id: collections.abc.Hashable) -> None:
    binding = getattr(_local, "binding", None)
    if binding is not None:
        binding[0].release(binding[1], lock_id)


@contextlib.contextmanager
def lock(lock_id: collections.abc.Hashable, *, label: str | None = None) -> typing.Generator[None, None, None]:
    acquire(lock_id, label=label)
    try:
        yield
    finally:
        release(lock_id)


def report_write(wrote: bool) -> None:
    binding = getattr(_local, "binding", None)
    if binding is not None:
        binding[0].report_write(binding[1], wrote)


class ThreadExplorer:
    def __init__(
        self,
        actors: typing.Mapping[str, typing.Callable[[], typing.Any]],
        setup: typing.Callable[[], typing.Any] | None = None,
        *,
        step_timeout: float = 10.0,
        max_runs: int | None = None,
        count_equivalent: bool = True,
        independent: typing.Callable[[Step, Step], bool] = independent_by_resource,
        backtrack_by: typing.Literal["reported", "planned"] = "reported",
    ) -> None:
        if not actors:
            raise ValueError("主体を1つ以上指定してください")
        if backtrack_by not in ("reported", "planned"):
            raise ValueError(f"backtrack_byには'reported'か'planned'を指定してください: {backtrack_by!r}")
        self.actors = dict(actors)
        self.setup = setup
        self.step_timeout = step_timeout
        self.max_runs = max_runs
        self.count_equivalent = count_equivalent
        self.independent = independent
        self.backtrack_by = backtrack_by
        self.outcome: Outcome | None = None
        self.runs = 0
        self.equivalent_runs = 0
        self._started = False
        self._failed = False

    def __iter__(self) -> typing.Iterator[ThreadRun]:
        if self._started:
            raise RuntimeError("ThreadExplorerの反復は1回だけ行える。新しいThreadExplorerを作成してください")
        self._started = True
        return self._explore()

    def replay(self, schedule: typing.Sequence[str]) -> ThreadRun:
        if self._failed:
            raise RuntimeError("時間切れで失敗した探索のプロセスでは再実行できない")
        run, _ = self._execute([], list(schedule))
        return run

    def _explore(self) -> typing.Iterator[ThreadRun]:
        prefix: list[_Node] = []
        counted = 0
        while True:
            run, nodes = self._execute(prefix, None)
            self.runs += 1
            if run.equivalent:
                self.equivalent_runs += 1
            if self.count_equivalent or not run.equivalent:
                counted += 1
            yield run
            next_prefix = _backtrack(nodes)
            if next_prefix is None:
                self.outcome = Outcome.EXHAUSTIVE
                return
            if self.max_runs is not None and counted >= self.max_runs:
                self.outcome = Outcome.TRUNCATED
                return
            prefix = next_prefix

    def _execute(self, prefix: list["_Node"], schedule: list[str] | None) -> tuple[ThreadRun, list["_Node"]]:
        if self.setup is not None:
            self.setup()
        names = list(self.actors)
        ctx = _RunContext(names, self.step_timeout)
        threads: dict[str, threading.Thread] = {}
        for name in names:
            thread = threading.Thread(
                target=_actor_main, args=(ctx, name, self.actors[name]), name=f"modelcheck-{name}", daemon=True
            )
            threads[name] = thread
            with ctx.cond:
                ctx.status[name] = "running"
            thread.start()
            if not ctx.wait_parked(name):
                self._fail(ctx, threads, name)

        nodes: list[_Node] = []
        sleep: dict[str, Step] = {}
        marked = False
        blocked: tuple[str, ...] = ()
        depth = 0
        while True:
            with ctx.cond:
                waiting = [n for n in names if ctx.status[n] == "waiting"]
                pending = {n: ctx.pending[n] for n in waiting}
                enabled = tuple(n for n in waiting if pending[n].kind != "acquire" or pending[n].resource not in ctx.locks)
            if not waiting:
                break
            if not enabled:
                blocked = tuple(waiting)
                break

            node: _Node | None = None
            if schedule is not None:
                chosen = schedule[depth] if depth < len(schedule) else enabled[0]
                if chosen not in enabled:
                    self._abort_and_raise(
                        ctx,
                        threads,
                        ValueError(f"選択の列の{depth}番目の主体 {chosen!r} は選択できない。選択できる主体: {list(enabled)}"),
                    )
            elif depth < len(prefix):
                node = prefix[depth]
                if node.enabled != enabled or node.keys != _pending_keys(pending):
                    self._abort_and_raise(
                        ctx,
                        threads,
                        NondeterminismError(
                            f"同じ選択の列の再実行で{depth}番目の選択点の候補が変わった。"
                            f"前回: {node.keys}、今回: {_pending_keys(pending)}。"
                            f"準備処理が環境を毎回同じ状態に作り直しているか、主体の処理が決定的かを確かめてください"
                        ),
                    )
                chosen = node.chosen
                sleep = node.sleep
            else:
                candidates = [n for n in enabled if n not in sleep]
                if not candidates:
                    marked = True
                chosen = candidates[0] if candidates else enabled[0]
                node = _Node(enabled, pending, dict(sleep), {}, chosen, marked)
            if node is not None:
                nodes.append(node)

            with ctx.cond:
                st = ctx.pending.pop(chosen)
                if st.kind == "acquire":
                    ctx.locks[st.resource] = chosen
                ctx.trace.append(st)
                ctx.last_index[chosen] = len(ctx.trace) - 1
                ctx.status[chosen] = "running"
                ctx.go.add(chosen)
                ctx.cond.notify_all()
            if not ctx.wait_parked(chosen):
                self._fail(ctx, threads, chosen)

            if node is not None and depth >= len(prefix) - 1:
                with ctx.cond:
                    executed = ctx.trace[-1]
                if self.backtrack_by == "planned" and depth == len(prefix) - 1:
                    executed = node.pending[chosen]
                sleep = {u: s for u, s in {**node.sleep, **node.done}.items() if u != chosen and self.independent(s, executed)}
            depth += 1

        if schedule is not None and depth < len(schedule):
            self._abort_and_raise(
                ctx, threads, ValueError(f"選択の列が実行より長い。実行した選択は{depth}個、指定は{len(schedule)}個")
            )
        if blocked:
            unfinished = _abort(ctx, threads, self.step_timeout)
            if unfinished:
                self._failed = True
                raise StepTimeoutError(unfinished[0], ctx.trace, unfinished)
        else:
            for thread in threads.values():
                thread.join(self.step_timeout)
        with ctx.cond:
            run = ThreadRun(
                steps=tuple(ctx.trace),
                returns=dict(ctx.returns),
                exceptions=dict(ctx.exceptions),
                deadlock=bool(blocked),
                blocked=blocked,
                equivalent=marked,
            )
        return run, nodes

    def _fail(self, ctx: "_RunContext", threads: dict[str, threading.Thread], actor: str) -> typing.NoReturn:
        self._failed = True
        unfinished = _abort(ctx, threads, self.step_timeout)
        raise StepTimeoutError(actor, ctx.trace, unfinished)

    def _abort_and_raise(self, ctx: "_RunContext", threads: dict[str, threading.Thread], error: Exception) -> typing.NoReturn:
        unfinished = _abort(ctx, threads, self.step_timeout)
        if unfinished:
            self._failed = True
            raise StepTimeoutError(unfinished[0], ctx.trace, unfinished) from error
        raise error


@dataclasses.dataclass
class _Node:
    enabled: tuple[str, ...]
    pending: dict[str, Step]
    sleep: dict[str, Step]
    done: dict[str, Step]
    chosen: str
    forced: bool

    @property
    def keys(self) -> list[tuple[str, typing.Any, bool, str]]:
        return _pending_keys(self.pending)


def _pending_keys(pending: dict[str, Step]) -> list[tuple[str, typing.Any, bool, str]]:
    return [(n, s.resource, s.write, s.kind) for n, s in pending.items()]


def _backtrack(nodes: list[_Node]) -> list[_Node] | None:
    while nodes:
        node = nodes[-1]
        if not node.forced:
            node.done[node.chosen] = node.pending[node.chosen]
            for name in node.enabled:
                if name not in node.sleep and name not in node.done:
                    node.chosen = name
                    return nodes
        nodes.pop()
    return None


class _RunContext:
    def __init__(self, names: list[str], step_timeout: float) -> None:
        self.cond = threading.Condition()
        self.step_timeout = step_timeout
        self.status: dict[str, typing.Literal["new", "running", "waiting", "done"]] = dict.fromkeys(names, "new")
        self.pending: dict[str, Step] = {}
        self.go: set[str] = set()
        self.aborted = False
        self.locks: dict[collections.abc.Hashable, str] = {}
        self.trace: list[Step] = []
        self.last_index: dict[str, int] = {}
        self.returns: dict[str, typing.Any] = {}
        self.exceptions: dict[str, BaseException] = {}

    def park(self, actor: str, pending: Step) -> None:
        with self.cond:
            if self.aborted:
                raise ExplorationAborted
            self.pending[actor] = pending
            self.status[actor] = "waiting"
            self.cond.notify_all()
            while actor not in self.go:
                if self.aborted:
                    raise ExplorationAborted
                self.cond.wait()
            if self.aborted:
                raise ExplorationAborted
            self.go.discard(actor)

    def release(self, actor: str, lock_id: collections.abc.Hashable) -> None:
        with self.cond:
            if self.aborted:
                raise ExplorationAborted
            if self.locks.get(lock_id) != actor:
                raise RuntimeError(f"主体 {actor!r} はロック {lock_id!r} を持っていない")
            del self.locks[lock_id]

    def report_write(self, actor: str, wrote: bool) -> None:
        with self.cond:
            if self.aborted:
                raise ExplorationAborted
            index = self.last_index.get(actor)
            if index is None:
                raise RuntimeError(f"主体 {actor!r} にはまだ実行した手順が無い。report_write()は手順の実行後に呼ぶ")
            self.trace[index] = dataclasses.replace(self.trace[index], wrote=wrote)

    def wait_parked(self, actor: str) -> bool:
        deadline = time.monotonic() + self.step_timeout
        with self.cond:
            while self.status[actor] == "running":
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self.cond.wait(remaining)
        return True


def _actor_main(ctx: _RunContext, name: str, func: typing.Callable[[], typing.Any]) -> None:
    _local.binding = (ctx, name)
    try:
        result = func()
    except ExplorationAborted:
        pass
    except BaseException as e:  # noqa: BLE001  # 主体の例外は実行の結果として利用者へ返す
        with ctx.cond:
            ctx.exceptions[name] = e
    else:
        with ctx.cond:
            ctx.returns[name] = result
    finally:
        _local.binding = None
        with ctx.cond:
            ctx.status[name] = "done"
            ctx.cond.notify_all()


def _abort(ctx: _RunContext, threads: dict[str, threading.Thread], timeout: float) -> list[str]:
    with ctx.cond:
        ctx.aborted = True
        ctx.cond.notify_all()
    deadline = time.monotonic() + timeout
    unfinished = []
    for name, thread in threads.items():
        thread.join(max(0.0, deadline - time.monotonic()))
        if thread.is_alive():
            unfinished.append(name)
    return unfinished


def _format_step(s: Step) -> str:
    access = "acquire" if s.kind == "acquire" else ("write" if s.write else "read")
    label = f" {s.label}" if s.label is not None else ""
    return f"{s.actor}: {access} {s.resource!r}{label}"


@dataclasses.dataclass(frozen=True)
class StateViolation[S]:
    kind: typing.Literal["invariant", "deadlock", "error"]
    state: S
    trace: tuple[str, ...]
    states: tuple[S, ...]
    exception: BaseException | None = None


@dataclasses.dataclass(frozen=True)
class StateExploration[S]:
    states: int
    outcome: Outcome | None
    violation: StateViolation[S] | None


def explore_states[S: collections.abc.Hashable](
    initial: S,
    next_states: typing.Callable[[S], typing.Iterable[tuple[str, S]]],
    invariant: typing.Callable[[S], bool] | None = None,
    *,
    is_terminal: typing.Callable[[S], bool] | None = None,
    max_states: int | None = None,
) -> StateExploration[S]:
    parents: dict[S, tuple[S, str] | None] = {initial: None}

    def violation(
        kind: typing.Literal["invariant", "deadlock", "error"], state: S, exception: BaseException | None = None
    ) -> StateExploration[S]:
        trace: list[str] = []
        path = [state]
        current = state
        while (parent := parents[current]) is not None:
            current, name = parent
            trace.append(name)
            path.append(current)
        return StateExploration(
            states=len(parents),
            outcome=None,
            violation=StateViolation(kind, state, tuple(reversed(trace)), tuple(reversed(path)), exception),
        )

    queue = collections.deque([initial])
    while queue:
        state = queue.popleft()
        try:
            ok = invariant is None or invariant(state)
        except Exception as e:  # noqa: BLE001  # 利用者の判定の例外は手順の列とともに違反として返す
            return violation("error", state, e)
        if not ok:
            return violation("invariant", state)
        try:
            successors = list(next_states(state))
            terminal = not successors and is_terminal is not None and is_terminal(state)
        except Exception as e:  # noqa: BLE001  # 同上
            return violation("error", state, e)
        if not successors and not terminal:
            return violation("deadlock", state)
        for name, nxt in successors:
            if nxt in parents:
                continue
            if max_states is not None and len(parents) >= max_states:
                return StateExploration(states=len(parents), outcome=Outcome.TRUNCATED, violation=None)
            parents[nxt] = (state, name)
            queue.append(nxt)
    return StateExploration(states=len(parents), outcome=Outcome.EXHAUSTIVE, violation=None)
