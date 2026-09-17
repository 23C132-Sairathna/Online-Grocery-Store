import os
import tempfile
import importlib
import pytest


def make_app():
    os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")
    import app
    app = importlib.reload(app)
    app.init_db()
    app.app.config.update(TESTING=True)
    return app.app


@pytest.fixture()
def client():
    return make_app().test_client()


def sign_in(client):
    response = client.post("/api/auth/signup", json={"name": "Asha", "email": "asha@example.com", "password": "secret123", "address": "12 Main Street"})
    assert response.status_code == 201


def test_homepage_contains_catalog(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"FreshCart" in response.data
    assert b"India Gate Basmati Rice" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_order_total_is_calculated(client):
    sign_in(client)
    response = client.post("/api/orders", json={"customer": "Asha", "address": "12 Main Street", "payment_method": "demo_card", "items": [{"product_id": "apple", "quantity": 2}]})
    assert response.status_code == 201
    assert response.json["total"] == 358.0


def test_order_requires_items(client):
    sign_in(client)
    response = client.post("/api/orders", json={"customer": "Asha", "address": "12 Main Street", "items": []})
    assert response.status_code == 400


def test_order_reserves_stock_and_can_be_retrieved(client):
    sign_in(client)
    response = client.post("/api/orders", json={"customer": "Asha", "address": "12 Main Street", "payment_method": "demo_card", "items": [{"product_id": "apple", "quantity": 2}]})
    assert response.status_code == 201

    order = client.get(f"/api/orders/{response.json['order_id']}")
    assert order.status_code == 200
    assert order.json["order"]["items"][0]["name"] == "Himachali Apples"

    products = client.get("/api/products?search=apple")
    assert products.json["products"][0]["stock"] == 22


def test_order_rejects_more_than_available_stock(client):
    sign_in(client)
    response = client.post("/api/orders", json={"customer": "Asha", "address": "12 Main Street", "payment_method": "demo_card", "items": [{"product_id": "basmati", "quantity": 99}]})
    assert response.status_code == 409


def test_signup_profile_and_demo_payment(client):
    signup = client.post("/api/auth/signup", json={"name": "Asha", "email": "asha@example.com", "password": "secret123", "address": "12 Main Street"})
    assert signup.status_code == 201
    assert signup.json["user"]["address"] == "12 Main Street"

    profile = client.put("/api/profile", json={"name": "Asha Rao", "address": "42 Market Road"})
    assert profile.status_code == 200
    assert profile.json["user"]["name"] == "Asha Rao"

    order = client.post("/api/orders", json={"items": [{"product_id": "banana", "quantity": 1}], "payment_method": "demo_card"})
    assert order.status_code == 201


def test_checkout_requires_login_and_payment_method(client):
    response = client.post("/api/orders", json={"items": [{"product_id": "apple", "quantity": 1}]})
    assert response.status_code == 401


def test_orders_and_qr_are_available_to_signed_in_user(client):
    sign_in(client)
    order = client.post("/api/orders", json={"items": [{"product_id": "banana", "quantity": 1}], "payment_method": "demo_card"})
    assert order.status_code == 201
    history = client.get("/api/orders")
    assert history.status_code == 200
    assert history.json["orders"][0]["status"] == "Order confirmed"
    qr = client.get("/api/payment/qr?reference=FC123&amount=89.00")
    assert qr.status_code == 200
    assert qr.mimetype == "image/png"


def test_order_history_requires_login_and_returns_user_orders(client):
    assert client.get("/api/orders").status_code == 401
    sign_in(client)
    created = client.post("/api/orders", json={"items": [{"product_id": "banana", "quantity": 1}], "payment_method": "demo_card"})
    assert created.status_code == 201
    history = client.get("/api/orders")
    assert history.status_code == 200
    assert history.json["orders"][0]["id"] == created.json["order_id"]
