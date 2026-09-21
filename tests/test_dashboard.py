from datetime import date


def _create_application(client, headers, status="applied"):
    payload = {
        "company": "Acme Corp",
        "role": "Backend Engineer",
        "applied_date": str(date.today()),
        "status": status,
    }
    return client.post("/applications", json=payload, headers=headers).json()


def test_dashboard_empty_when_no_applications(client, auth_headers):
    resp = client.get("/applications/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"counts_by_status": {}, "total": 0}


def test_dashboard_counts_by_status(client, auth_headers):
    _create_application(client, auth_headers, status="applied")
    _create_application(client, auth_headers, status="applied")
    _create_application(client, auth_headers, status="interview")

    resp = client.get("/applications/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["counts_by_status"] == {"applied": 2, "interview": 1}
    assert body["total"] == 3


def test_dashboard_reflects_status_change_immediately(client, auth_headers):
    """
    Edge case: cache invalidation. Without it, this would return stale
    counts from before the PATCH.
    """
    created = _create_application(client, auth_headers, status="applied")

    first = client.get("/applications/dashboard/summary", headers=auth_headers).json()
    assert first["counts_by_status"] == {"applied": 1}

    client.patch(
        f"/applications/{created['id']}", json={"status": "offer"}, headers=auth_headers
    )

    second = client.get("/applications/dashboard/summary", headers=auth_headers).json()
    assert second["counts_by_status"] == {"offer": 1}


def test_dashboard_reflects_deletion(client, auth_headers):
    created = _create_application(client, auth_headers, status="applied")
    client.get("/applications/dashboard/summary", headers=auth_headers)  # warm the cache

    client.delete(f"/applications/{created['id']}", headers=auth_headers)

    resp = client.get("/applications/dashboard/summary", headers=auth_headers).json()
    assert resp == {"counts_by_status": {}, "total": 0}


def test_dashboard_is_isolated_per_user(client, db_session):
    """Edge case: User A's counts must never leak into User B's dashboard."""
    client.post("/auth/register", json={"email": "dashA@example.com", "password": "passwordA1"})
    login_a = client.post(
        "/auth/login", json={"email": "dashA@example.com", "password": "passwordA1"}
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    _create_application(client, headers_a, status="applied")
    _create_application(client, headers_a, status="applied")

    client.post("/auth/register", json={"email": "dashB@example.com", "password": "passwordB1"})
    login_b = client.post(
        "/auth/login", json={"email": "dashB@example.com", "password": "passwordB1"}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    _create_application(client, headers_b, status="offer")

    resp_a = client.get("/applications/dashboard/summary", headers=headers_a).json()
    resp_b = client.get("/applications/dashboard/summary", headers=headers_b).json()

    assert resp_a["total"] == 2
    assert resp_b["total"] == 1
