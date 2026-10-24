"""Demo məlumatları əlavə edir: python seed.py"""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import connect

app = create_app()
conn = connect(app.config["DATABASE"])

if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]:
    print("Bazada artıq tədbirlər var, seed ləğv edildi.")
    raise SystemExit(0)

categories = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}
admin_id = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()["id"]


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


events = [
    ("Süni intellekt konfransı", "AI-in təhsildə tətbiqi", "Konfrans", day(10), "10:00", "Akt zalı", 100),
    ("Python seminarı", "Başlayanlar üçün Python", "Seminar", day(5), "14:00", "Auditoriya 204", 3),
    ("Veb proqramlaşdırma təlimi", "Flask ilə veb tətbiq", "Təlim", day(20), "11:00", "Kompüter laboratoriyası", 25),
    ("Hackathon 2026", "24 saatlıq proqramlaşdırma müsabiqəsi", "Müsabiqə", day(30), "09:00", "İnnovasiya mərkəzi", 60),
    ("Keçmiş elmi seminar", "Arxiv tədbiri", "Seminar", day(-15), "13:00", "Kitabxana", 40),
]
for title, desc, cat, d, t, loc, cap in events:
    conn.execute(
        """INSERT INTO events (title, description, category_id, event_date, event_time,
                               location, max_participants, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, desc, categories[cat], d, t, loc, cap, admin_id))

for i in range(1, 4):
    conn.execute(
        "INSERT OR IGNORE INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
        (f"Tələbə {i}", f"student{i}@university.az", generate_password_hash("Student123!")))

print("Demo məlumatlar əlavə olundu. Giriş: student1@university.az / Student123!")
conn.close()
