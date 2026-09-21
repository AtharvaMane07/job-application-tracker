from datetime import date


def _create_application(client, headers, **overrides):
    payload = {
        "company": "Acme Corp",
        "role": "Backend Engineer",
        "applied_date": str(date.today()),
        "status": "applied",
        **overrides,
    }
    return client.post("/applications", json=payload, headers=headers)


def test_create_application(client, auth_headers):
    resp = _create_application(client, auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["company"] == "Acme Corp"
    assert body["status"] == "applied"
    assert "id" in body


def test_list_applications_scoped_to_current_user(client, auth_headers):
    _create_application(client, auth_headers, company="Acme")
    _create_application(client, auth_headers, company="Globex")

    resp = client.get("/applications", headers=auth_headers)
    assert resp.status_code == 200
    companies = {a["company"] for a in resp.json()}
    assert companies == {"Acme", "Globex"}


def test_get_application_by_id(client, auth_headers):
    created = _create_application(client, auth_headers).json()
    resp = client.get(f"/applications/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_nonexistent_application_returns_404(client, auth_headers):
    resp = client.get("/applications/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_application_partial_fields(client, auth_headers):
    created = _create_application(client, auth_headers).json()
    resp = client.patch(
        f"/applications/{created['id']}",
        json={"notes": "phone screen went well"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["notes"] == "phone screen went well"
    assert body["company"] == "Acme Corp"  # untouched fields preserved


def test_delete_application(client, auth_headers):
    created = _create_application(client, auth_headers).json()
    resp = client.delete(f"/applications/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/applications/{created['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_status_change_writes_history_row(client, auth_headers):
    created = _create_application(client, auth_headers).json()

    client.patch(
        f"/applications/{created['id']}",
        json={"status": "screening"},
        headers=auth_headers,
    )

    resp = client.get(
        f"/applications/{created['id']}/status-history", headers=auth_headers
    )
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["old_status"] == "applied"
    assert history[0]["new_status"] == "screening"


def test_non_status_update_does_not_write_history_row(client, auth_headers):
    """Edge case: updating notes/company must NOT pollute the audit log."""
    created = _create_application(client, auth_headers).json()

    client.patch(
        f"/applications/{created['id']}",
        json={"notes": "called recruiter"},
        headers=auth_headers,
    )

    resp = client.get(
        f"/applications/{created['id']}/status-history", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_setting_status_to_same_value_does_not_write_history_row(client, auth_headers):
    """Edge case: PATCH with the status it already has shouldn't log a no-op transition."""
    created = _create_application(client, auth_headers).json()  # status: applied

    client.patch(
        f"/applications/{created['id']}",
        json={"status": "applied"},
        headers=auth_headers,
    )

    resp = client.get(
        f"/applications/{created['id']}/status-history", headers=auth_headers
    )
    assert resp.json() == []


def test_user_cannot_access_another_users_application(client, db_session):
    """
    Edge case: ownership isolation. User B must get 404 (not 403 or the
    data) when requesting User A's application — 404 avoids confirming
    to User B that the application id even exists.
    """
    client.post("/auth/register", json={"email": "userA@example.com", "password": "passwordA1"})
    login_a = client.post(
        "/auth/login", json={"email": "userA@example.com", "password": "passwordA1"}
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    app_a = _create_application(client, headers_a).json()

    client.post("/auth/register", json={"email": "userB@example.com", "password": "passwordB1"})
    login_b = client.post(
        "/auth/login", json={"email": "userB@example.com", "password": "passwordB1"}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    resp = client.get(f"/applications/{app_a['id']}", headers=headers_b)
    assert resp.status_code == 404

    resp = client.patch(
        f"/applications/{app_a['id']}", json={"notes": "hijacked"}, headers=headers_b
    )
    assert resp.status_code == 404

    resp = client.delete(f"/applications/{app_a['id']}", headers=headers_b)
    assert resp.status_code == 404
