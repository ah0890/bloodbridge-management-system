import pytest

from app.models.enums import BloodGroup as G
from app.models.enums import Component as C
from app.models.enums import RequestStatus as S
from app.services.compatibility import Compat, compatibility, compatible_donor_groups
from app.services.lifecycle import TERMINAL, TransitionError, check_transition, fulfilment_status


# ---------- ABO/RhD compatibility ----------
@pytest.mark.parametrize(
    "recipient,expected",
    [
        (G.O_NEG, {G.O_NEG}),
        (G.O_POS, {G.O_POS, G.O_NEG}),
        (G.A_NEG, {G.A_NEG, G.O_NEG}),
        (G.B_POS, {G.B_POS, G.B_NEG, G.O_POS, G.O_NEG}),
        (G.AB_POS, set(G)),
        (G.AB_NEG, {G.AB_NEG, G.A_NEG, G.B_NEG, G.O_NEG}),
    ],
)
def test_red_cell_compatibility(recipient, expected):
    assert set(compatible_donor_groups(recipient, C.RED_CELLS)) == expected


def test_whole_blood_requires_abo_identical():
    assert set(compatible_donor_groups(G.B_POS, C.WHOLE_BLOOD)) == {G.B_POS, G.B_NEG}
    assert set(compatible_donor_groups(G.O_NEG, C.WHOLE_BLOOD)) == {G.O_NEG}
    assert compatibility(G.A_POS, G.O_NEG, C.WHOLE_BLOOD).level == Compat.INCOMPATIBLE


def test_plasma_compatibility_is_reversed_and_ignores_rhd():
    assert set(compatible_donor_groups(G.O_NEG, C.PLASMA)) == set(G)
    assert set(compatible_donor_groups(G.AB_POS, C.PLASMA)) == {G.AB_POS, G.AB_NEG}
    assert compatibility(G.A_NEG, G.AB_POS, C.PLASMA).level == Compat.COMPATIBLE
    assert compatibility(G.A_POS, G.O_POS, C.PLASMA).level == Compat.INCOMPATIBLE


def test_o_negative_is_not_a_universal_donor_for_every_component():
    assert compatibility(G.A_POS, G.O_NEG, C.RED_CELLS).level == Compat.COMPATIBLE
    assert compatibility(G.A_POS, G.O_NEG, C.PLASMA).level == Compat.INCOMPATIBLE
    assert compatibility(G.A_POS, G.O_NEG, C.PLATELETS).level == Compat.REVIEW


def test_platelets_non_identical_require_review_not_exclusion_or_acceptance():
    assert compatibility(G.B_POS, G.A_POS, C.PLATELETS).level == Compat.REVIEW
    assert compatibility(G.B_NEG, G.B_POS, C.PLATELETS).level == Compat.REVIEW
    assert compatibility(G.B_POS, G.B_NEG, C.PLATELETS).level == Compat.COMPATIBLE
    assert G.A_POS not in compatible_donor_groups(G.B_POS, C.PLATELETS)
    assert G.A_POS in compatible_donor_groups(G.B_POS, C.PLATELETS, include_review=True)


def test_rhd_negative_recipient_never_offered_positive_red_cells():
    for recipient in (G.O_NEG, G.A_NEG, G.B_NEG, G.AB_NEG):
        assert all(not d.value.endswith("+") for d in compatible_donor_groups(recipient, C.RED_CELLS))


# ---------- request lifecycle ----------
def test_valid_path_to_fulfilled():
    path = [S.SUBMITTED, S.UNDER_REVIEW, S.SEARCHING, S.MATCHES_FOUND, S.COORDINATION]
    for a, b in zip(path, path[1:], strict=False):
        check_transition(a, b, units_fulfilled=0, units_required=2)
    check_transition(S.COORDINATION, S.FULFILLED, units_fulfilled=2, units_required=2)


def test_cannot_skip_review():
    with pytest.raises(TransitionError):
        check_transition(S.SUBMITTED, S.SEARCHING, units_fulfilled=0, units_required=1)


def test_cannot_mark_fulfilled_without_recorded_units():
    with pytest.raises(TransitionError, match="Record issued units"):
        check_transition(S.COORDINATION, S.FULFILLED, units_fulfilled=1, units_required=2)


def test_partial_requires_some_but_not_all_units():
    with pytest.raises(TransitionError):
        check_transition(S.COORDINATION, S.PARTIALLY_FULFILLED, units_fulfilled=0, units_required=2)
    check_transition(S.COORDINATION, S.PARTIALLY_FULFILLED, units_fulfilled=1, units_required=2)


@pytest.mark.parametrize("terminal", sorted(TERMINAL))
def test_terminal_statuses_are_final(terminal):
    for target in S:
        with pytest.raises(TransitionError):
            check_transition(terminal, target, units_fulfilled=5, units_required=5)


def test_fulfilment_status():
    assert fulfilment_status(0, 3) is None
    assert fulfilment_status(1, 3) == S.PARTIALLY_FULFILLED
    assert fulfilment_status(3, 3) == S.FULFILLED
