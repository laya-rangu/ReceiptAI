"""Use independent, versioned receipt files and golden answers against the API.

No provider calls. The clock is frozen; tests never seed or change developer data.
"""

import copy
import json
from datetime import date as RealDate
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import analytics, main, receipts
from app.auth import hash_password
from app.db import SessionLocal
from app.ingestion import inspect_file
from app.models import Receipt, User
from app.receipts import apply_draft, validate_finances
from app.schemas import ReceiptDraft
from evaluations.fixtures.build import materialize_boundaries
from evaluations.fixtures.verify import verify

FIXTURES = Path(__file__).resolve().parents[2] / "evaluations" / "fixtures"
ROOT = FIXTURES / "v1"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
RECORDS = json.loads((ROOT / "expected/receipts.json").read_text(encoding="utf-8"))["records"]
SCENARIOS = json.loads((FIXTURES / "scenarios.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def freeze_reference_date(monkeypatch):
    class ReferenceDate(RealDate):
        @classmethod
        def today(cls):
            return cls(2026, 9, 28)

    for module in (analytics, main, receipts):
        monkeypatch.setattr(module, "date", ReferenceDate)


def test_fixture_integrity_and_independent_golden_answers():
    assert verify()["status"] == "PASS"


@pytest.mark.parametrize("document", MANIFEST["documents"], ids=lambda doc: doc["id"])
def test_fixture_upload_policy(document):
    data = (ROOT / document["path"]).read_bytes()
    if document["expected"]["upload"] == "reject":
        with pytest.raises(ValueError):
            inspect_file(data)
    else:
        content_type, _ = inspect_file(data)
        assert content_type == document["content_type"]


@pytest.mark.parametrize("case", SCENARIOS["financial_cases"], ids=lambda case: case["record_id"])
def test_fixture_financial_validation(case):
    draft = ReceiptDraft.model_validate(copy.deepcopy(RECORDS[case["record_id"]]))
    errors = validate_finances(draft)
    if case["expected_errors"]:
        assert errors
        assert draft.total_cents == case["reported_total_cents"]
    else:
        assert errors == []
        assert draft.total_cents == case["expected_total_cents"]


@pytest.mark.parametrize("case", SCENARIOS["schema_cases"], ids=lambda case: case["id"])
def test_fixture_invalid_values(case):
    raw = copy.deepcopy(RECORDS[case["base"]])
    raw.update(case.get("set", {}))
    for key in case.get("remove", []):
        raw.pop(key)
    if "set_item" in case:
        item_change = case["set_item"]
        raw["items"][item_change["index"]].update(
            {key: value for key, value in item_change.items() if key != "index"}
        )
    if case["expected"] == "reject_schema":
        with pytest.raises(ValidationError):
            ReceiptDraft.model_validate(raw)
    else:
        assert validate_finances(ReceiptDraft.model_validate(raw))


def test_exact_byte_and_pixel_boundaries(tmp_path):
    materialize_boundaries(tmp_path)
    for case in SCENARIOS["large_file_recipes"]:
        data = (tmp_path / f"{case['id']}.png").read_bytes()
        if "bytes" in case:
            assert len(data) == case["bytes"]
        if case["expected_upload"] == "reject":
            with pytest.raises(ValueError):
                inspect_file(data)
        else:
            assert inspect_file(data)[0] == "image/png"


@pytest.mark.parametrize("document_id", ["P1", "P1_JPG", "P1_PDF", "P1_PDF5"])
def test_manual_review_with_actual_receipt_files(customer, document_id):
    doc = next(doc for doc in MANIFEST["documents"] if doc["id"] == document_id)
    response = customer.post(
        "/api/receipts/upload",
        files={
            "file": (Path(doc["path"]).name, (ROOT / doc["path"]).read_bytes(), doc["content_type"])
        },
    )
    assert response.status_code == 202
    receipt_id = response.json()["receipt_id"]
    assert customer.get(f"/api/receipts/{receipt_id}/status").json()["status"] == "NEEDS_REVIEW"
    assert (
        customer.patch(f"/api/receipts/{receipt_id}/draft", json=RECORDS["P1"]).status_code == 200
    )
    result = customer.post(f"/api/receipts/{receipt_id}/confirm", json={})
    assert result.status_code == 200
    assert result.json()["total_cents"] == 1057
    assert (
        customer.get(f"/api/me/receipts/{receipt_id}/file").content
        == (ROOT / doc["path"]).read_bytes()
    )


def test_qr_and_photo_share_exact_golden_total(client):
    with SessionLocal() as db:
        db.add(
            User(
                name="Test Cafe",
                email="fixture-merchant@example.com",
                password_hash=hash_password("fixture-password"),
                role="merchant",
            )
        )
        db.commit()
    client.post(
        "/api/auth/login",
        json={"email": "fixture-merchant@example.com", "password": "fixture-password"},
    )
    sale = client.post("/api/merchant/sales", json=SCENARIOS["sale"]["request"])
    assert sale.status_code == 201
    assert sale.json()["subtotal_cents"] == 1275
    assert sale.json()["tax_cents"] == 102
    assert sale.json()["total_cents"] == 1377
    token = client.post(f"/api/merchant/sales/{sale.json()['id']}/complete").json()["token"]
    client.post(
        "/api/auth/register",
        json={
            "name": "Fixture A",
            "email": "fixture-a@example.com",
            "password": "fixture-password-A",
        },
    )
    qr = client.post("/api/receipts/claim", json={"token": token})
    assert qr.status_code == 201
    uploaded = client.post(
        "/api/receipts/upload",
        files={"file": ("P1.png", (ROOT / "clear/P1.png").read_bytes(), "image/png")},
    )
    assert uploaded.status_code == 202
    receipt_id = uploaded.json()["receipt_id"]
    client.patch(f"/api/receipts/{receipt_id}/draft", json=RECORDS["BAD1"])
    assert client.post(f"/api/receipts/{receipt_id}/confirm", json={}).status_code == 422
    assert client.get("/api/me/spending").json()["total_cents"] == 1377
    assert client.patch(f"/api/receipts/{receipt_id}/draft", json=RECORDS["P1"]).status_code == 200
    assert client.post(f"/api/receipts/{receipt_id}/confirm", json={}).status_code == 200
    assert client.post(f"/api/receipts/{receipt_id}/confirm", json={}).status_code == 200
    summary = client.get("/api/me/spending").json()
    assert (summary["total_cents"], summary["receipt_count"]) == (2434, 2)
    answer = client.post("/api/chat", json={"message": "How much did I spend this month?"}).json()
    assert "$24.34" in answer["content"]
    assert {e["id"] for e in answer["evidence"]} == {qr.json()["id"], receipt_id}


def test_owned_month_and_date_boundary_summaries(customer):
    user_id = customer.get("/api/auth/me").json()["id"]
    with SessionLocal() as db:
        for spec in SCENARIOS["date_boundaries"]["records"]:
            data = copy.deepcopy(RECORDS["P1"])
            data.update(
                purchased_at=spec["date"],
                subtotal_cents=spec["total_cents"],
                total_cents=spec["total_cents"],
            )
            data["items"] = [{**data["items"][0], "line_total_cents": spec["total_cents"]}]
            receipt = Receipt(user_id=user_id, source_type="PHOTO", status="READY")
            apply_draft(receipt, ReceiptDraft.model_validate(data))
            db.add(receipt)
        db.commit()
    for name in ["this_month", "last_month", "last_30_days"]:
        spec = SCENARIOS["date_boundaries"][name]
        summary = customer.get(
            "/api/me/spending", params={"start": spec["start"], "end": spec["end"]}
        ).json()
        assert summary["total_cents"] == spec["total_cents"]
        assert summary["receipt_count"] == len(spec["ids"])
