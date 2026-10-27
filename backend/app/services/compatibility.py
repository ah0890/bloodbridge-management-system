"""Explicit ABO/RhD compatibility tables, per blood component.

These are conservative *operational* defaults for coordination, versioned so that each match run records which
rules it used. They must be reviewed by qualified blood-bank personnel before any clinical use; crossmatching,
antibody screening and local policy always take precedence.

Conventions
- Red cells / whole blood: recipient may receive red cells lacking antigens they have antibodies against.
  Whole blood (red cells + plasma) is restricted to ABO-identical, RhD-compatible units.
- Plasma / cryoprecipitate: compatibility is reversed (donor plasma must lack antibodies to recipient antigens).
  RhD is not considered for plasma.
- Platelets: ABO-identical preferred; ABO non-identical platelets are flagged for human review rather than excluded
  or silently accepted. RhD-negative recipients receiving RhD-positive platelets are also flagged for review.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.models.enums import BloodGroup as G
from app.models.enums import Component as C

RULES_VERSION = "bb-compat-2026.1"


class Compat(StrEnum):
    IDENTICAL = "identical"
    COMPATIBLE = "compatible"
    REVIEW = "requires_review"
    INCOMPATIBLE = "incompatible"


_ABO = {G.O_POS: "O", G.O_NEG: "O", G.A_POS: "A", G.A_NEG: "A", G.B_POS: "B", G.B_NEG: "B", G.AB_POS: "AB", G.AB_NEG: "AB"}
_RH_POS = {G.O_POS, G.A_POS, G.B_POS, G.AB_POS}

# ABO red-cell compatibility: recipient ABO -> donor ABO groups whose red cells they can receive.
_RBC_ABO: dict[str, set[str]] = {"O": {"O"}, "A": {"A", "O"}, "B": {"B", "O"}, "AB": {"AB", "A", "B", "O"}}
# ABO plasma compatibility: recipient ABO -> donor ABO groups whose plasma they can receive.
_PLASMA_ABO: dict[str, set[str]] = {"O": {"O", "A", "B", "AB"}, "A": {"A", "AB"}, "B": {"B", "AB"}, "AB": {"AB"}}


@dataclass(frozen=True)
class CompatResult:
    level: Compat
    reason: str


def compatibility(recipient: G, donor: G, component: C) -> CompatResult:
    r_abo, d_abo = _ABO[recipient], _ABO[donor]
    r_pos, d_pos = recipient in _RH_POS, donor in _RH_POS

    if component == C.WHOLE_BLOOD:
        if r_abo != d_abo:
            return CompatResult(Compat.INCOMPATIBLE, "Whole blood requires an ABO-identical donor.")
        if d_pos and not r_pos:
            return CompatResult(Compat.INCOMPATIBLE, "RhD-positive blood is not offered to an RhD-negative recipient.")
        return CompatResult(Compat.IDENTICAL if recipient == donor else Compat.COMPATIBLE, "ABO-identical, RhD-compatible.")

    if component == C.RED_CELLS:
        if d_abo not in _RBC_ABO[r_abo]:
            return CompatResult(Compat.INCOMPATIBLE, f"Group {d_abo} red cells are ABO-incompatible with a group {r_abo} recipient.")
        if d_pos and not r_pos:
            return CompatResult(Compat.INCOMPATIBLE, "RhD-positive red cells are not offered to an RhD-negative recipient.")
        if recipient == donor:
            return CompatResult(Compat.IDENTICAL, "ABO/RhD identical.")
        return CompatResult(Compat.COMPATIBLE, f"Group {donor.value} red cells are ABO/RhD compatible with {recipient.value}.")

    if component in (C.PLASMA, C.CRYOPRECIPITATE):
        if d_abo not in _PLASMA_ABO[r_abo]:
            return CompatResult(Compat.INCOMPATIBLE, f"Group {d_abo} plasma is ABO-incompatible with a group {r_abo} recipient.")
        if r_abo == d_abo:
            return CompatResult(Compat.IDENTICAL, "ABO-identical plasma (RhD not considered for plasma).")
        return CompatResult(Compat.COMPATIBLE, f"Group {d_abo} plasma is ABO-compatible with a group {r_abo} recipient.")

    if component == C.PLATELETS:
        if r_abo != d_abo:
            return CompatResult(Compat.REVIEW, "ABO non-identical platelets: acceptability depends on local policy; needs review.")
        if d_pos and not r_pos:
            return CompatResult(Compat.REVIEW, "RhD-positive platelets for an RhD-negative recipient: needs review (anti-D policy).")
        return CompatResult(Compat.IDENTICAL if recipient == donor else Compat.COMPATIBLE, "ABO-identical platelets.")

    return CompatResult(Compat.REVIEW, "No rule defined for this component; needs review.")


def compatible_donor_groups(recipient: G, component: C, include_review: bool = False) -> list[G]:
    """Donor groups that are at least compatible (optionally including review-level) for ``recipient``."""
    allowed = {Compat.IDENTICAL, Compat.COMPATIBLE} | ({Compat.REVIEW} if include_review else set())
    return [d for d in G if compatibility(recipient, d, component).level in allowed]
