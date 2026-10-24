"""Biznes məntiqi qatı: yoxlamalar, qaydalar, tranzaksiyalar."""
import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .db import transaction
from .errors import AuthError, ConflictError, NotFoundError, ValidationError
from .repositories import (
    CategoryRepository,
    DuplicateRegistration,
    EventRepository,
    RegistrationRepository,
    StatsRepository,
    UserRepository,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 6


def public_user(user):
    return {k: user[k] for k in ("id", "full_name", "email", "role")}


class AuthService:
    def __init__(self, conn):
        self.users = UserRepository(conn)

    def register(self, payload):
        full_name = str(payload.get("full_name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        errors = {}
        if not full_name:
            errors["full_name"] = "Ad və soyad məcburidir"
        if not EMAIL_RE.match(email):
            errors["email"] = "E-poçt ünvanı düzgün deyil"
        if len(password) < MIN_PASSWORD_LENGTH:
            errors["password"] = f"Parol ən azı {MIN_PASSWORD_LENGTH} simvol olmalıdır"
        if errors:
            raise ValidationError("Qeydiyyat məlumatları düzgün deyil", errors)
        if self.users.get_by_email(email):
            raise ConflictError("Bu e-poçt artıq qeydiyyatdan keçib", {"email": "Artıq mövcuddur"})
        user_id = self.users.create(full_name, email, generate_password_hash(password))
        return public_user(self.users.get_by_id(user_id))

    def login(self, payload):
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not email or not password:
            raise ValidationError("E-poçt və parol məcburidir")
        user = self.users.get_by_email(email)
        # Eyni mesaj: istifadəçinin mövcudluğunu açıqlamamaq üçün
        if not user or not check_password_hash(user["password_hash"], password):
            raise AuthError("E-poçt və ya parol yanlışdır")
        return public_user(user)

    def get_user(self, user_id):
        user = self.users.get_by_id(user_id) if user_id else None
        return public_user(user) if user else None


@dataclass
class EventInput:
    """Tədbir formasından gələn məlumatın yoxlanılmış forması."""
    title: str
    description: str
    category_id: int
    event_date: str
    event_time: str
    location: str
    max_participants: int

    @classmethod
    def from_payload(cls, payload):
        errors = {}
        title = str(payload.get("title", "")).strip()
        description = str(payload.get("description", "")).strip()
        location = str(payload.get("location", "")).strip()
        event_date = str(payload.get("event_date", "")).strip()
        event_time = str(payload.get("event_time", "")).strip()

        if not title:
            errors["title"] = "Tədbirin adı məcburidir"
        elif len(title) > 200:
            errors["title"] = "Ad 200 simvoldan uzun ola bilməz"
        if not location:
            errors["location"] = "Keçirilmə yeri məcburidir"
        if not _valid_date(event_date):
            errors["event_date"] = "Tarix YYYY-MM-DD formatında olmalıdır"
        if not _valid_time(event_time):
            errors["event_time"] = "Saat HH:MM formatında olmalıdır"
        category_id = _to_int(payload.get("category_id"))
        if category_id is None:
            errors["category_id"] = "Kateqoriya seçilməlidir"
        max_participants = _to_int(payload.get("max_participants"))
        if max_participants is None or max_participants < 1:
            errors["max_participants"] = "Maksimum iştirakçı sayı müsbət tam ədəd olmalıdır"

        if errors:
            raise ValidationError("Tədbir məlumatları düzgün deyil", errors)
        return cls(title, description, category_id, event_date, event_time, location,
                   max_participants)

    def as_dict(self):
        return self.__dict__.copy()


class EventService:
    def __init__(self, conn, clock=date.today):
        self.conn = conn
        self.clock = clock
        self.events = EventRepository(conn)
        self.categories = CategoryRepository(conn)
        self.registrations = RegistrationRepository(conn)

    def _today(self):
        return self.clock().isoformat()

    def _present(self, event, registered_ids=frozenset()):
        event = dict(event)
        event["is_past"] = event["event_date"] < self._today()
        event["seats_left"] = max(event["max_participants"] - event["registered_count"], 0)
        event["is_full"] = event["seats_left"] == 0
        event["is_registered"] = event["id"] in registered_ids
        return event

    def create(self, payload, user_id):
        data = EventInput.from_payload(payload)
        if data.event_date < self._today():
            raise ValidationError("Tədbir məlumatları düzgün deyil",
                                  {"event_date": "Keçmiş tarixə tədbir yaratmaq olmaz"})
        self._ensure_category(data.category_id)
        event_id = self.events.create(data.as_dict(), user_id)
        return self._present(self.events.get(event_id))

    def update(self, event_id, payload):
        data = EventInput.from_payload(payload)
        self._ensure_category(data.category_id)
        with transaction(self.conn):
            event = self.events.get(event_id)
            if not event:
                raise NotFoundError("Tədbir tapılmadı")
            # Tutum dəyişəndə mövcud qeydiyyatlarla uyğunluğu yoxla
            if data.max_participants < event["registered_count"]:
                raise ValidationError("Limit düzgün deyil", {
                    "max_participants":
                        f"Limit hazırkı qeydiyyat sayından ({event['registered_count']}) az ola bilməz"})
            self.events.update(event_id, data.as_dict())
        return self._present(self.events.get(event_id))

    def delete(self, event_id):
        if not self.events.delete(event_id):
            raise NotFoundError("Tədbir tapılmadı")

    def get(self, event_id, user_id=None):
        event = self.events.get(event_id)
        if not event:
            raise NotFoundError("Tədbir tapılmadı")
        return self._present(event, self._registered_ids(user_id))

    def search(self, filters, user_id=None):
        clean = {
            "q": str(filters.get("q", "")).strip(),
            "category_id": _to_int(filters.get("category_id")),
            "date": _optional_date(filters.get("date"), "date"),
            "date_from": _optional_date(filters.get("date_from"), "date_from"),
            "date_to": _optional_date(filters.get("date_to"), "date_to"),
            "location": str(filters.get("location", "")).strip(),
            "status": filters.get("status") if filters.get("status") in ("upcoming", "past") else None,
        }
        if clean["date_from"] and clean["date_to"] and clean["date_from"] > clean["date_to"]:
            raise ValidationError("Tarix aralığı düzgün deyil",
                                  {"date_from": "Başlanğıc tarixi son tarixdən böyük ola bilməz"})
        registered = self._registered_ids(user_id)
        return [self._present(e, registered) for e in self.events.search(clean, self._today())]

    def list_categories(self):
        return self.categories.list_all()

    def _registered_ids(self, user_id):
        return self.registrations.event_ids_for_user(user_id) if user_id else set()

    def _ensure_category(self, category_id):
        if not self.categories.get(category_id):
            raise ValidationError("Kateqoriya tapılmadı", {"category_id": "Belə kateqoriya yoxdur"})


class RegistrationService:
    def __init__(self, conn, clock=date.today):
        self.conn = conn
        self.clock = clock
        self.events = EventRepository(conn)
        self.registrations = RegistrationRepository(conn)

    def register(self, event_id, user_id):
        with transaction(self.conn):
            event = self.events.get(event_id)
            if not event:
                raise NotFoundError("Tədbir tapılmadı")
            if event["event_date"] < self.clock().isoformat():
                raise ValidationError("Keçmiş tədbirə qeydiyyat mümkün deyil")
            if self.registrations.exists(event_id, user_id):
                raise ConflictError("Siz bu tədbirə artıq qeydiyyatdan keçmisiniz")
            if self.registrations.count_for_event(event_id) >= event["max_participants"]:
                raise ConflictError("İştirakçı limiti dolub, yeni qeydiyyat qəbul edilmir")
            try:
                self.registrations.add(event_id, user_id)
            except DuplicateRegistration as exc:
                raise ConflictError("Siz bu tədbirə artıq qeydiyyatdan keçmisiniz") from exc
        return {"registered_count": self.registrations.count_for_event(event_id)}

    def cancel(self, event_id, user_id):
        if not self.events.get(event_id):
            raise NotFoundError("Tədbir tapılmadı")
        if not self.registrations.remove(event_id, user_id):
            raise NotFoundError("Bu tədbirə qeydiyyatınız yoxdur")
        return {"registered_count": self.registrations.count_for_event(event_id)}

    def participants(self, event_id):
        if not self.events.get(event_id):
            raise NotFoundError("Tədbir tapılmadı")
        return self.registrations.list_for_event(event_id)

    def export_csv(self, event_id):
        """İştirakçı siyahısını CSV mətni kimi qaytarır (Excel üçün UTF-8 BOM ilə)."""
        event = self.events.get(event_id)
        if not event:
            raise NotFoundError("Tədbir tapılmadı")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["№", "Ad və soyad", "E-poçt", "Qeydiyyat vaxtı"])
        for i, p in enumerate(self.registrations.list_for_event(event_id), start=1):
            writer.writerow([i, _safe_cell(p["full_name"]), p["email"], p["registered_at"]])
        return "﻿" + buffer.getvalue(), event["title"]


class StatsService:
    def __init__(self, conn):
        self.events = EventRepository(conn)
        self.registrations = RegistrationRepository(conn)
        self.users = UserRepository(conn)
        self.stats = StatsRepository(conn)

    def dashboard(self):
        return {
            "total_events": self.events.count(),
            "total_registrations": self.registrations.count(),
            "total_users": self.users.count(),
            "top_events": self.stats.top_events(5),
            "by_category": self.stats.by_category(),
        }


# ---------- köməkçi funksiyalar ----------

def _to_int(value):
    try:
        if isinstance(value, bool) or value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _valid_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        return False


def _valid_time(value):
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M") == value
    except ValueError:
        return False


def _optional_date(value, field):
    if not value:
        return None
    value = str(value).strip()
    if not _valid_date(value):
        raise ValidationError("Tarix düzgün deyil", {field: "Tarix YYYY-MM-DD formatında olmalıdır"})
    return value


def _safe_cell(value):
    """CSV injection-dan qorunma: =, +, -, @ ilə başlayan xanaların əvvəlinə ' qoyulur."""
    return "'" + value if value and value[0] in "=+-@" else value
