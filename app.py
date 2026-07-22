
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
import os, uuid, json

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(BASE_DIR / "medrush.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    pack = db.Column(db.String(80), nullable=False)
    mrp = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    prescription_required = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(40), unique=True, nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    prescription_file = db.Column(db.String(255))
    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="Order received")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def seed_products():
    if Product.query.count():
        return
    products = [
        Product(name="Storvas CV 40 Tablet", category="Medicines", pack="Strip of 10 tablets", mrp=349.00, price=279.20, prescription_required=True),
        Product(name="Verquvo 5 mg Tablet", category="Medicines", pack="Strip of 14 tablets", mrp=1785.94, price=1428.75, prescription_required=True),
        Product(name="Ecosprin 150 Tablet", category="Medicines", pack="Strip of 14 tablets", mrp=5.29, price=4.23, prescription_required=True),
        Product(name="Hftril 50 Tablet", category="Medicines", pack="Strip of 14 tablets", mrp=444.68, price=355.74, prescription_required=True),
        Product(name="Ivabid 5 Tablet", category="Medicines", pack="Strip of 14 tablets", mrp=373.53, price=298.82, prescription_required=True),
        Product(name="Pregalin 75 Capsule", category="Medicines", pack="Strip of 15 capsules", mrp=380.43, price=304.34, prescription_required=True),
        Product(name="Daily Multivitamin", category="Nutrition", pack="Bottle of 60 tablets", mrp=699.00, price=559.20, prescription_required=False),
        Product(name="Whey Protein", category="Nutrition", pack="1 kg pack", mrp=2499.00, price=1999.20, prescription_required=False),
        Product(name="Gentle Face Wash", category="Beauty", pack="100 ml", mrp=399.00, price=319.20, prescription_required=False),
    ]
    db.session.add_all(products)
    db.session.commit()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/products")
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category and category != "All":
        query = query.filter_by(category=category)
    return jsonify([{
        "id": p.id, "name": p.name, "category": p.category, "pack": p.pack,
        "mrp": p.mrp, "price": p.price,
        "prescription_required": p.prescription_required
    } for p in query.order_by(Product.id).all()])

@app.route("/api/orders", methods=["POST"])
def create_order():
    try:
        cart = json.loads(request.form.get("items", "[]"))
    except Exception:
        return jsonify({"error": "Invalid cart data"}), 400
    if not cart:
        return jsonify({"error": "Your cart is empty"}), 400

    product_ids = [int(i["id"]) for i in cart]
    products = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()}
    needs_rx = any(products.get(int(i["id"])) and products[int(i["id"])].prescription_required for i in cart)

    file = request.files.get("prescription")
    prescription_name = None
    if needs_rx and (not file or not file.filename):
        return jsonify({"error": "Prescription copy is required for one or more medicines."}), 400
    if file and file.filename:
        if not allowed_file(file.filename):
            return jsonify({"error": "Upload PNG, JPG, WEBP or PDF only."}), 400
        ext = file.filename.rsplit(".", 1)[1].lower()
        prescription_name = f"{uuid.uuid4().hex}.{ext}"
        file.save(UPLOAD_DIR / secure_filename(prescription_name))

    subtotal = 0.0
    mrp_total = 0.0
    clean_items = []
    for item in cart:
        pid = int(item["id"])
        qty = max(1, int(item.get("qty", 1)))
        p = products.get(pid)
        if not p:
            continue
        subtotal += p.price * qty
        mrp_total += p.mrp * qty
        clean_items.append({"id": p.id, "name": p.name, "pack": p.pack, "qty": qty, "price": p.price, "mrp": p.mrp})

    discount = max(0, mrp_total - subtotal)
    delivery_fee = 0.0 if subtotal >= 499 else 49.0
    total = subtotal + delivery_fee
    order_no = "MR" + datetime.utcnow().strftime("%y%m%d") + uuid.uuid4().hex[:6].upper()

    order = Order(
        order_no=order_no,
        customer_name=request.form.get("name", "").strip(),
        phone=request.form.get("phone", "").strip(),
        email=request.form.get("email", "").strip(),
        address=request.form.get("address", "").strip(),
        city=request.form.get("city", "").strip(),
        state=request.form.get("state", "").strip(),
        pincode=request.form.get("pincode", "").strip(),
        payment_method=request.form.get("payment_method", "Cash on Delivery"),
        prescription_file=prescription_name,
        items_json=json.dumps(clean_items),
        subtotal=round(subtotal, 2),
        discount=round(discount, 2),
        delivery_fee=round(delivery_fee, 2),
        total=round(total, 2),
    )
    if not all([order.customer_name, order.phone, order.address, order.city, order.state, order.pincode]):
        return jsonify({"error": "Please complete all required delivery details."}), 400

    db.session.add(order)
    db.session.commit()
    return jsonify({
        "success": True,
        "order_no": order.order_no,
        "total": order.total,
        "status": order.status,
        "message": "A registered pharmacy will verify the prescription, stock and final bill before fulfilment."
    })

@app.route("/api/track/<order_no>")
def track(order_no):
    order = Order.query.filter_by(order_no=order_no.upper()).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({
        "order_no": order.order_no,
        "status": order.status,
        "total": order.total,
        "created_at": order.created_at.strftime("%d %b %Y, %I:%M %p")
    })

@app.route("/admin")
def admin():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin.html", orders=orders)

@app.route("/api/orders/<int:order_id>/status", methods=["POST"])
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json(silent=True) or {}
    order.status = data.get("status", order.status)
    db.session.commit()
    return jsonify({"success": True, "status": order.status})

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

with app.app_context():
    db.create_all()
    seed_products()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
