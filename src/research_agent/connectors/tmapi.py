from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .base import append_query, http_get


@dataclass
class TmapiClient:
    token: str
    base_url: str = "http://api.tmapi.top"

    def get(self, path: str, **params: str) -> Dict[str, Any]:
        url = append_query(f"{self.base_url.rstrip('/')}/{path.lstrip('/')}", {"apiToken": self.token, **params})
        return http_get(url).json()
