import io
from datetime import date

from PIL import Image

from app.auth import hash_password
from app.db import SessionLocal
from app.models import User


def image_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def draft(total=1057):
    return {
        "merchant_name": "Test Grocery",
        "purchased_at": date.today().isoformat(),
        "currency": "USD",
        "category": "Groceries",
        "subtotal_cents": 1057,
        "total_cents": total,
        "items": [
            {
                "raw_name": "MLK",
                "normalized_name": "Milk",
                "quantity": "1",
                "line_total_cents": 459,
            },
            {
                "raw_name": "BRD",
                "normalized_name": "Bread",
                "quantity": "2",
                "line_total_cents": 598,
            },
        ],
    }


def upload(client):
    result = client.post(
        "/api/receipts/upload", files={"file": ("receipt.png", image_bytes(), "image/png")}
    )
    assert result.status_code == 202
    return result.json()["receipt_id"]


def test_health_and_private_endpoints(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/me/receipts").status_code == 401
    assert client.get("/api/me/export").status_code == 401
    assert client.get("/api/chat/history").status_code == 401


def test_customer_cannot_create_sales(customer):
    result = customer.post(
        "/api/merchant/sales", json={"items": [{"product_id": "latte", "quantity": 1}]}
    )
    assert result.status_code == 403


def test_bad_login_and_cross_origin_mutation(customer):
    assert (
        customer.post(
            "/api/auth/login", json={"email": "customer@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        customer.post(
            "/api/auth/logout", headers={"origin": "https://unrelated.example"}
        ).status_code
        == 403
    )


def test_upload_review_confirm_and_spending(customer):
    receipt_id = upload(customer)
    assert customer.get(f"/api/receipts/{receipt_id}/status").json()["status"] == "NEEDS_REVIEW"
    assert customer.get("/api/me/spending").json()["total_cents"] == 0
    assert customer.patch(f"/api/receipts/{receipt_id}/draft", json=draft()).status_code == 200
    result = customer.post(f"/api/receipts/{receipt_id}/confirm", json={})
    assert result.status_code == 200
    assert result.json()["status"] == "READY"
    assert customer.get("/api/me/spending").json()["total_cents"] == 1057
    answer = customer.post("/api/chat", json={"message": "How much did I spend this month?"}).json()
    assert "$10.57" in answer["content"]
    assert answer["evidence"][0]["id"] == receipt_id


def test_mismatched_total_cannot_be_confirmed(customer):
    receipt_id = upload(customer)
    assert (
        customer.patch(f"/api/receipts/{receipt_id}/draft", json=draft(total=2000)).status_code
        == 200
    )
    assert customer.post(f"/api/receipts/{receipt_id}/confirm", json={}).status_code == 422
    assert customer.get("/api/me/spending").json()["total_cents"] == 0


def test_file_content_validation_and_duplicates(customer):
    result = customer.post(
        "/api/receipts/upload", files={"file": ("fake.png", b"not an image", "image/png")}
    )
    assert result.status_code == 422
    receipt_id = upload(customer)
    repeated = customer.post(
        "/api/receipts/upload", files={"file": ("again.png", image_bytes(), "image/png")}
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"]["receipt_id"] == receipt_id


def test_other_account_cannot_read_edit_or_delete_receipt_or_file(customer):
    receipt_id = upload(customer)
    customer.post(
        "/api/auth/register",
        json={
            "name": "Other Customer",
            "email": "other@example.com",
            "password": "another-password-2026",
        },
    )
    for path in [
        f"/api/me/receipts/{receipt_id}",
        f"/api/me/receipts/{receipt_id}/file",
        f"/api/receipts/{receipt_id}/status",
    ]:
        assert customer.get(path).status_code == 404
    assert customer.patch(f"/api/receipts/{receipt_id}/draft", json=draft()).status_code == 404
    assert customer.delete(f"/api/me/receipts/{receipt_id}").status_code == 404
    assert customer.get("/api/me/receipts").json()["total"] == 0


def test_qr_sale_claim_and_replay_protection(client):
    with SessionLocal() as db:
        db.add(
            User(
                name="Test Cafe",
                email="merchant@example.com",
                password_hash=hash_password("merchant-password"),
                role="merchant",
            )
        )
        db.commit()
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "merchant@example.com", "password": "merchant-password"},
        ).status_code
        == 200
    )
    sale = client.post(
        "/api/merchant/sales", json={"items": [{"product_id": "latte", "quantity": 2}]}
    ).json()
    assert sale["total_cents"] == 1188
    completed = client.post(f"/api/merchant/sales/{sale['id']}/complete").json()
    preview = client.get(f"/api/public/receipts/{completed['token']}").json()
    assert "items" not in preview
    assert preview["total_cents"] == 1188
    client.post(
        "/api/auth/register",
        json={"name": "Buyer", "email": "buyer@example.com", "password": "buyer-password-2026"},
    )
    claimed = client.post("/api/receipts/claim", json={"token": completed["token"]})
    assert claimed.status_code == 201
    assert claimed.json()["total_cents"] == 1188
    assert client.post("/api/receipts/claim", json={"token": completed["token"]}).status_code == 409
