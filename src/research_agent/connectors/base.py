from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import base64
import json
from urllib.error import HTTPError
from urllib import parse, request


@dataclass
class HttpResponse:
    status: int
    body: str

    def json(self) -> Any:
        return json.loads(self.body)


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> HttpResponse:
    req = request.Request(url, headers=headers or {}, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(status=resp.getcode(), body=resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return HttpResponse(status=exc.code, body=body)


def http_post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> HttpResponse:
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    req = request.Request(
        url,
        headers=merged_headers,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(status=resp.getcode(), body=resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return HttpResponse(status=exc.code, body=body)


def basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def append_query(url: str, params: Dict[str, str]) -> str:
    parsed = parse.urlparse(url)
    query = dict(parse.parse_qsl(parsed.query))
    query.update(params)
    return parse.urlunparse(parsed._replace(query=parse.urlencode(query)))
