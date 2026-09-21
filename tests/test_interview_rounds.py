from datetime import date


def _create_application(client, headers):
    payload = {
        "company": "Acme Corp",
        "role": "Backend Engineer",
        "applied_date": str(date.today()),
        "status": "applied",
    }
    return client.post("/applications", json=payload, headers=headers).json()


def test_create_interview_round(client, auth_headers):
    app_obj = _create_application(client, auth_headers)
    resp = client.post(
        f"/applications/{app_obj['id']}/interview-rounds",
        json={"round_type": "Technical", "scheduled_date": "2026-09-01T10:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["round_type"] == "Technical"
    assert body["outcome"] == "pending"


def test_create_round_on_nonexistent_application_returns_404(client, auth_headers):
    resp = client.post(
        "/applications/999999/interview-rounds",
        json={"round_type": "Technical", "scheduled_date": "2026-09-01T10:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_list_rounds_for_application(client, auth_headers):
    app_obj = _create_application(client, auth_headers)
    client.post(
        f"/applications/{app_obj['id']}/interview-rounds",
        json={"round_type": "Phone Screen", "scheduled_date": "2026-09-01T10:00:00"},
        headers=auth_headers,
    )
    client.post(
        f"/applications/{app_obj['id']}/interview-rounds",
        json={"round_type": "Onsite", "scheduled_date": "2026-09-05T10:00:00"},
        headers=auth_headers,
    )

    resp = client.get(
        f"/applications/{app_obj['id']}/interview-rounds", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_round_outcome(client, auth_headers):
    app_obj = _create_application(client, auth_headers)
    round_obj = client.post(
        f"/applications/{app_obj['id']}/interview-rounds",
        json={"round_type": "Technical", "scheduled_date": "2026-09-01T10:00:00"},
        headers=auth_headers,
    ).json()

    resp = client.patch(
        f"/applications/{app_obj['id']}/interview-rounds/{round_obj['id']}",
        json={"outcome": "passed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "passed"


def test_delete_round(client, auth_headers):
    app_obj = _create_application(client, auth_headers)
    round_obj = client.post(
        f"/applications/{app_obj['id']}/interview-rounds",
        json={"round_type": "Technical", "scheduled_date": "2026-09-01T10:00:00"},
        headers=auth_headers,
    ).json()

    resp = client.delete(
        f"/applications/{app_obj['id']}/interview-rounds/{round_obj['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


def test_cannot_access_interview_round_via_another_users_application(client, db_session):
    """
    Edge case: even if User B guesses a valid round_id, nesting it under
    an application_id they don't own must still 404 — ownership is
    checked on the PARENT application, not just the round itself.
    """
    client.post("/auth/register", json={"email": "userA2@example.com", "password": "passwordA1"})
    login_a = client.post(
        "/auth/login", json={"email": "userA2@example.com", "password": "passwordA1"}
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    app_a = _create_application(client, headers_a)
    round_a = client.post(
        f"/applications/{app_a['id']}/interview-rounds",
        json={"round_type": "Technical", "scheduled_date": "2026-09-01T10:00:00"},
        headers=headers_a,
    ).json()

    client.post("/auth/register", json={"email": "userB2@example.com", "password": "passwordB1"})
    login_b = client.post(
        "/auth/login", json={"email": "userB2@example.com", "password": "passwordB1"}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    resp = client.get(
        f"/applications/{app_a['id']}/interview-rounds/{round_a['id']}", headers=headers_b
    )
    assert resp.status_code == 404
