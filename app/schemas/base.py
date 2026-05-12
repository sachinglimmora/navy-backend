from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class GenericResponse[T](BaseModel):
    success: bool
    message: str
    data: T | None = None
