from __future__ import annotations


def test_healthcheck_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "test",
        "now": "2024-05-23T08:30:00+00:00",
    }
