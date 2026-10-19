"""The only part of the auth module that other modules and app.main can import.

Architect-owned (CODEOWNERS). The auth agent implements _internal/ against
contracts/openapi.yaml. To export more, propose it in the PR.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.modules.auth._internal.dependencies import get_current_user
from app.modules.auth._internal.models import User
from app.modules.auth._internal.router import router


def get_current_user_id(user: Annotated[User, Depends(get_current_user)]) -> UUID:
    """A Depends() provider for other modules (docs/adr/0109).

    It returns the ID of the user of the session cookie, or it raises 401.
    It does not give the User, because the User holds the password hash.
    """
    return user.id


__all__ = ["get_current_user_id", "router"]
