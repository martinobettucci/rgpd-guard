# @spec docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-011 | docs/DAT.md#api | docs/DAT.md#securite
# @verifies docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-011 | docs/DAT.md#securite
"""API : refus directs sans droits (en contournant toute interface), sessions, politiques, journal."""

from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import TOKEN, load_fixture, make_iban


def test_health_is_public(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["profile"] == "rapide"


def test_hooks_refused_without_or_with_wrong_token(client: TestClient) -> None:
    payload = load_fixture("user_prompt_submit")
    assert client.post("/v1/hooks/user-prompt-submit", json=payload).status_code == 401
    bad = {"X-RGPD-Guard-Token": "faux"}
    assert client.post("/v1/hooks/user-prompt-submit", json=payload, headers=bad).status_code == 401


def test_hook_with_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/v1/hooks/user-prompt-submit", json=load_fixture("user_prompt_submit"), headers=auth_headers
    )
    assert response.status_code == 200 and response.json()["decision"] == "block"
    assert client.post("/v1/hooks/inconnu", json={}, headers=auth_headers).status_code == 404


def test_foreign_host_refused(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/health", headers={"Host": "attaquant.example"})
    assert response.status_code == 400


def test_foreign_origin_refused_on_mutation(client: TestClient) -> None:
    response = client.post("/v1/auth/session", json={"token": TOKEN}, headers={"Origin": "http://evil.example"})
    assert response.status_code == 403


def test_non_json_body_refused(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/session", content="token=x", headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 415


def test_admin_routes_require_session(client: TestClient, auth_headers: dict[str, str]) -> None:
    for path in ("/v1/audit/events", "/v1/audit/stats", "/v1/policies", "/v1/engines"):
        assert client.get(path).status_code == 401
        # Le jeton des hooks n'ouvre pas les routes d'administration : il faut une session.
        assert client.get(path, headers=auth_headers).status_code == 401


def test_login_logout(client: TestClient) -> None:
    assert client.post("/v1/auth/session", json={"token": "faux"}).status_code == 401
    response = client.post("/v1/auth/session", json={"token": TOKEN})
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Max-Age" not in cookie
    assert client.get("/v1/auth/session").json() == {"authenticated": True}
    client.delete("/v1/auth/session")
    assert client.get("/v1/audit/stats").status_code == 401


def test_analyze_summary_has_no_value(client: TestClient, auth_headers: dict[str, str]) -> None:
    iban = make_iban(9)
    body = client.post("/v1/analyze", json={"text": f"IBAN {iban}", "summary": True}, headers=auth_headers).json()
    assert body["counts"] == {"IBAN": 1} and iban not in str(body)


def test_analyze_detail_for_sandbox(logged_client: TestClient) -> None:
    body = logged_client.post("/v1/analyze", json={"text": f"IBAN {make_iban(9)}", "profile": "rapide"}).json()
    assert body["decision"] == "block" and body["findings"][0]["label"] == "IBAN"
    assert body["pseudonymized"].startswith("IBAN ⟦IBAN_")


def test_policy_update_validated_server_side(logged_client: TestClient) -> None:
    current = logged_client.get("/v1/policies").json()
    assert current["source"] == "default"
    policy = current["policy"]
    policy["labels"]["IBAN"]["prompt"] = "warn"
    assert logged_client.put("/v1/policies", json=policy).status_code == 200
    body = logged_client.post("/v1/analyze", json={"text": f"IBAN {make_iban(9)}"}).json()
    assert body["decision"] == "warn"
    policy["labels"]["IBAN"]["prompt"] = "interdit"
    invalid = logged_client.put("/v1/policies", json=policy)
    assert invalid.status_code == 422
    assert invalid.json()["erreurs"][0]["message"].startswith("valeur non autorisée (attendu : ")
    policy["labels"]["IBAN"]["prompt"] = "warn"
    policy["allowlist"]["patterns"] = ["(non fermée"]
    bad_regex = logged_client.put("/v1/policies", json=policy).json()["erreurs"]
    assert bad_regex == [
        {
            "champ": "allowlist.patterns",
            "message": "expression régulière invalide « (non fermée » (erreur à la position 0)",
        }
    ]
    reset = logged_client.post("/v1/policies/reset").json()
    assert reset["source"] == "default" and reset["policy"]["labels"]["IBAN"]["prompt"] == "block"


def test_audit_listing_and_filters(logged_client: TestClient, auth_headers: dict[str, str]) -> None:
    logged_client.post("/v1/hooks/user-prompt-submit", json=load_fixture("user_prompt_submit"), headers=auth_headers)
    data = logged_client.get("/v1/audit/events", params={"label": "IBAN"}).json()
    assert data["total"] == 1 and data["events"][0]["entities"][0]["preview"].startswith("F")
    assert logged_client.get("/v1/audit/events", params={"decision": "allow"}).json()["total"] == 0
    assert logged_client.get("/v1/audit/stats").json()["by_label"] == {"IBAN": 1}


def test_engines_status(logged_client: TestClient) -> None:
    body = logged_client.get("/v1/engines").json()
    names = {c["name"] for c in body["components"]}
    assert {"rules", "secrets"} <= names and body["profiles"]["rapide"]["missing"] == []
    assert body["profiles"]["equilibre"]["classifiers_prompt"] == ["laya"]
    assert body["labels"]["IBAN"] == "IBAN" and body["categories"]["SANTE"] == "santé"


def test_scan_returns_counts_only(client: TestClient, auth_headers: dict[str, str], settings) -> None:  # type: ignore[no-untyped-def]
    iban = make_iban(11)
    target = settings.workspace_root / "factures.txt"
    target.write_text(f"Virement sur {iban}\n", encoding="utf-8")
    body = client.post("/v1/scan", json={"path": str(target)}, headers=auth_headers).json()
    assert body["status"] == "analysed" and body["counts"] == {"IBAN": 1} and iban not in str(body)
    outside = client.post("/v1/scan", json={"path": "/etc/hostname"}, headers=auth_headers).json()
    assert outside["status"] == "out_of_reach"
    assert client.post("/v1/scan", json={"path": str(target)}).status_code == 401
