"""Role → permission mapping. The backend is the source of truth; the frontend only mirrors it."""

from enum import StrEnum

from app.models.enums import Role


class Perm(StrEnum):
    DASHBOARD_VIEW = "dashboard:view"
    DONORS_READ = "donors:read"
    DONORS_WRITE = "donors:write"
    DONORS_CONTACT = "donors:contact"  # see contact details and record contact attempts
    DONORS_EXPORT = "donors:export"
    DONATIONS_READ = "donations:read"
    DONATIONS_WRITE = "donations:write"
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"  # scoped to own organisation for bank managers
    REQUESTS_READ = "requests:read"
    REQUESTS_MANAGE = "requests:manage"
    MATCHING_RUN = "matching:run"
    BANKS_READ = "banks:read"
    BANKS_MANAGE = "banks:manage"
    BANKS_EDIT_OWN = "banks:edit_own"
    GEO_VIEW = "geo:view"
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
    NOTIFICATIONS_VIEW = "notifications:view"
    AUDIT_READ = "audit:read"
    USERS_MANAGE = "users:manage"
    SETTINGS_MANAGE = "settings:manage"
    IMPORTS_RUN = "imports:run"


_COMMON = {
    Perm.DASHBOARD_VIEW,
    Perm.INVENTORY_READ,
    Perm.REQUESTS_READ,
    Perm.BANKS_READ,
    Perm.GEO_VIEW,
    Perm.REPORTS_VIEW,
    Perm.NOTIFICATIONS_VIEW,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Perm]] = {
    Role.ADMIN: frozenset(Perm),
    Role.BANK_MANAGER: frozenset(
        _COMMON
        | {
            Perm.INVENTORY_WRITE,
            Perm.REQUESTS_MANAGE,
            Perm.DONATIONS_READ,
            Perm.DONATIONS_WRITE,
            Perm.BANKS_EDIT_OWN,
            Perm.REPORTS_EXPORT,
            Perm.AUDIT_READ,  # own organisation's events only
        }
    ),
    Role.COORDINATOR: frozenset(
        _COMMON
        | {
            Perm.DONORS_READ,
            Perm.DONORS_WRITE,
            Perm.DONORS_CONTACT,
            Perm.DONORS_EXPORT,
            Perm.DONATIONS_READ,
            Perm.DONATIONS_WRITE,
            Perm.REQUESTS_MANAGE,
            Perm.MATCHING_RUN,
            Perm.REPORTS_EXPORT,
        }
    ),
}


def has_perm(role: Role, perm: Perm) -> bool:
    return perm in ROLE_PERMISSIONS.get(role, frozenset())
