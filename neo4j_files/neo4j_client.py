from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timedelta
from neo4j import GraphDatabase

uri      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user     = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")
driver = GraphDatabase.driver(uri, auth=(user, password))

def record_order_metrics(order_data):
    order_id     = str(order_data.get("_id", "unknown"))
    customer_id  = str(order_data.get("customer_id", 0))
    total_amount = float(order_data.get("total_amount", 0.0))
    order_date   = datetime.utcnow().isoformat()

    def _tx(tx):
        tx.run(
            """
            MERGE (c:Customer {id: $cust})
            MERGE (o:Order {id: $order})
            SET o.total_amount = $total, o.date = $date
            MERGE (c)-[:PLACED]->(o)
            """,
            cust=customer_id, order=order_id,
            total=total_amount, date=order_date,
        )
        for item in order_data.get("items", []):
            pid      = str(item.get("product_id", 0))
            qty      = int(item.get("quantity", 1))
            price    = float(item.get("price", 0.0))
            subtotal = qty * price
            tx.run(
                """
                MERGE (p:Product {id: $pid})
                MERGE (o:Order {id: $order})
                MERGE (o)-[r:CONTAINS]->(p)
                SET r.quantity = $qty, r.price = $price, r.total = $subtotal
                """,
                pid=pid, order=order_id, qty=qty, price=price, subtotal=subtotal
            )

    with driver.session() as session:
        session.write_transaction(_tx)
    return True

def record_inventory_change(product_id, old_stock, new_stock):
    ts     = datetime.utcnow().isoformat()
    change = new_stock - old_stock

    def _tx(tx):
        tx.run(
            """
            MERGE (p:Product {id: $pid})
            CREATE (ic:InventoryChange {
                old_stock: $old,
                new_stock: $new,
                change: $chg,
                timestamp: $ts
            })
            MERGE (p)-[:HAS_CHANGE]->(ic)
            """,
            pid=str(product_id),
            old=old_stock, new=new_stock,
            chg=change, ts=ts
        )

    with driver.session() as session:
        session.write_transaction(_tx)
    return True

def get_sales_by_timeframe(start_time, end_time):
    start_iso = start_time.isoformat()
    end_iso   = end_time.isoformat()

    def _tx(tx):
        result = tx.run(
            """
            MATCH (o:Order)
            WHERE datetime(o.date) >= datetime($start)
              AND datetime(o.date) <= datetime($end)
            RETURN date(datetime(o.date)) AS day,
                   sum(o.total_amount)      AS total_sales
            ORDER BY day
            """,
            start=start_iso, end=end_iso
        )
        return [
            {"time": record["day"].iso_format(), "total_sales": record["total_sales"]}
            for record in result
        ]

    with driver.session() as session:
        return session.read_transaction(_tx)

def get_product_sales_history(product_id, days=30):
    now       = datetime.utcnow()
    start     = now - timedelta(days=days)
    start_iso = start.isoformat()
    end_iso   = now.isoformat()

    def _tx(tx):
        result = tx.run(
            """
            MATCH (o:Order)-[r:CONTAINS]->(p:Product {id:$pid})
            WHERE datetime(o.date) >= datetime($start)
              AND datetime(o.date) <= datetime($end)
            RETURN date(datetime(o.date)) AS day,
                   sum(r.total)            AS sales
            ORDER BY day
            """,
            pid=str(product_id), start=start_iso, end=end_iso
        )
        return [
            {"time": record["day"].iso_format(), "sales": record["sales"]}
            for record in result
        ]

    with driver.session() as session:
        return session.read_transaction(_tx)
