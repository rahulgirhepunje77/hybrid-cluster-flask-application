import os
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres.hybrid-lab.svc.cluster.local")
DB_NAME = os.getenv("DB_NAME", "paymentdb")
DB_USER = os.getenv("DB_USER", "paymentuser")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=5432,
        connect_timeout=5
    )

@app.route("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify(status="healthy", database="connected"), 200
    except Exception as error:
        return jsonify(status="unhealthy", error=str(error)), 503

@app.route("/payments", methods=["GET", "POST"])
def payments():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if request.method == "POST":
            data = request.get_json()
            amount = data.get("amount")

            if amount is None:
                return jsonify(error="amount is required"), 400

            cursor.execute(
                "INSERT INTO payments (amount) VALUES (%s) RETURNING id, amount",
                (amount,)
            )
            payment = cursor.fetchone()
            conn.commit()

            result = {"id": payment[0], "amount": float(payment[1])}
        else:
            cursor.execute("SELECT id, amount FROM payments ORDER BY id")
            result = [
                {"id": row[0], "amount": float(row[1])}
                for row in cursor.fetchall()
            ]

        cursor.close()
        conn.close()
        return jsonify(result)

    except Exception as error:
        return jsonify(error=str(error)), 500
