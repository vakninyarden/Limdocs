import json
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("INDEX_NAME", "owner_courses_index")

import get_courses  # noqa: E402


def _auth_event(sub="user-1", user_id="user-1", method="GET"):
    return {
        "httpMethod": method,
        "pathParameters": {"userId": user_id} if user_id is not None else None,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }


class GetCoursesTests(unittest.TestCase):
    def setUp(self):
        self.table_mock = MagicMock()
        get_courses._table = self.table_mock

    def test_sub_mismatch_returns_403(self):
        resp = get_courses.lambda_handler(_auth_event(sub="user-a", user_id="user-b"), None)
        self.assertEqual(resp["statusCode"], 403)
        self.assertIn("Forbidden", json.loads(resp["body"])["message"])

    def test_missing_user_id_returns_400(self):
        event = {
            "httpMethod": "GET",
            "pathParameters": {},
            "requestContext": {"authorizer": {"claims": {"sub": "user-1"}}},
        }
        resp = get_courses.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 400)

    def test_missing_sub_returns_401(self):
        resp = get_courses.lambda_handler(_auth_event(sub=None), None)
        self.assertEqual(resp["statusCode"], 401)

    def test_happy_path_queries_owner_index_and_returns_raw_items(self):
        items = [
            {"course_id": "c1", "owner_id": "user-1", "visibility": "PRIVATE"},
            {"course_id": "c2", "owner_id": "user-1", "visibility": "PUBLIC"},
        ]
        self.table_mock.query.return_value = {"Items": items}

        resp = get_courses.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["courses"], items)

        kwargs = self.table_mock.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "owner_courses_index")


if __name__ == "__main__":
    unittest.main()
