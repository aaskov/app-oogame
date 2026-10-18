"""The only part of the auth module that other modules and app.main can import.

Architect-owned (CODEOWNERS). The auth agent implements _internal/ against
contracts/openapi.yaml. To export more, propose it in the PR.
"""

from app.modules.auth._internal.router import router

__all__ = ["router"]
