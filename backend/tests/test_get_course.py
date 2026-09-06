import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("COURSES_TABLE", "courses")

import get_course  # noqa: E402


def _auth_event(sub="owner-1", course_id="c1", method="GET"):
    return {
        "httpMethod": method,
        "pathParameters": {"courseId": course_id} if course_id is not None else None,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }


def _course_item(**extra):
    item = {
        "course_id": "c1",
        "course_name": "OS",
        "visibility": "PUBLIC",
        "owner_id": "owner-1",
        "owner_username": "alice",
        "description": "secret",
        "email": "hidden@example.com",
    }
    item.update(extra)
    return item


class GetCourseTests(unittest.TestCase):
    def setUp(self):
        self.table_mock = MagicMock()
        get_course._courses_table = self.table_mock

    def test_options_returns_200_with_cors(self):
        resp = get_course.lambda_handler({"httpMethod": "OPTIONS"}, None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", resp["headers"])

    def test_missing_sub_returns_401(self):
        resp = get_course.lambda_handler(_auth_event(sub=None), None)
        self.assertEqual(resp["statusCode"], 401)

    def test_missing_course_id_returns_400(self):
        resp = get_course.lambda_handler(_auth_event(course_id=None), None)
        self.assertEqual(resp["statusCode"], 400)

    def test_owner_payload_is_whitelisted_and_is_owner_true(self):
        self.table_mock.get_item.return_value = {"Item": _course_item(visibility="PRIVATE")}
        resp = get_course.lambda_handler(_auth_event(sub="owner-1"), None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(
            set(body.keys()),
            {"course_id", "course_name", "visibility", "is_owner"},
        )
        self.assertEqual(body["course_id"], "c1")
        self.assertEqual(body["course_name"], "OS")
        self.assertEqual(body["visibility"], "PRIVATE")
        self.assertTrue(body["is_owner"])
        for forbidden in ("owner_id", "email", "description", "owner_username"):
            self.assertNotIn(forbidden, body)

    def test_visitor_public_is_owner_false_server_derived(self):
        self.table_mock.get_item.return_value = {"Item": _course_item()}
        event = _auth_event(sub="visitor")
        event["queryStringParameters"] = {"is_owner": "true"}
        event["body"] = json.dumps({"is_owner": True, "owner_id": "visitor"})
        resp = get_course.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertFalse(body["is_owner"])
        self.assertEqual(body["visibility"], "PUBLIC")
        self.assertNotIn("owner_id", body)

    def test_non_owner_private_returns_403(self):
        self.table_mock.get_item.return_value = {"Item": _course_item(visibility="PRIVATE")}
        resp = get_course.lambda_handler(_auth_event(sub="visitor"), None)
        self.assertEqual(resp["statusCode"], 403)

    def test_missing_course_returns_404(self):
        self.table_mock.get_item.return_value = {}
        resp = get_course.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 404)

    def test_error_contract(self):
        self.table_mock.get_item.side_effect = RuntimeError("boom")
        with patch.object(get_course.logger, "exception") as log_mock:
            resp = get_course.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 500)
        body = json.loads(resp["body"])
        self.assertEqual(body, {"message": "Internal server error"})
        self.assertNotIn("boom", resp["body"])
        log_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
