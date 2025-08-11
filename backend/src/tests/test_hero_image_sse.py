import json
import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import app


class DummyCreds:
    def __init__(self, token: str):
        self.credentials = token


def _make_jwt(user_id: str = "user_test"):
    import jwt
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    payload = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "role": "PREMIUM",
        "iat": int(datetime.utcnow().timestamp())
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.timeout(30)
def test_hero_image_stream_early(monkeypatch):
    """Ensure hero_image_url appears in SSE before final completion status."""
    token = _make_jwt()

    from main import get_current_user

    async def fake_user(*args, **kwargs):  # type: ignore
        return await get_current_user(DummyCreds(token))  # type: ignore

    monkeypatch.setattr("main.get_current_user", fake_user)

    client = TestClient(app)

    resp = client.post(
        "/generate-blog",
        headers={"Authorization": f"Bearer {token}"},
        json={"instructions": "Write a brief tech blog about async Python."}
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]

    with client.stream("GET", f"/stream/{task_id}?token={token}") as stream:
        hero_seen = False
        completion_seen = False
        for line in stream.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: "):])
            if 'hero_image_url' in payload and not hero_seen:
                hero_seen = True
            if payload.get('status') == 'completed':
                completion_seen = True
                break
        assert hero_seen, "Expected hero_image_url before completion"
        assert completion_seen, "Expected completion event"
