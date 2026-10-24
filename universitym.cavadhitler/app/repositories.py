"""Repository qatı: yalnız SQL. Bütün sorğular parametrlidir (SQL injection-dan qorunma)."""
import sqlite3


def _row(row):
    return dict(row) if row is not None else None


class CategoryRepository:
    def __init__(self, conn):
        self.conn = conn

    def list_all(self):
        rows = self.conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get(self, category_id):
        return _row(self.conn.execute(
            "SELECT id, name FROM categories WHERE id = ?", (category_id,)).fetchone())


class UserRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, full_name, email, password_hash, role="user"):
        cur = self.conn.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (full_name, email, password_hash, role),
        )
        return cur.lastrowid

    def get_by_id(self, user_id):
        return _row(self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def get_by_email(self, email):
        return _row(self.conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


class EventRepository:
    _SELECT = """
        SELECT e.*, c.name AS category_name,
               (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered_count
        FROM events e
        JOIN categories c ON c.id = e.category_id
    """

    def __init__(self, conn):
        self.conn = conn

    def create(self, data, created_by):
        cur = self.conn.execute(
            """INSERT INTO events (title, description, category_id, event_date, event_time,
                                   location, max_participants, created_by)
               VALUES (:title, :description, :category_id, :event_date, :event_time,
                       :location, :max_participants, :created_by)""",
            {**data, "created_by": created_by},
        )
        return cur.lastrowid

    def update(self, event_id, data):
        self.conn.execute(
            """UPDATE events SET title = :title, description = :description,
                      category_id = :category_id, event_date = :event_date,
                      event_time = :event_time, location = :location,
                      max_participants = :max_participants
               WHERE id = :id""",
            {**data, "id": event_id},
        )

    def delete(self, event_id):
        cur = self.conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return cur.rowcount > 0

    def get(self, event_id):
        return _row(self.conn.execute(self._SELECT + " WHERE e.id = ?", (event_id,)).fetchone())

    def search(self, filters, today):
        """filters: q, category_id, date, date_from, date_to, location, status."""
        conditions, params = [], []
        if filters.get("q"):
            conditions.append("e.title LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(filters['q'])}%")
        if filters.get("category_id"):
            conditions.append("e.category_id = ?")
            params.append(filters["category_id"])
        if filters.get("date"):
            conditions.append("e.event_date = ?")
            params.append(filters["date"])
        if filters.get("date_from"):
            conditions.append("e.event_date >= ?")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            conditions.append("e.event_date <= ?")
            params.append(filters["date_to"])
        if filters.get("location"):
            conditions.append("e.location LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(filters['location'])}%")
        if filters.get("status") == "upcoming":
            conditions.append("e.event_date >= ?")
            params.append(today)
        elif filters.get("status") == "past":
            conditions.append("e.event_date < ?")
            params.append(today)

        sql = self._SELECT
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY e.event_date, e.event_time, e.id"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]


class RegistrationRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, event_id, user_id):
        try:
            cur = self.conn.execute(
                "INSERT INTO registrations (event_id, user_id) VALUES (?, ?)", (event_id, user_id))
        except sqlite3.IntegrityError as exc:
            raise DuplicateRegistration from exc
        return cur.lastrowid

    def remove(self, event_id, user_id):
        cur = self.conn.execute(
            "DELETE FROM registrations WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        return cur.rowcount > 0

    def exists(self, event_id, user_id):
        return self.conn.execute(
            "SELECT 1 FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, user_id)).fetchone() is not None

    def count_for_event(self, event_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)).fetchone()[0]

    def list_for_event(self, event_id):
        rows = self.conn.execute(
            """SELECT u.id AS user_id, u.full_name, u.email, r.registered_at
               FROM registrations r JOIN users u ON u.id = r.user_id
               WHERE r.event_id = ? ORDER BY r.registered_at, r.id""", (event_id,)).fetchall()
        return [dict(r) for r in rows]

    def event_ids_for_user(self, user_id):
        rows = self.conn.execute(
            "SELECT event_id FROM registrations WHERE user_id = ?", (user_id,)).fetchall()
        return {r["event_id"] for r in rows}

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]


class StatsRepository:
    def __init__(self, conn):
        self.conn = conn

    def top_events(self, limit=5):
        rows = self.conn.execute(
            """SELECT e.id, e.title, e.max_participants, COUNT(r.id) AS registered_count
               FROM events e LEFT JOIN registrations r ON r.event_id = e.id
               GROUP BY e.id
               ORDER BY registered_count DESC, e.event_date, e.id
               LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def by_category(self):
        rows = self.conn.execute(
            """SELECT c.name AS category,
                      COUNT(DISTINCT e.id) AS event_count,
                      COUNT(r.id) AS registration_count
               FROM categories c
               LEFT JOIN events e ON e.category_id = c.id
               LEFT JOIN registrations r ON r.event_id = e.id
               GROUP BY c.id ORDER BY event_count DESC, c.name""").fetchall()
        return [dict(r) for r in rows]


class DuplicateRegistration(Exception):
    """Unikal (event_id, user_id) məhdudiyyəti pozulduqda."""


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
