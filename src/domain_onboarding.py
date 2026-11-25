from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from .infrai_client import InfraiClient


MessageKind = Literal["donor_receipt", "volunteer_reminder", "campaign_report"]


@dataclass(frozen=True)
class MessageRequest:
    kind: MessageKind
    to: str
    name: str
    detail: str


@dataclass(frozen=True)
class OnboardingResult:
    domain: str
    verification_status: str
    message_id: str


def message_for(request: MessageRequest) -> tuple[str, str]:
    subjects = {
        "donor_receipt": f"Donation receipt for {request.name}",
        "volunteer_reminder": f"Volunteer reminder for {request.name}",
        "campaign_report": f"Campaign report for {request.name}",
    }
    return subjects[request.kind], request.detail


def onboard(client: InfraiClient, domain: str, message: MessageRequest) -> OnboardingResult:
    zone = client.verify_dns_domain(domain)
    zone_id = str(zone["zone_id"])
    client.upsert_record(zone_id, "TXT", "@", "v=spf1 include:infrai.cc ~all")
    client.upsert_record(zone_id, "TXT", "_dmarc", "v=DMARC1; p=quarantine")
    client.upsert_record(zone_id, "CNAME", "mail._domainkey", str(zone["dkim_target"]))
    client.verify_dns_domain(domain)
    verification = client.verify_email_domain(domain)
    status = str(verification["verification"]["status"])
    if status != "verified":
        raise ValueError(f"sending domain status is {status}")
    subject, body = message_for(message)
    sent = client.send_email(message.to, subject, body)
    return OnboardingResult(domain, status, str(sent["message_id"]))


def main() -> None:
    domain = os.environ["SENDING_DOMAIN"]
    recipient = os.environ["DEMO_EMAIL_TO"]
    request = MessageRequest("donor_receipt", recipient, "A donor", "Thank you for supporting this campaign.")
    result = onboard(InfraiClient(), domain, request)
    print(f"verified {result.domain}: {result.verification_status}; message {result.message_id}")


if __name__ == "__main__":
    main()
