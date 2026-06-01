import logging

from fastapi.testclient import TestClient


def test_app_startup_logs_configured_flow_mode(monkeypatch, caplog):
    monkeypatch.setenv("ONBOARDFLOW_FLOW_MODE", "deterministic")

    from onboardflow.config.settings import get_settings

    get_settings.cache_clear()
    from onboardflow.api.main import create_app

    caplog.set_level(logging.INFO)
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "onboardflow_backend_started flow_mode=deterministic" in messages


def test_generate_and_get_run_returns_frontend_compatible_plan(client, employee_payload):
    start_response = client.post("/api/onboarding/generate", json=employee_payload)
    assert start_response.status_code == 200
    start_body = start_response.json()
    assert start_body["status"] == "running"
    assert start_body["runId"].startswith("run_")

    status_response = client.get(f"/api/onboarding/runs/{start_body['runId']}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "done"
    assert body["result"]["employeeProfile"]["fullName"] == "Ana Silva"
    assert body["result"]["status"] == "ready_for_review"
    assert body["result"]["communications"][0]["draft"] is True
    assert "Plano de Onboarding" in body["markdown"]
    assert any(action["actionType"] == "specialist_task_completed" for action in body["agentActivity"])


def test_generate_logs_deterministic_agent_operations(client, employee_payload, caplog):
    caplog.set_level(logging.INFO)

    response = client.post("/api/onboarding/generate", json=employee_payload)
    run_id = response.json()["runId"]

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert f"onboarding_generation_started run_id={run_id} flow_mode=deterministic" in messages
    assert (
        "agent_operation_started flow_mode=deterministic "
        f"run_id={run_id} task_id=generate_document_checklist agent=Compliance"
    ) in messages
    assert (
        "agent_operation_completed flow_mode=deterministic "
        f"run_id={run_id} task_id=generate_document_checklist agent=Compliance status=done"
    ) in messages
    assert (
        "agent_operation_started flow_mode=deterministic "
        f"run_id={run_id} task_id=draft_stakeholder_messages agent=Communication"
    ) in messages
    assert f"onboarding_generation_completed run_id={run_id} status=done" in messages


def test_invalid_start_date_returns_error_run(client, employee_payload):
    payload = {**employee_payload, "startDate": "2025-01-01"}
    start_body = client.post("/api/onboarding/generate", json=payload).json()

    status_response = client.get(f"/api/onboarding/runs/{start_body['runId']}")
    body = status_response.json()

    assert body["status"] == "error"
    assert body["errorMessage"] == "Entrada invalida para execucao dos agentes."
    assert body["validationResult"]["status"] == "unusable"


def test_refine_adds_revision_and_preserves_schema(client, employee_payload):
    run_id = client.post("/api/onboarding/generate", json=employee_payload).json()["runId"]

    response = client.post(
        f"/api/onboarding/runs/{run_id}/refine",
        json={"instruction": "Revisar prazos da agenda inicial."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["revisionNumber"] == 2
    assert body["result"]["status"] == "draft"
    assert "Ajustes solicitados pelo RH foram incorporados" in body["result"]["executiveSummary"]
    assert any(
        item["title"] == "Revisao da agenda inicial solicitada"
        for item in body["result"]["initialAgenda"]
    )
    assert any(
        item["title"] == "Ajuste solicitado pelo RH"
        for item in body["result"]["pendingActions"]
    )


def test_refine_logs_deterministic_agent_operations(client, employee_payload, caplog):
    run_id = client.post("/api/onboarding/generate", json=employee_payload).json()["runId"]
    caplog.clear()
    caplog.set_level(logging.INFO)

    response = client.post(
        f"/api/onboarding/runs/{run_id}/refine",
        json={"instruction": "Revisar prazos da agenda inicial."},
    )

    assert response.status_code == 200
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert f"onboarding_refinement_started run_id={run_id} flow_mode=deterministic" in messages
    assert (
        "agent_operation_started flow_mode=deterministic "
        f"run_id={run_id} task_id=refine_plan_revision agent=Refinement"
    ) in messages
    assert (
        "agent_operation_completed flow_mode=deterministic "
        f"run_id={run_id} task_id=refine_plan_revision agent=Refinement status=done"
    ) in messages
    assert f"onboarding_refinement_completed run_id={run_id} revision_number=2" in messages
