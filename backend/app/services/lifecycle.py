"""Blood request lifecycle: the single definition of permitted status transitions."""

from app.models.enums import RequestStatus as S

TERMINAL: frozenset[S] = frozenset({S.FULFILLED, S.CANCELLED, S.CLOSED_UNFULFILLED})
OPEN: frozenset[S] = frozenset(set(S) - TERMINAL)

TRANSITIONS: dict[S, frozenset[S]] = {
    S.SUBMITTED: frozenset({S.UNDER_REVIEW, S.CANCELLED}),
    S.UNDER_REVIEW: frozenset({S.SEARCHING, S.CANCELLED, S.CLOSED_UNFULFILLED}),
    S.SEARCHING: frozenset({S.MATCHES_FOUND, S.PARTIALLY_FULFILLED, S.FULFILLED, S.CANCELLED, S.CLOSED_UNFULFILLED}),
    S.MATCHES_FOUND: frozenset({S.COORDINATION, S.SEARCHING, S.PARTIALLY_FULFILLED, S.FULFILLED, S.CANCELLED, S.CLOSED_UNFULFILLED}),
    S.COORDINATION: frozenset({S.PARTIALLY_FULFILLED, S.FULFILLED, S.SEARCHING, S.CANCELLED, S.CLOSED_UNFULFILLED}),
    S.PARTIALLY_FULFILLED: frozenset({S.FULFILLED, S.COORDINATION, S.SEARCHING, S.CANCELLED, S.CLOSED_UNFULFILLED}),
    S.FULFILLED: frozenset(),
    S.CANCELLED: frozenset(),
    S.CLOSED_UNFULFILLED: frozenset(),
}

# Statuses whose meaning depends on recorded fulfilment quantities, not on a manual choice.
FULFILMENT_STATUSES: frozenset[S] = frozenset({S.PARTIALLY_FULFILLED, S.FULFILLED})


class TransitionError(ValueError):
    pass


def can_transition(current: S, target: S) -> bool:
    return target in TRANSITIONS[current]


def check_transition(current: S, target: S, *, units_fulfilled: int, units_required: int) -> None:
    """Raise TransitionError unless ``current → target`` is permitted given recorded fulfilment."""
    if not can_transition(current, target):
        raise TransitionError(f"Cannot move a request from '{current.value}' to '{target.value}'.")
    if target == S.FULFILLED and units_fulfilled < units_required:
        raise TransitionError(
            f"Only {units_fulfilled} of {units_required} units have been recorded as fulfilled. "
            "Record issued units or confirmed donations before marking the request fulfilled."
        )
    if target == S.PARTIALLY_FULFILLED and not (0 < units_fulfilled < units_required):
        raise TransitionError("Partially fulfilled requires at least one, but not all, units to be recorded as fulfilled.")


def fulfilment_status(units_fulfilled: int, units_required: int) -> S | None:
    if units_fulfilled >= units_required:
        return S.FULFILLED
    if units_fulfilled > 0:
        return S.PARTIALLY_FULFILLED
    return None
