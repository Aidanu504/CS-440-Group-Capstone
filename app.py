from neo4j_files.payments import record_payment
import os
from dotenv import load_dotenv    
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from bson.json_util import dumps, loads

load_dotenv()  

from sqlite_files import db, Product, Customer, Supplier
from mongo_files import insert_order, find_orders_by_customer, find_order_by_id

from redis_files import (
    cache_product, get_cached_product, 
    cache_product_list, get_cached_product_list,
    invalidate_product_cache, increment_view_counter,
    get_popular_products
)

from neo4j_files import (
    payments,
    record_order_metrics, record_inventory_change,
    get_sales_by_timeframe, get_product_sales_history
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def convert_mongo_document(doc):
    if isinstance(doc, list):
        return [convert_mongo_document(item) for item in doc]
    if not isinstance(doc, dict):
        return doc
    result = {}
    for key, value in doc.items():
        if key == '_id' and hasattr(value, '__str__'):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = convert_mongo_document(value)
        elif isinstance(value, list):
            result[key] = [convert_mongo_document(item) for item in value]
        else:
            result[key] = value
    return result

@app.route("/")
def index():
    return render_template("index.html")

#Get all products Targets: SQLite
@app.route("/products", methods=["GET"])
def list_products():
    cached_products = get_cached_product_list()
    if cached_products:
        return jsonify(cached_products)

    prods = Product.query.all()
    products = [{"id": p.id, "name": p.name, "price": p.price, "stock": p.stock} for p in prods]
    cache_product_list(products)
    return jsonify(products)

#Get product by ID Targets: Redis and SQLite
@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    views = increment_view_counter(product_id)
    cached_product = get_cached_product(product_id)
    if cached_product:
        return jsonify(cached_product)
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    product_data = {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "stock": product.stock,
        "views": views
    }
    cache_product(product_id, product_data)
    return jsonify(product_data)

#add new product targets: SQLite
@app.route("/products", methods=["POST"])
def add_product():
    data = request.json
    p = Product(name=data["name"], price=data["price"], stock=data.get("stock", 0))
    db.session.add(p)
    db.session.commit()
    invalidate_product_cache()
    return jsonify({"id": p.id}), 201

#update product targets: SQLite and Neo4j
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    data = request.json
    old_stock = product.stock
    if "name" in data:
        product.name = data["name"]
    if "price" in data:
        product.price = data["price"]
    if "stock" in data:
        product.stock = data["stock"]
    db.session.commit()
    if "stock" in data and old_stock != product.stock:
        record_inventory_change(product_id, old_stock, product.stock)
    invalidate_product_cache(product_id)
    invalidate_product_cache()
    return jsonify({"id": product.id, "updated": True})

#create order Targets: Mongodb ad SQlite and Mongodb and Neo4j
@app.route("/orders", methods=["POST"])
def create_order():
    order_data = request.json
    if not order_data.get("customer_id"):
        return jsonify({"error": "Customer ID is required"}), 400
    if not order_data.get("items") or not isinstance(order_data["items"], list):
        return jsonify({"error": "Order items are required"}), 400

    total_amount = 0
    for item in order_data["items"]:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({"error": f"Product {product_id} not found"}), 404
        if product.stock < quantity:
            return jsonify({"error": f"Insufficient stock for product {product_id}"}), 400
        item["price"] = product.price
        total_amount += product.price * quantity
        old_stock = product.stock
        product.stock -= quantity
        record_inventory_change(product_id, old_stock, product.stock)

    item["name"] = product.name
    order_data["total_amount"] = total_amount
    order_data["date"] = datetime.utcnow().isoformat()

    order_id = insert_order(order_data)
    record_order_metrics(order_data)
    db.session.commit()
    invalidate_product_cache()
    return jsonify({"order_id": str(order_id), "total_amount": total_amount}), 201

#get all orders for a customer Targets: Mongodb and Sqlite 
@app.route("/orders/<int:customer_id>", methods=["GET"])
def get_orders(customer_id):
    orders = find_orders_by_customer(customer_id)
    for order in orders:
        for item in order.get("items", []):
            prod = db.session.get(Product, item["product_id"])
            item["name"] = prod.name if prod else "Unknown"
    return jsonify(convert_mongo_document(orders))

#record a payment for an order targets: Neo4j
@app.route("/orders/<order_id>/pay", methods=["POST"])
def make_payment(order_id):
    data = request.json
    amount = data.get("amount")
    method = data.get("method", "Cash")

    if amount is None or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    order = find_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    total_due = order.get("total_amount", 0)
    status = "Paid" if amount >= total_due else "Pending"

    record_payment(order_id, method, amount, status)
    return jsonify({"message": "Payment recorded"})

#retrieve latest payment information Targets: Neo4j
@app.route("/orders/<order_id>/payment", methods=["GET"])
def get_payment(order_id):
    from neo4j_files.neo4j_client import driver
    query = """
    MATCH (:Order {id: $order_id})-[:HAS_PAYMENT]->(p:Payment)
    RETURN p.method AS method, p.amount AS amount, p.status AS status, p.timestamp AS timestamp
    ORDER BY p.timestamp DESC
    LIMIT 1
    """
    with driver.session() as session:
        result = session.run(query, order_id=order_id).single()
        if result:
            return jsonify(result.data())
        else:
            return jsonify({"error": "No payment found"}), 404

#get most viewed products Targets: Redis and SQLite and Neo4j
@app.route("/analytics/popular-products", methods=["GET"])
def popular_products():
    limit = int(request.args.get("limit", 5))
    popular_ids = get_popular_products(limit)
    popular_with_details = []
    for pid in popular_ids:
        product = db.session.get(Product, pid)
        if product:
            sales_history = get_product_sales_history(pid, days=30)
            product_data = {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "stock": product.stock,
                "sales_history": sales_history
            }
            popular_with_details.append(product_data)
    return jsonify(popular_with_details)

#get sales over time targets: neo4j
@app.route("/analytics/sales", methods=["GET"])
def sales_analytics():
    days = int(request.args.get("days", 30))
    end_time = datetime.utcnow()         
    start_time = end_time - timedelta(days=days)
    sales_data = get_sales_by_timeframe(start_time, end_time)
    return jsonify({
        "start_time": start_time.isoformat(),
        "end_time":   end_time.isoformat(),
        "sales_data": sales_data
    })

#get sales history for product targets: neo4j and sqlite
@app.route("/analytics/product-history/<int:product_id>", methods=["GET"])
def product_history(product_id):
    days = int(request.args.get("days", 30))
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    sales_history = get_product_sales_history(product_id, days=days)
    return jsonify({
        "product_id": product_id,
        "product_name": product.name,
        "days": days,
        "sales_history": sales_history
    })

#get all supliers targets sqlite
@app.route("/suppliers", methods=["GET"])
def list_suppliers():
    sup = Supplier.query.all()
    return jsonify([{"id": s.id, "name": s.name} for s in sup])

#add new supliers targets sqlite
@app.route("/suppliers", methods=["POST"])
def add_supplier():
    data = request.json
    s = Supplier(name=data["name"])
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id}), 201

#get all cusotmers targets sqlite
@app.route("/customers", methods=["GET"])
def list_customers():
    customers = Customer.query.all()
    return jsonify([{"id": c.id, "name": c.name, "email": c.email} for c in customers])

#add new customer targets sqlite
@app.route("/customers", methods=["POST"])
def add_customer():
    data = request.json
    c = Customer(name=data["name"], email=data["email"])
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id}), 201

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
