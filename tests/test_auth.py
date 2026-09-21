def test_register_creates_user(client):
    resp = client.post(
        "/auth/register", json={"email": "new@example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client, registered_user):
    resp = client.post("/auth/register", json=registered_user)
    assert resp.status_code == 409


def test_login_success_returns_token_pair(client, registered_user):
    resp = client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client, registered_user):
    resp = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_email_rejected(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert resp.status_code == 401


def test_login_wrong_password_and_nonexistent_email_return_identical_error(
    client, registered_user
):
    """
    Edge case: the error for 'wrong password' and 'no such account' must be
    indistinguishable, otherwise the endpoint lets an attacker enumerate
    which emails are registered.
    """
    wrong_password_resp = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    no_such_user_resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert wrong_password_resp.status_code == no_such_user_resp.status_code
    assert wrong_password_resp.json() == no_such_user_resp.json()


def test_protected_endpoint_rejects_missing_token(client):
    resp = client.get("/applications")
    assert resp.status_code == 403


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get(
        "/applications", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


def test_protected_endpoint_accepts_valid_token(client, auth_headers):
    resp = client.get("/applications", headers=auth_headers)
    assert resp.status_code == 200


def test_refresh_issues_new_access_token(client, registered_user):
    login_resp = client.post("/auth/login", json=registered_user)
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_rejects_garbage_token(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client, registered_user):
    login_resp = client.post("/auth/login", json=registered_user)
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    # the same refresh token must no longer work after logout
    reuse_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_resp.status_code == 401
