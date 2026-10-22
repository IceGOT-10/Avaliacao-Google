"""Regras puras de autorização por papel."""

ROLE_RANK = {"manager": 1, "owner": 2, "admin": 3}


def role_allows(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(minimum, 0)

