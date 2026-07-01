from typing import Mapping
from fastapi.exceptions import HTTPException

class Http404(HTTPException):
    """Шорткат для HTTPException с 404 кодом."""
    def __init__(self, detail: str, headers: Mapping[str, str] | None = None):
        super().__init__(404, detail, headers)
