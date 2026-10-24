"""HTTP/API səviyyəsində inteqrasiya testləri (frontend ↔ backend ↔ DB əlaqəsi)."""
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

from app import create_app

FUTURE = (date.today() + timedelta(days=30)).isoformat()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(self.tmp.name, "test.db"),
            "SECRET_KEY": "test",
            "ADMIN_EMAIL": "admin@test.az",
            "ADMIN_PASSWORD": "Admin123!",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, client, email, password):
        return client.post("/api/auth/login", json={"email": email, "password": password})

    def admin_client(self):
        client = self.app.test_client()
        self.assertEqual(self.login(client, "admin@test.az", "Admin123!").status_code, 200)
        return client

    def user_client(self, n=1):
        client = self.app.test_client()
        res = client.post("/api/auth/register", json={
            "full_name": f"User {n}", "email": f"u{n}@test.az", "password": "secret1"})
        self.assertEqual(res.status_code, 201)
        return client

    def payload(self, **overrides):
        data = {"title": "Konfrans", "description": "", "category_id": 1, "event_date": FUTURE,
                "event_time": "10:00", "location": "Akt zalı", "max_participants": 1}
        data.update(overrides)
        return data


class AuthApiTests(ApiTestCase):
    def test_login_with_wrong_password_returns_401(self):  # T13
        res = self.login(self.client, "admin@test.az", "yanlis")
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.get_json())

    def test_me_returns_null_when_anonymous(self):
        self.assertIsNone(self.client.get("/api/auth/me").get_json())

    def test_non_json_body_is_rejected(self):
        res = self.client.post("/api/auth/login", data="email=a", content_type="text/plain")
        self.assertEqual(res.status_code, 400)


class PermissionTests(ApiTestCase):
    def test_event_creation_permissions(self):  # T14
        self.assertEqual(self.client.post("/api/events", json=self.payload()).status_code, 401)
        self.assertEqual(self.user_client().post("/api/events", json=self.payload()).status_code, 403)
        self.assertEqual(self.admin_client().post("/api/events", json=self.payload()).status_code, 201)

    def test_stats_and_participants_are_admin_only(self):
        user = self.user_client()
        self.assertEqual(user.get("/api/stats").status_code, 403)
        self.assertEqual(user.get("/api/events/1/participants").status_code, 403)


class EndToEndTests(ApiTestCase):
    def test_full_registration_flow(self):  # T15
        admin = self.admin_client()
        event_id = admin.post("/api/events", json=self.payload(max_participants=1)).get_json()["id"]

        first, second = self.user_client(1), self.user_client(2)
        res = first.post(f"/api/events/{event_id}/register")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(first.post(f"/api/events/{event_id}/register").status_code, 409)  # təkrar
        self.assertEqual(second.post(f"/api/events/{event_id}/register").status_code, 409)  # limit

        listed = first.get("/api/events").get_json()[0]
        self.assertEqual(listed["registered_count"], 1)
        self.assertTrue(listed["is_registered"])
        self.assertTrue(listed["is_full"])

        self.assertEqual(first.delete(f"/api/events/{event_id}/register").status_code, 200)
        self.assertEqual(second.post(f"/api/events/{event_id}/register").status_code, 201)

    def test_search_without_results_and_validation_errors(self):
        admin = self.admin_client()
        res = admin.post("/api/events", json=self.payload(title=""))
        self.assertEqual(res.status_code, 400)
        self.assertIn("title", res.get_json()["details"])
        self.assertEqual(self.client.get("/api/events?q=yoxdur").get_json(), [])

    def test_csv_export_and_stats(self):
        admin = self.admin_client()
        event_id = admin.post("/api/events", json=self.payload(max_participants=5)).get_json()["id"]
        self.user_client().post(f"/api/events/{event_id}/register")
        res = admin.get(f"/api/events/{event_id}/export")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers["Content-Type"])
        self.assertIn("u1@test.az", res.get_data(as_text=True))
        stats = admin.get("/api/stats").get_json()
        self.assertEqual((stats["total_events"], stats["total_registrations"]), (1, 1))

    def test_pages_render(self):
        for path in ("/", "/login", "/register", "/events/new", "/dashboard"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_unexpected_error_returns_friendly_message(self):  # T16
        with mock.patch("app.routes.EventService.search", side_effect=RuntimeError("boom")):
            res = self.client.get("/api/events")
        self.assertEqual(res.status_code, 500)
        self.assertIn("Gözlənilməyən xəta", res.get_json()["error"])
        self.assertNotIn("boom", res.get_data(as_text=True))

    def test_unknown_api_route_returns_json_404(self):
        res = self.client.get("/api/yoxdur")
        self.assertEqual(res.status_code, 404)
        self.assertIn("error", res.get_json())


if __name__ == "__main__":
    unittest.main()
