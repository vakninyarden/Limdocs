import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("DOCUMENTS_TABLE", "documents")
os.environ.setdefault("VISIBILITY_INDEX_NAME", "visibility_courses_index")
os.environ.setdefault("DOCUMENTS_COURSE_INDEX", "CourseIdIndex")

import get_public_courses  # noqa: E402


def _auth_event(sub="user-a", **extra):
    event = {
        "httpMethod": "GET",
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub},
            },
        },
    }
    event.update(extra)
    return event


def _public_course(course_id, owner_id="owner-1", **extra):
    item = {
        "course_id": course_id,
        "course_name": f"Course {course_id}",
        "visibility": "PUBLIC",
        "owner_id": owner_id,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    item.update(extra)
    return item


class GetPublicCoursesTests(unittest.TestCase):
    def setUp(self):
        self.courses_mock = MagicMock()
        self.documents_mock = MagicMock()
        get_public_courses._courses_table = self.courses_mock
        get_public_courses._documents_table = self.documents_mock

    def _courses_pages(self, pages):
        self.courses_mock.query.side_effect = pages

    def _docs_pages(self, pages):
        self.documents_mock.query.side_effect = pages

    def _empty_docs(self):
        self.documents_mock.query.return_value = {"Items": []}

    def test_options_returns_200_with_cors(self):
        resp = get_public_courses.lambda_handler({"httpMethod": "OPTIONS"}, None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", resp["headers"])

    def test_missing_sub_returns_401(self):
        event = {"httpMethod": "GET", "requestContext": {"authorizer": {"claims": {}}}}
        resp = get_public_courses.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 401)

    def test_empty_result(self):
        self._courses_pages([{"Items": []}])
        resp = get_public_courses.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(json.loads(resp["body"]), {"courses": []})

    def test_index_and_key_condition(self):
        self._courses_pages([{"Items": []}])
        get_public_courses.lambda_handler(_auth_event(), None)
        kwargs = self.courses_mock.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "visibility_courses_index")
        self.assertFalse(kwargs["ScanIndexForward"])

    def test_defence_in_depth_visibility_filtering(self):
        items = [
            _public_course("pub-1"),
            {"course_id": "priv-1", "visibility": "PRIVATE", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "missing-vis", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "none-vis", "visibility": None, "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "lower-priv", "visibility": "private", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "lower-pub", "visibility": "public", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "empty-vis", "visibility": "", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
            {"course_id": "num-vis", "visibility": 1, "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
        ]
        self._courses_pages([{"Items": items}])
        self._empty_docs()

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        body = json.loads(resp["body"])
        ids = {c["course_id"] for c in body["courses"]}
        self.assertEqual(ids, {"pub-1"})

    def test_server_derived_ownership_ignores_forged_client_values(self):
        self._courses_pages([
            {"Items": [_public_course("c1", owner_id="user-a"), _public_course("c2", owner_id="user-b")]}
        ])
        self._empty_docs()

        event = _auth_event(
            sub="user-a",
            body=json.dumps({"is_owner": True, "owner_id": "user-b"}),
            queryStringParameters={"is_owner": "true", "owner_id": "user-b"},
        )
        resp = get_public_courses.lambda_handler(event, None)
        body = json.loads(resp["body"])
        by_id = {c["course_id"]: c["is_owner"] for c in body["courses"]}
        self.assertTrue(by_id["c1"])
        self.assertFalse(by_id["c2"])

    def test_sanitized_shape(self):
        self._courses_pages([
            {
                "Items": [
                    {
                        "course_id": "c1",
                        "course_name": "OS",
                        "visibility": "PUBLIC",
                        "owner_id": "user-a",
                        "owner_username": "alice",
                        "description": "secret",
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "s3_raw_key": "x",
                        "topics": ["a"],
                        "matrix": {},
                    }
                ]
            }
        ])
        self._empty_docs()

        resp = get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertEqual(
            set(course.keys()),
            {
                "course_id",
                "course_name",
                "visibility",
                "is_owner",
                "document_count",
                "last_updated_at",
            },
        )
        for forbidden in (
            "owner_id",
            "owner_username",
            "description",
            "s3_raw_key",
            "s3_processed_key",
            "topics",
            "matrix",
        ):
            self.assertNotIn(forbidden, course)

    def test_course_pagination_to_exhaustion(self):
        pages = []
        for i in range(250):
            pages.append(_public_course(f"c{i}"))
        self._courses_pages([
            {"Items": pages[:100], "LastEvaluatedKey": {"visibility": "PUBLIC", "created_at": "x", "course_id": "c99"}},
            {"Items": pages[100:200], "LastEvaluatedKey": {"visibility": "PUBLIC", "created_at": "y", "course_id": "c199"}},
            {"Items": pages[200:]},
        ])
        self._empty_docs()

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        body = json.loads(resp["body"])
        self.assertEqual(len(body["courses"]), 250)
        self.assertEqual(self.courses_mock.query.call_count, 3)
        second_call = self.courses_mock.query.call_args_list[1].kwargs
        self.assertIn("ExclusiveStartKey", second_call)

    def test_document_pagination_to_exhaustion(self):
        self._courses_pages([{"Items": [_public_course("c1")]}])
        self._docs_pages([
            {
                "Items": [{"created_at": "2026-01-01T00:00:00+00:00"}],
                "LastEvaluatedKey": {"course_id": "c1", "document_id": "d1"},
            },
            {"Items": [{"created_at": "2026-02-01T00:00:00+00:00"}]},
        ])

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertEqual(course["document_count"], 2)
        self.assertEqual(course["last_updated_at"], "2026-02-01T00:00:00+00:00")

    def test_document_statistics(self):
        self._courses_pages([
            {"Items": [_public_course("no-docs", created_at="2026-03-01T00:00:00+00:00")]}
        ])
        self._docs_pages([{"Items": []}])

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertEqual(course["document_count"], 0)
        self.assertEqual(course["last_updated_at"], "2026-03-01T00:00:00+00:00")

    def test_course_updated_at_wins_over_documents(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course(
                        "c1",
                        updated_at="2026-06-01T00:00:00+00:00",
                        created_at="2026-01-01T00:00:00+00:00",
                    )
                ]
            }
        ])
        self._docs_pages([{"Items": [{"created_at": "2026-02-01T00:00:00+00:00"}]}])

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertEqual(course["last_updated_at"], "2026-06-01T00:00:00+00:00")

    def test_last_updated_null_when_nothing_parses(self):
        self._courses_pages([{"Items": [{"course_id": "c1", "visibility": "PUBLIC", "owner_id": "o1"}]}])
        self._docs_pages([{"Items": [{"created_at": "not-a-date"}]}])

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertIsNone(course["last_updated_at"])

    def test_sequential_aggregation_one_query_per_public_course(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course("pub-1"),
                    _public_course("pub-2"),
                    {"course_id": "priv-1", "visibility": "PRIVATE", "owner_id": "o1", "created_at": "2026-01-01T00:00:00+00:00"},
                ]
            }
        ])
        self._docs_pages([{"Items": []}, {"Items": []}])

        get_public_courses.lambda_handler(_auth_event(), None)
        self.assertEqual(self.documents_mock.query.call_count, 2)

    def test_error_contract(self):
        self.courses_mock.query.side_effect = RuntimeError("boom")
        with patch.object(get_public_courses.logger, "exception") as log_mock:
            resp = get_public_courses.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 500)
        body = json.loads(resp["body"])
        self.assertEqual(body, {"message": "Internal server error"})
        self.assertNotIn("error", body)
        self.assertNotIn("boom", resp["body"])
        log_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
