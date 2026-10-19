"""The only part of the planets module that other modules and app.main can import.

Architect-owned (CODEOWNERS). The planets agent implements _internal/ against
contracts/openapi.yaml. To export more, propose it in the PR.
"""

from app.modules.planets._internal.router import router

__all__ = ["router"]
