"""Servis qatının unit testləri (yaddaşda SQLite bazası ilə)."""
import unittest
from datetime import date

from app.db import connect, init_db
from app.errors import ConflictError, NotFoundError, ValidationError
from app.services import AuthService, EventService, RegistrationService, StatsService

TODAY = date(2026, 10, 24)


def event_payload(**overrides):
    payload = {
        "title": "Python seminarı",
        "description": "Giriş",
        "category_id": 2,
        "event_date": "2026-11-15",
        "event_time": "14:00",
        "location": "Auditoriya 204",
        "max_participants": 2,
    }
    payload.update(overrides)
    return payload


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        init_db(self.conn, "admin@test.az", "Admin123!")
        clock = lambda: TODAY  # noqa: E731
        self.events = EventService(self.conn, clock)
        self.regs = RegistrationService(self.conn, clock)
        self.stats = StatsService(self.conn)
        self.auth = AuthService(self.conn)
        self.admin_id = self.auth.users.get_by_email("admin@test.az")["id"]

    def tearDown(self):
        self.conn.close()

    def make_user(self, n):
        return self.auth.register(
            {"full_name": f"User {n}", "email": f"user{n}@test.az", "password": "secret1"})["id"]

    def make_event(self, **overrides):
        return self.events.create(event_payload(**overrides), self.admin_id)


class EventManagementTests(ServiceTestCase):
    def test_create_event_saves_all_fields(self):  # T1
        event = self.make_event()
        self.assertEqual(event["title"], "Python seminarı")
        self.assertEqual(event["max_participants"], 2)
        self.assertEqual(event["registered_count"], 0)
        self.assertFalse(event["is_past"])

    def test_create_event_with_empty_required_fields_is_rejected(self):  # T2
        with self.assertRaises(ValidationError) as ctx:
            self.make_event(title="  ", location="", max_participants="")
        self.assertEqual(set(ctx.exception.errors), {"title", "location", "max_participants"})

    def test_create_event_in_past_is_rejected(self):  # T3
        with self.assertRaises(ValidationError) as ctx:
            self.make_event(event_date="2026-01-01")
        self.assertIn("event_date", ctx.exception.errors)

    def test_invalid_date_and_limit_are_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.make_event(event_date="31.12.2026", event_time="25:00", max_participants=0)
        self.assertEqual(set(ctx.exception.errors), {"event_date", "event_time", "max_participants"})

    def test_past_and_upcoming_events_are_distinguished(self):
        upcoming = self.make_event()
        self.conn.execute("UPDATE events SET event_date = '2026-01-01' WHERE id = ?", (upcoming["id"],))
        self.assertTrue(self.events.get(upcoming["id"])["is_past"])

    def test_update_changes_event(self):
        event = self.make_event()
        updated = self.events.update(event["id"], event_payload(title="Yeni ad", max_participants=10))
        self.assertEqual(updated["title"], "Yeni ad")
        self.assertEqual(updated["max_participants"], 10)

    def test_update_capacity_below_registered_count_is_rejected(self):  # T4
        event = self.make_event(max_participants=3)
        for n in (1, 2):
            self.regs.register(event["id"], self.make_user(n))
        with self.assertRaises(ValidationError):
            self.events.update(event["id"], event_payload(max_participants=1))
        self.assertEqual(self.events.get(event["id"])["max_participants"], 3)

    def test_delete_event_removes_its_registrations(self):
        event = self.make_event()
        self.regs.register(event["id"], self.make_user(1))
        self.events.delete(event["id"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0], 0)
        with self.assertRaises(NotFoundError):
            self.events.get(event["id"])


class SearchTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.make_event(title="Python seminarı", category_id=2, location="Auditoriya 204",
                        event_date="2026-11-01")
        self.make_event(title="AI konfransı", category_id=1, location="Akt zalı",
                        event_date="2026-12-01")

    def titles(self, **filters):
        return [e["title"] for e in self.events.search(filters)]

    def test_search_by_name(self):  # T5
        self.assertEqual(self.titles(q="python"), ["Python seminarı"])

    def test_filter_by_category_location_and_dates(self):
        self.assertEqual(self.titles(category_id="1"), ["AI konfransı"])
        self.assertEqual(self.titles(location="akt"), ["AI konfransı"])
        self.assertEqual(self.titles(date="2026-11-01"), ["Python seminarı"])
        self.assertEqual(len(self.titles(date_from="2026-10-01", date_to="2026-12-31")), 2)

    def test_empty_result_returns_empty_list(self):  # T6
        self.assertEqual(self.titles(q="mövcud olmayan tədbir"), [])

    def test_sql_injection_attempt_is_harmless(self):  # T7
        self.assertEqual(self.titles(q="'; DROP TABLE events; --"), [])
        self.assertEqual(len(self.events.search({})), 2)

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.events.search({"date_from": "2026-12-01", "date_to": "2026-11-01"})


