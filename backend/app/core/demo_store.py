from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import get_settings

DEMO_CAMPAIGNS = [
    {
        "id": "b4f90d73-4f37-4a6b-9af3-60d1fce0a111",
        "title": "Toyota Corolla Weekend Drive",
        "vendor": "Addis Auto Hub",
        "prize": "Toyota Corolla 2024",
        "description": "A premium urban drive campaign for lucky participants across Ethiopia. The winner receives a fully serviced Corolla with registration support and a free first-year service package.",
        "entry_mode": "FREE",
        "entries": 128,
        "max_entries": 500,
        "status": "ACTIVE",
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        "draw_at": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat(),
        "prize_image_url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=900&q=80",
        "entry_price": None,
        "prize_value": 1200000.0,
        "city": "Addis Ababa",
        "prize_category": "car",
    },
    {
        "id": "2ec5a67c-1eb3-4cdc-b9d2-84c0dcdb114d",
        "title": "Smartphone Elite Bundle",
        "vendor": "City Telecom",
        "prize": "iPhone 15 Pro Max",
        "description": "Enter to win a flagship smartphone package with accessories, warranty coverage and a monthly data bundle for the first six months.",
        "entry_mode": "PROMOTIONAL",
        "entries": 241,
        "max_entries": 800,
        "status": "ACTIVE",
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=18)).isoformat(),
        "draw_at": (datetime.now(timezone.utc) + timedelta(days=25)).isoformat(),
        "prize_image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        "entry_price": None,
        "prize_value": 89000.0,
        "city": "Dire Dawa",
        "prize_category": "smartphone",
    },
    {
        "id": "6c2e8549-31d0-42b5-8ff2-cd4f38be9ae6",
        "title": "Home Upgrade Giveaway",
        "vendor": "Moonlight Home Mart",
        "prize": "Samsung Refrigerator + Washing Machine",
        "description": "A household bundle campaign for families preparing for a fresh new season. Includes installation support and a one-year appliance care plan.",
        "entry_mode": "FREE",
        "entries": 64,
        "max_entries": 220,
        "status": "SCHEDULED",
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
        "draw_at": (datetime.now(timezone.utc) + timedelta(days=42)).isoformat(),
        "prize_image_url": "https://images.unsplash.com/photo-1585518419759-7fe2e0fbf8a6?auto=format&fit=crop&w=900&q=80",
        "entry_price": None,
        "prize_value": 76000.0,
        "city": "Bahir Dar",
        "prize_category": "refrigerator",
    },
]

DEMO_USER = {
    "id": "17b6788a-f89d-4c7d-a7b0-f5101f7cc4ab",
    "phone": "+251911223344",
    "display_name": "Demo participant",
    "email": "demo@assetdraw.dev",
    "role": "PARTICIPANT",
    "status": "active",
}

DEMO_CHALLENGES: dict[str, str] = {}


def is_demo_mode() -> bool:
    settings = get_settings()
    if settings.demo_mode is not None:
        return settings.demo_mode
    return settings.environment != "production"


def demo_health_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "checks": {
            "database": "demo",
            "redis": "demo",
        },
    }


def demo_list_campaigns(status_filter: str | None = None, search: str | None = None) -> list[dict[str, object]]:
    results = [dict(c) for c in DEMO_CAMPAIGNS]
    if status_filter:
        results = [c for c in results if c["status"] == status_filter]
    if search:
        needle = search.lower()
        results = [
            c for c in results
            if needle in str(c["title"]).lower()
            or needle in str(c["description"]).lower()
            or needle in str(c["prize"]).lower()
        ]
    return results


def demo_get_campaign(campaign_id: str) -> dict[str, object] | None:
    for campaign in DEMO_CAMPAIGNS:
        if campaign["id"] == campaign_id:
            return dict(campaign)
    return None


def demo_request_otp(phone: str) -> dict[str, object]:
    challenge_id = str(uuid4())
    code = "123456"
    DEMO_CHALLENGES[challenge_id] = code
    return {
        "challenge_id": challenge_id,
        "detail": "Development OTP issued for demo mode. Use 123456 to continue.",
        "development_code": code,
    }


def demo_verify_otp(challenge_id: str, code: str) -> dict[str, str]:
    expected = DEMO_CHALLENGES.get(challenge_id)
    if not expected or code != expected:
        raise ValueError("Invalid OTP")
    DEMO_CHALLENGES.pop(challenge_id, None)
    return {"access_token": "demo-access-token", "token_type": "bearer"}
