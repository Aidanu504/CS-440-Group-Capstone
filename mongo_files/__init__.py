from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

def insert_order(order_doc):
    orderid = db.orders.insert_one(order_doc).inserted_id
    return str(orderid)

def find_orders_by_customer(customer_id):
    return list(db.orders.find({"customer_id": customer_id}))

def find_order_by_id(order_id):
    from bson import ObjectId
    try:
        return db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        return None
