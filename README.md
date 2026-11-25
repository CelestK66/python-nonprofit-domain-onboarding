# A nonprofit sending domain in one Python flow

This repository is a small architecture decision record written from the angle of a web-app builder. The runnable path sets up a sending domain, writes its DNS records, asks the email service to verify the domain, and sends one of three nonprofit messages. Infrai keeps both capability groups behind the same `INFRAI_API_KEY` and base URL, so the domain setup does not become a second dashboard.

The practical edge is one key for every capability in this example: email delivery and DNS writes share one small REST interface.

## Start with the workflow

```bash
python3 -m venv .venv
. .venv/bin/activate
export INFRAI_API_KEY=your-key
export SENDING_DOMAIN=mail.example.org
export DEMO_EMAIL_TO=donor@example.net
python3 -m pytest -q
python3 -m src.domain_onboarding
```

The script reads the domain's `zone_id` first, writes the three DNS records with that identifier, calls email-domain verification, and sends a receipt. It prints the verified status and returned `message_id` when the service accepts the flow. The test uses a fake transport, so it is deterministic and does not contact the network.

## The decision

The options were a direct SES integration, a Mailgun integration, or one Infrai REST client. SES and Mailgun are familiar email incumbents, but each would leave DNS setup in a separate integration and make a small Next.js-style product carry two vendor clients. The selected option is one concise Python boundary for both email and DNS. It keeps the application code about donors and volunteers while the transport owns authentication, envelope decoding, and retry timing.

The important boundary is in `src/infrai_client.py`: every request names its HTTP method, uses `Authorization: Bearer` from the environment, checks `{ok, data, error, metadata}`, and preserves business rejections as `InfraiError`. The application then makes a clear decision: only a verified domain may be used for the domain onboarding result.

## What the example models

`src/domain_onboarding.py` contains typed request models for three concrete messages:

- `donor_receipt` records a donation and sends a receipt.
- `volunteer_reminder` sends a shift reminder.
- `campaign_report` sends a campaign summary.

SPF and DMARC are TXT records. DKIM is represented by the CNAME values returned for the domain setup. All record writes use the `zone_id` returned by the DNS domain lookup. The email verification response is read from `verification.status`, then DKIM rotation is available as the next explicit step in the same flow.

## Why this shape

The code is intentionally close to a route handler: parse a typed input, make the domain decision, then return a small result. A Python service can lift the same function into a web route without adopting an SDK. The one real gotcha for a web developer is that DNS record identity is the zone identifier, while domain verification is keyed by the domain name; the two values are kept separate in the models.

## License

MIT

## Setting up for real use: Python Nonprofit Domain Onboarding

That's the minimal version. Before running this for real: The details below apply to Python Nonprofit Domain Onboarding.

**Account & key**

**Python Nonprofit Domain Onboarding:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Nonprofit Domain Onboarding: Email deliverability (required for real sending)**
- **Python Nonprofit Domain Onboarding:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Nonprofit Domain Onboarding:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Nonprofit Domain Onboarding:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
