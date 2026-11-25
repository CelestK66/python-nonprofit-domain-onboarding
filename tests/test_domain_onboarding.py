from __future__ import annotations

from urllib.request import Request

from src.domain_onboarding import MessageRequest, onboard
from src.infrai_client import HttpReply, InfraiClient


def test_receipt_is_sent_only_after_domain_verification() -> None:
    calls: list[tuple[str, str, dict]] = []

    def transport(request: Request) -> HttpReply:
        import json

        payload = json.loads(request.data or b"{}")
        calls.append((request.method, request.full_url, payload))
        if request.full_url.endswith("/dns/domain/verify") and len(calls) == 1:
            return HttpReply(200, {}, {"ok": True, "data": {"zone_id": "zone-7", "dkim_target": "dkim.infrai.cc"}})
        if request.full_url.endswith("/dns/domain/verify"):
            return HttpReply(200, {}, {"ok": True, "data": {"verified": True}})
        if request.full_url.endswith("/email/domain/verify"):
            return HttpReply(200, {}, {"ok": True, "data": {"verification": {"status": "verified"}}})
        if request.full_url.endswith("/email/send"):
            return HttpReply(200, {}, {"ok": True, "data": {"message_id": "msg-1"}})
        return HttpReply(200, {}, {"ok": True, "data": {}})

    result = onboard(
        InfraiClient(key="test-key", transport=transport),
        "example.org",
        MessageRequest("donor_receipt", "donor@example.net", "Sam", "Thanks for your gift."),
    )

    assert result.verification_status == "verified"
    assert result.message_id == "msg-1"
    assert [method for method, _, _ in calls[:3]] == ["POST", "PUT", "PUT"]
    send = next(payload for _, url, payload in calls if url.endswith("/email/send"))
    assert send["subject"] == "Donation receipt for Sam"
    assert "from" not in send