class RegistrationTests(ServiceTestCase):
    def test_register_increases_participant_count(self):  # T8
        event = self.make_event()
        result = self.regs.register(event["id"], self.make_user(1))
        self.assertEqual(result["registered_count"], 1)
        self.assertEqual(self.events.get(event["id"])["registered_count"], 1)

    def test_duplicate_registration_is_prevented(self):  # T9
        event, user = self.make_event(), self.make_user(1)
        self.regs.register(event["id"], user)
        with self.assertRaises(ConflictError):
            self.regs.register(event["id"], user)
        self.assertEqual(self.events.get(event["id"])["registered_count"], 1)

    def test_capacity_limit_is_enforced(self):  # T10
        event = self.make_event(max_participants=2)
        self.regs.register(event["id"], self.make_user(1))
        self.regs.register(event["id"], self.make_user(2))
        with self.assertRaises(ConflictError):
            self.regs.register(event["id"], self.make_user(3))
        self.assertEqual(self.events.get(event["id"])["registered_count"], 2)

    def test_cancel_frees_a_seat(self):  # T11
        event = self.make_event(max_participants=1)
        first, second = self.make_user(1), self.make_user(2)
        self.regs.register(event["id"], first)
        self.regs.cancel(event["id"], first)
        self.regs.register(event["id"], second)
        self.assertEqual(self.events.get(event["id"])["registered_count"], 1)

    def test_cancel_without_registration_fails(self):
        event = self.make_event()
        with self.assertRaises(NotFoundError):
            self.regs.cancel(event["id"], self.make_user(1))

    def test_register_for_past_event_is_rejected(self):
        event = self.make_event()
        self.conn.execute("UPDATE events SET event_date = '2026-01-01' WHERE id = ?", (event["id"],))
        with self.assertRaises(ValidationError):
            self.regs.register(event["id"], self.make_user(1))

    def test_register_for_missing_event_fails(self):
        with self.assertRaises(NotFoundError):
            self.regs.register(9999, self.make_user(1))

    def test_export_csv_lists_participants(self):
        event = self.make_event()
        self.regs.register(event["id"], self.make_user(1))
        content, title = self.regs.export_csv(event["id"])
        self.assertTrue(content.startswith("﻿"))
        self.assertIn("user1@test.az", content)
        self.assertEqual(title, "Python seminarı")


class StatsTests(ServiceTestCase):
    def test_dashboard_statistics(self):  # T12
        popular = self.make_event(title="Populyar", category_id=1, max_participants=5)
        self.make_event(title="Az maraqlı", category_id=2, max_participants=5)
        for n in (1, 2, 3):
            self.regs.register(popular["id"], self.make_user(n))
        data = self.stats.dashboard()
        self.assertEqual(data["total_events"], 2)
        self.assertEqual(data["total_registrations"], 3)
        self.assertEqual(data["top_events"][0]["title"], "Populyar")
        by_cat = {c["category"]: c for c in data["by_category"]}
        self.assertEqual(by_cat["Konfrans"]["registration_count"], 3)
        self.assertEqual(by_cat["Seminar"]["event_count"], 1)


class AuthTests(ServiceTestCase):
    def test_register_validates_input(self):
        with self.assertRaises(ValidationError) as ctx:
            self.auth.register({"full_name": "", "email": "yanlis", "password": "123"})
        self.assertEqual(set(ctx.exception.errors), {"full_name", "email", "password"})

    def test_duplicate_email_is_rejected(self):
        self.make_user(1)
        with self.assertRaises(ConflictError):
            self.make_user(1)

    def test_password_is_hashed(self):
        self.make_user(1)
        stored = self.auth.users.get_by_email("user1@test.az")["password_hash"]
        self.assertNotIn("secret1", stored)


if __name__ == "__main__":
    unittest.main()
