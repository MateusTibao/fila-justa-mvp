import os

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, render_template

app = Flask(__name__)


def get_connection():
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")

    if any(not os.getenv(name) for name in required):
        raise RuntimeError("Configuração do banco incompleta")

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=5432,
        sslmode="require",
        connect_timeout=5,
        row_factory=dict_row,
    )


def fetch_priorities():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    rank,
                    tipo,
                    area_nome,
                    ROUND(score_0_100::numeric, 2) AS score_0_100
                FROM gold.mart_fila_priorizacao
                ORDER BY rank
                LIMIT 30
            """)
            return cursor.fetchall()


def check_database():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() is not None


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/")
def index():
    try:
        rows = fetch_priorities()
        return render_template("index.html", rows=rows, error=False)
    except (psycopg.Error, RuntimeError):
        app.logger.error("Consulta à fila indisponível")
        return render_template("index.html", rows=[], error=True), 503


@app.get("/health")
def health():
    try:
        if check_database():
            return jsonify(status="healthy"), 200
    except (psycopg.Error, RuntimeError):
        pass

    return jsonify(status="degraded"), 503
