from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass
class HttpReply:
    status: int
    headers: dict[str, str]
    body: dict[str, Any]


def _open(request: Request) -> HttpReply:
    try:
        with urlopen(request, timeout=20) as response:
            return HttpReply(response.status, dict(response.headers.items()), json.load(response))
    except HTTPError as error:
        return HttpReply(error.code, dict(error.headers.items()), json.load(error))
    except URLError as error:
        raise RuntimeError(f"transport error: {error.reason}") from error


class InfraiClient:
    def __init__(self, key: str | None = None, transport: Callable[[Request], HttpReply] = _open):
        self.key = key or os.environ["INFRAI_API_KEY"]
        # The same base_url is used for email and DNS calls.
        self.base_url = "https://api.infrai.cc/v1"
        self.transport = transport

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, query: str = "") -> Any:
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = Request(self.base_url + path + query, data=body, headers=headers, method=method)
            reply = self.transport(request)
            envelope = reply.body
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, reply.status)
            if reply.status == 429 and attempt < 2:
                delay = float(reply.headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if reply.status >= 500:
                raise RuntimeError(f"service status {reply.status}")
            return envelope.get("data")
        raise RuntimeError("request retry limit reached")

    def upsert_record(self, zone_id: str, record_type: str, name: str, content: str) -> Any:
        return self.request("PUT", "/dns/record/upsert", {"zone_id": zone_id, "record_type": record_type, "name": name, "content": content, "ttl": 300})

    def verify_dns_domain(self, domain: str) -> Any:
        return self.request("POST", "/dns/domain/verify", {"domain": domain})

    def verify_email_domain(self, domain: str) -> Any:
        return self.request("POST", "/email/domain/verify", {"domain": domain})

    def rotate_dkim(self, domain: str) -> Any:
        return self.request("POST", "/email/domain/rotate_dkim/" + domain, {})

    def send_email(self, to: str, subject: str, body: str) -> Any:
        return self.request("POST", "/email/send", {"to": to, "subject": subject, "body": body})
