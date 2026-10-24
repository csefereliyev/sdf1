"""HTTP qatı: sorğunu qəbul edir, servisləri çağırır, JSON qaytarır."""
from functools import wraps
from types import SimpleNamespace

from flask import Blueprint, Response, g, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from .db import get_db
from .errors import AuthError, ForbiddenError, ValidationError
from .services import AuthService, EventService, RegistrationService, StatsService

api = Blueprint("api", __name__)
pages = Blueprint("pages", __name__)


def services():
    """Hər sorğu üçün servis obyektlərini bir dəfə yaradır."""
    if "services" not in g:
        conn = get_db()
        g.services = SimpleNamespace(
            auth=AuthService(conn),
            events=EventService(conn),
            registrations=RegistrationService(conn),
            stats=StatsService(conn),
        )
    return g.services


def current_user():
    return services().auth.get_user(session.get("user_id"))


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            raise AuthError("Bu əməliyyat üçün daxil olmalısınız")
        g.user = user
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            raise ForbiddenError("Bu əməliyyat yalnız administrator üçündür")
        return view(*args, **kwargs)
    return wrapper


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Sorğu JSON formatında olmalıdır")
    return data


# ---------- Auth ----------

@api.post("/auth/register")
def register():
    user = services().auth.register(json_body())
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user), 201


@api.post("/auth/login")
def login():
    user = services().auth.login(json_body())
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user)


@api.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@api.get("/auth/me")
def me():
    return jsonify(current_user())


# ---------- Events ----------

@api.get("/categories")
def categories():
    return jsonify(services().events.list_categories())


@api.get("/events")
def list_events():
    user = current_user()
    events = services().events.search(request.args, user["id"] if user else None)
    return jsonify(events)


@api.get("/events/<int:event_id>")
def get_event(event_id):
    user = current_user()
    return jsonify(services().events.get(event_id, user["id"] if user else None))


@api.post("/events")
@admin_required
def create_event():
    return jsonify(services().events.create(json_body(), g.user["id"])), 201


@api.put("/events/<int:event_id>")
@admin_required
def update_event(event_id):
    return jsonify(services().events.update(event_id, json_body()))


@api.delete("/events/<int:event_id>")
@admin_required
def delete_event(event_id):
    services().events.delete(event_id)
    return jsonify({"ok": True})


# ---------- Registrations ----------

@api.post("/events/<int:event_id>/register")
@login_required
def register_for_event(event_id):
    return jsonify(services().registrations.register(event_id, g.user["id"])), 201


@api.delete("/events/<int:event_id>/register")
@login_required
def cancel_registration(event_id):
    return jsonify(services().registrations.cancel(event_id, g.user["id"]))


@api.get("/events/<int:event_id>/participants")
@admin_required
def participants(event_id):
    return jsonify(services().registrations.participants(event_id))


@api.get("/events/<int:event_id>/export")
@admin_required
def export_participants(event_id):
    content, title = services().registrations.export_csv(event_id)
    filename = secure_filename(title) or "event"
    return Response(
        content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}_participants.csv"},
    )


# ---------- Stats ----------

@api.get("/stats")
@admin_required
def stats():
    return jsonify(services().stats.dashboard())


# ---------- Səhifələr (HTML qabıqları; məlumat API-dən gəlir) ----------

@pages.get("/")
def index():
    return render_template("index.html")


@pages.get("/login")
def login_page():
    return render_template("login.html")


@pages.get("/register")
def register_page():
    return render_template("register.html")


@pages.get("/events/new")
def new_event_page():
    return render_template("event_form.html", event_id=None)


@pages.get("/events/<int:event_id>")
def event_detail_page(event_id):
    return render_template("event_detail.html", event_id=event_id)


@pages.get("/events/<int:event_id>/edit")
def edit_event_page(event_id):
    return render_template("event_form.html", event_id=event_id)


@pages.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")
