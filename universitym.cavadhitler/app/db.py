"""Verilənlər bazası ilə iş: bağlantı, sxemin yaradılması, tranzaksiya."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_CATEGORIES = ["Konfrans", "Seminar", "Təlim", "Müsabiqə", "Digər"]


def connect(path):
    # isolation_level=None: tranzaksiyaları özümüz idarə edirik (BEGIN IMMEDIATE)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn):
    """BEGIN IMMEDIATE yazı kilidini dərhal alır, beləliklə limit yoxlaması
    ilə qeydiyyat əlavə etmə arasında başqa sorğu gedə bilməz."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_db(conn, admin_email, admin_password):
    """Sxemi yaradır, kateqoriyaları və ilk admini əlavə edir (təkrar çağırış təhlükəsizdir)."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    for name in DEFAULT_CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (admin_email,)).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Administrator", admin_email, generate_password_hash(admin_password)),
        )


def init_app(app):
    app.teardown_appcontext(close_db)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(app.config["DATABASE"])
    try:
        init_db(conn, app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"])
    finally:
        conn.close()
