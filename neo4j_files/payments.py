from neo4j import GraphDatabase
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

def record_payment(order_id, method, amount, status="Paid", transaction_id=None):
    timestamp = datetime.utcnow().isoformat()

    def _tx(tx):
        tx.run(
            """
            MATCH (o:Order {id: $order_id})
            CREATE (p:Payment {
                id: apoc.create.uuid(),
                method: $method,
                amount: $amount,
                status: $status,
                timestamp: $timestamp,
                transaction_id: $txid
            })
            MERGE (o)-[:HAS_PAYMENT]->(p)
            """,
            order_id=order_id,
            method=method,
            amount=amount,
            status=status,
            timestamp=timestamp,
            txid=transaction_id,
        )

    with driver.session() as session:
        session.write_transaction(_tx)
    return True
