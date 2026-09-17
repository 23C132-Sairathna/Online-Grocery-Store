import os
import sqlite3
from io import BytesIO
from functools import wraps
import qrcode
from flask import Flask, jsonify, render_template, request, session, send_file
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
DATABASE = os.getenv("DATABASE_PATH", "freshcart.db")
app.secret_key = os.getenv("SECRET_KEY", "freshcart-development-key")

PRODUCTS = [
    ("basmati", "India Gate Basmati Rice", "Premium long-grain rice, 5 kg", "Pantry", 649.00, "🍚", 18),
    ("atta", "Aashirvaad Whole Wheat Atta", "Everyday chakki atta, 5 kg", "Pantry", 289.00, "🌾", 22),
    ("dal", "Tata Sampann Toor Dal", "Unpolished pigeon peas, 1 kg", "Pantry", 189.00, "🫘", 20),
    ("masala", "MDH Garam Masala", "Classic Indian spice blend, 100 g", "Pantry", 78.00, "🌶️", 25),
    ("chai", "Tata Tea Gold", "Aromatic tea leaves, 500 g", "Pantry", 275.00, "🍵", 16),
    ("oil", "Fortune Sunflower Oil", "Light cooking oil, 1 litre", "Pantry", 145.00, "🫗", 19),
    ("mango", "Alphonso Mangoes", "Seasonal Ratnagiri mangoes", "Fruits", 399.00, "🥭", 14),
    ("banana", "Yelakki Bananas", "Naturally sweet, 1 dozen", "Fruits", 89.00, "🍌", 30),
    ("apple", "Himachali Apples", "Crisp Shimla apples, 1 kg", "Fruits", 179.00, "🍎", 24),
    ("pomegranate", "Kashmiri Pomegranates", "Ruby-red arils, 1 kg", "Fruits", 249.00, "🍒", 17),
    ("tomato", "Desi Vine Tomatoes", "Fresh local tomatoes, 1 kg", "Vegetables", 59.00, "🍅", 28),
    ("potato", "Fresh Potatoes", "Farm-picked potatoes, 2 kg", "Vegetables", 79.00, "🥔", 32),
    ("onion", "Red Onions", "Everyday Indian onions, 1 kg", "Vegetables", 69.00, "🧅", 30),
    ("paneer", "Amul Fresh Paneer", "Soft malai paneer, 200 g", "Dairy", 95.00, "🧀", 15),
    ("curd", "Amul Masti Dahi", "Thick set curd, 400 g", "Dairy", 48.00, "🥣", 18),
    ("milk", "Amul Taaza Milk", "Fresh toned milk, 1 litre", "Dairy", 68.00, "🥛", 20),
    ("paratha", "Haldiram's Aloo Paratha", "Frozen ready-to-cook pack", "Frozen", 165.00, "🫓", 12),
    ("idli", "MTR Rava Idli Mix", "Instant breakfast mix, 200 g", "Breakfast", 92.00, "🍘", 14),
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
            category TEXT NOT NULL, price REAL NOT NULL, emoji TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT NOT NULL,
            address TEXT NOT NULL, total REAL NOT NULL, user_id INTEGER,
            payment_method TEXT NOT NULL DEFAULT 'demo_card',
            payment_status TEXT NOT NULL DEFAULT 'paid',
            status TEXT NOT NULL DEFAULT 'Order confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            address TEXT NOT NULL DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            product_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL
        )""")
        db.executemany(
            "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            PRODUCTS,
        )
        product_ids = tuple(product[0] for product in PRODUCTS)
        placeholders = ",".join("?" for _ in product_ids)
        db.execute(f"DELETE FROM products WHERE id NOT IN ({placeholders})", product_ids)
        for product in PRODUCTS:
            db.execute(
                "UPDATE products SET name = ?, description = ?, category = ?, price = ?, emoji = ? WHERE id = ?",
                (product[1], product[2], product[3], product[4], product[5], product[0]),
            )
        columns = {row[1] for row in db.execute("PRAGMA table_info(orders)")}
        if "user_id" not in columns:
            db.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
        if "payment_method" not in columns:
            db.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'demo_card'")
        if "payment_status" not in columns:
            db.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'paid'")
        if "status" not in columns:
            db.execute("ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'Order confirmed'")


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        user = db.execute("SELECT id, name, email, address FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(user) if user else None


def login_required(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return jsonify(error="Please sign in before continuing."), 401
        return route(*args, **kwargs)
    return wrapped


@app.get("/")
def index():
    with get_db() as db:
        products = [tuple(row) for row in db.execute(
            "SELECT id, name, description, category, price, emoji, stock FROM products ORDER BY name"
        )]
    return render_template("index.html", products=products, user=current_user())


@app.post("/api/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    address = str(payload.get("address", "")).strip()
    if not name or not email or len(password) < 6:
        return jsonify(error="Name, email, and a password of at least 6 characters are required."), 400
    try:
        with get_db() as db:
            cursor = db.execute("INSERT INTO users (name, email, password_hash, address) VALUES (?, ?, ?, ?)", (name, email, generate_password_hash(password), address))
            session["user_id"] = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify(error="An account with that email already exists."), 409
    return jsonify(user=current_user()), 201


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Email or password is incorrect."), 401
    session["user_id"] = user["id"]
    return jsonify(user=current_user())


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(message="Signed out")


@app.get("/api/profile")
@login_required
def profile():
    return jsonify(user=current_user())


@app.put("/api/profile")
@login_required
def update_profile():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    address = str(payload.get("address", "")).strip()
    if not name or not address:
        return jsonify(error="Name and delivery address are required."), 400
    with get_db() as db:
        db.execute("UPDATE users SET name = ?, address = ? WHERE id = ?", (name, address, session["user_id"]))
    return jsonify(user=current_user())


@app.get("/api/orders")
@login_required
def list_orders():
    with get_db() as db:
        orders = db.execute(
            "SELECT id, customer, address, total, payment_method, payment_status, status, created_at "
            "FROM orders WHERE user_id = ? ORDER BY created_at DESC, id DESC",
            (session["user_id"],),
        ).fetchall()
    return jsonify(orders=[dict(order) for order in orders])


@app.get("/api/payment/qr")
@login_required
def payment_qr():
    reference = request.args.get("reference", "FRESHCART-DEMO")
    amount = request.args.get("amount", "0")
    qr = qrcode.make(f"upi://pay?pa=freshcart@demo&pn=FreshCart&am={amount}&cu=INR&tn={reference}")
    image = BytesIO()
    qr.save(image, format="PNG")
    image.seek(0)
    return send_file(image, mimetype="image/png", max_age=0)


@app.get("/api/products")
def list_products():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip().lower()
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, category, price, emoji, stock FROM products "
            "WHERE (? = '' OR category = ?) AND (lower(name) LIKE ? OR lower(description) LIKE ?) "
            "ORDER BY name",
            (category, category, f"%{search}%", f"%{search}%"),
        ).fetchall()
    return jsonify(products=[dict(row) for row in rows])


@app.get("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return jsonify(status="ok", service="freshcart", database="ok")
    except sqlite3.Error:
        return jsonify(status="degraded", service="freshcart", database="error"), 503


@app.post("/api/orders")
def create_order():
    user = current_user()
    if user is None:
        return jsonify(error="Please sign in before checkout."), 401
    payload = request.get_json(silent=True) or {}
    customer = str(payload.get("customer", user["name"])).strip()
    address = str(payload.get("address", user["address"])).strip()
    payment_method = str(payload.get("payment_method", "")).strip()
    items = payload.get("items", [])
    if not customer or not address or not payment_method or not isinstance(items, list) or not items:
        return jsonify(error="Name, address, payment method, and at least one item are required."), 400
    if payment_method not in {"demo_card", "demo_cash"}:
        return jsonify(error="Choose a supported demo payment method."), 400
    requested = {}
    for item in items:
        if not isinstance(item, dict):
            return jsonify(error="One or more cart items are invalid."), 400
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if not isinstance(product_id, str) or not isinstance(quantity, int) or quantity < 1 or quantity > 99:
            return jsonify(error="One or more cart items are invalid."), 400
        requested[product_id] = requested.get(product_id, 0) + quantity

    with get_db() as db:
        placeholders = ",".join("?" for _ in requested)
        rows = db.execute(f"SELECT id, price, stock FROM products WHERE id IN ({placeholders})", tuple(requested)).fetchall()
        products = {row["id"]: row for row in rows}
        if len(products) != len(requested):
            return jsonify(error="One or more products are unavailable."), 400
        for product_id, quantity in requested.items():
            if quantity > products[product_id]["stock"]:
                return jsonify(error=f"Not enough stock for {product_id}."), 409
        total = round(sum(products[product_id]["price"] * quantity for product_id, quantity in requested.items()), 2)
        cursor = db.execute("INSERT INTO orders (customer, address, total, user_id, payment_method, payment_status, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (customer, address, total, session["user_id"], payment_method, "paid", "Order confirmed"))
        for product_id, quantity in requested.items():
            product = products[product_id]
            db.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)", (cursor.lastrowid, product_id, quantity, product["price"]))
            db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
    return jsonify(message="Order placed", order_id=cursor.lastrowid, total=round(total, 2)), 201


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    with get_db() as db:
        order = db.execute("SELECT id, customer, address, total, payment_method, payment_status, status, created_at FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None:
            return jsonify(error="Order not found."), 404
        items = db.execute(
            "SELECT order_items.product_id, order_items.quantity, order_items.unit_price, products.name "
            "FROM order_items JOIN products ON products.id = order_items.product_id WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    return jsonify(order={**dict(order), "items": [dict(item) for item in items]})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
