"""The SQLAlchemy table definitions (docs/adr/0104). Architect-owned (CODEOWNERS).

Repositories read and write these classes. A change here needs a new Alembic
migration in backend/migrations/.
"""

from app.shared.orm.base import Base
from app.shared.orm.users import UserRow

__all__ = ["Base", "UserRow"]
