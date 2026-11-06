import os
from contextlib import closing

import psycopg2
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Prometheus instrumentation
metrics = PrometheusMetrics(app)

# PostgreSQL configuration
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
        with closing(get_connection()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

        return jsonify(status="healthy", database="connected"), 200

    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify(status="unhealthy", database="disconnected"), 503


@app.route("/payments", methods=["GET", "POST"])
def payments():
    try:
        with closing(get_connection()) as conn:
            with conn.cursor() as cursor:

                if request.method == "POST":
                    data = request.get_json(silent=True) or {}
                    amount = data.get("amount")

                    if amount is None:
                        return jsonify(error="amount is required"), 400

                    cursor.execute(
                        """
                        INSERT INTO payments (amount)
                        VALUES (%s)
                        RETURNING id, amount
                        """,
                        (amount,)
                    )

                    payment = cursor.fetchone()
                    conn.commit()

                    result = {
                        "id": payment[0],
                        "amount": float(payment[1])
                    }

                else:
                    cursor.execute(
                        "SELECT id, amount FROM payments ORDER BY id"
                    )

                    result = [
                        {"id": row[0], "amount": float(row[1])}
                        for row in cursor.fetchall()
                    ]

        return jsonify(result), 200

    except Exception:
        app.logger.exception("Payment request failed")
        return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
