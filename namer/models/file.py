from pony.orm import Optional, PrimaryKey, Required
from typing import TYPE_CHECKING

from namer.models import db

# Use TYPE_CHECKING pattern to resolve mypy error: "Name 'db.Entity' is not defined"
# db.Entity exists at runtime but not during static type checking because Pony ORM
# uses dynamic entity creation. The Entity type stub provides proper type hints.
if TYPE_CHECKING:
    from pony.orm.core import Entity as _Entity

    EntityBase = _Entity
else:
    EntityBase = db.Entity  # type: ignore[attr-defined]


class File(EntityBase):
    id = PrimaryKey(int, auto=True)

    file_name = Required(str)
    file_size = Required(int, size=64)
    file_time = Required(float)

    duration = Optional(int)
    phash = Optional(str)
    oshash = Optional(str)
