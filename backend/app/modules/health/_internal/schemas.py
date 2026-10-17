from typing import Literal

from pydantic import BaseModel, ConfigDict


class Health(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal["ok"]
