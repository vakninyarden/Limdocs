import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
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
        self.dynamodb_mock = MagicMock()
        get_public_courses._courses_table = self.courses_mock
        get_public_courses._documents_table = self.documents_mock
        get_public_courses._dynamodb = self.dynamodb_mock
        self._usernames({})

    def _courses_pages(self, pages):
        self.courses_mock.query.side_effect = pages

    def _docs_pages(self, pages):
        self.documents_mock.query.side_effect = pages

    def _empty_docs(self):
        self.documents_mock.query.return_value = {"Items": []}

    def _usernames(self, mapping):
        items = [
            {"course_id": course_id, "owner_username": username}
            for course_id, username in mapping.items()
        ]
        self.dynamodb_mock.batch_get_item.return_value = {
            "Responses": {get_public_courses.COURSES_TABLE: items}
        }

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

    def test_foreign_course_includes_owner_username(self):
        self._courses_pages([
            {"Items": [_public_course("c2", owner_id="user-b")]}
        ])
        self._usernames({"c2": "nadav123"})
        self._empty_docs()
        resp = get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertFalse(course["is_owner"])
        self.assertEqual(course["owner_username"], "nadav123")
        self.assertNotIn("owner_id", course)
        self.assertNotIn("email", course)

    def test_blank_owner_username_is_omitted(self):
        self._courses_pages([{"Items": [_public_course("c1")]}])
        self._usernames({"c1": "  "})
        self._empty_docs()
        course = json.loads(
            get_public_courses.lambda_handler(_auth_event(), None)["body"]
        )["courses"][0]
        self.assertNotIn("owner_username", course)

    def test_owned_public_course_keeps_is_owner_true(self):
        self._courses_pages([
            {"Items": [_public_course("c1", owner_id="user-a")]}
        ])
        self._usernames({"c1": "me"})
        self._empty_docs()
        course = json.loads(
            get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)["body"]
        )["courses"][0]
        self.assertTrue(course["is_owner"])
        self.assertEqual(course["owner_username"], "me")
        self.assertIn("document_count", course)
        self.assertIn("last_updated_at", course)

    def test_owner_username_comes_from_base_table_not_gsi(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course(
                        "c1",
                        owner_id="user-b",
                        owner_username="from-gsi",
                    )
                ]
            }
        ])
        self._usernames({"c1": "from-base"})
        self._empty_docs()
        course = json.loads(
            get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)["body"]
        )["courses"][0]
        self.assertEqual(course["owner_username"], "from-base")
        self.assertFalse(course["is_owner"])

    def test_batch_get_used_once_for_multiple_courses(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course("c1", owner_id="user-a"),
                    _public_course("c2", owner_id="user-b"),
                    _public_course("c3", owner_id="user-c"),
                ]
            }
        ])
        self._usernames({"c1": "alice", "c2": "bob", "c3": "cara"})
        self._empty_docs()

        resp = get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)
        body = json.loads(resp["body"])
        by_id = {c["course_id"]: c for c in body["courses"]}
        self.assertTrue(by_id["c1"]["is_owner"])
        self.assertFalse(by_id["c2"]["is_owner"])
        self.assertEqual(by_id["c2"]["owner_username"], "bob")
        self.assertEqual(self.dynamodb_mock.batch_get_item.call_count, 1)
        self.courses_mock.get_item.assert_not_called()
        kwargs = self.dynamodb_mock.batch_get_item.call_args.kwargs
        request = kwargs["RequestItems"][get_public_courses.COURSES_TABLE]
        self.assertEqual(
            request["ProjectionExpression"],
            "course_id, owner_username",
        )
        self.assertEqual(
            request["Keys"],
            [
                {"course_id": "c1"},
                {"course_id": "c2"},
                {"course_id": "c3"},
            ],
        )
        for key in request["Keys"]:
            self.assertEqual(set(key.keys()), {"course_id"})

    def test_batch_get_chunks_over_100(self):
        ids = [f"c{i}" for i in range(101)]
        self._courses_pages([{"Items": [_public_course(cid) for cid in ids]}])
        self._empty_docs()

        get_public_courses.lambda_handler(_auth_event(), None)
        self.assertEqual(self.dynamodb_mock.batch_get_item.call_count, 2)
        first_keys = self.dynamodb_mock.batch_get_item.call_args_list[0].kwargs[
            "RequestItems"
        ][get_public_courses.COURSES_TABLE]["Keys"]
        second_keys = self.dynamodb_mock.batch_get_item.call_args_list[1].kwargs[
            "RequestItems"
        ][get_public_courses.COURSES_TABLE]["Keys"]
        self.assertEqual(len(first_keys), 100)
        self.assertEqual(len(second_keys), 1)
        self.assertEqual(first_keys[0], {"course_id": "c0"})
        self.assertEqual(second_keys[0], {"course_id": "c100"})
        for key in first_keys + second_keys:
            self.assertEqual(set(key.keys()), {"course_id"})

    def test_unprocessed_keys_are_retried(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course("c1"),
                    _public_course("c2"),
                ]
            }
        ])
        self._empty_docs()
        table = get_public_courses.COURSES_TABLE
        self.dynamodb_mock.batch_get_item.side_effect = [
            {
                "Responses": {table: [{"course_id": "c1", "owner_username": "alice"}]},
                "UnprocessedKeys": {
                    table: {
                        "Keys": [{"course_id": "c2"}],
                        "ProjectionExpression": "course_id, owner_username",
                    }
                },
            },
            {
                "Responses": {table: [{"course_id": "c2", "owner_username": "bob"}]},
            },
        ]

        courses = json.loads(
            get_public_courses.lambda_handler(_auth_event(), None)["body"]
        )["courses"]
        by_id = {c["course_id"]: c["owner_username"] for c in courses}
        self.assertEqual(by_id, {"c1": "alice", "c2": "bob"})
        self.assertEqual(self.dynamodb_mock.batch_get_item.call_count, 2)

    def test_empty_public_list_skips_batch_get(self):
        self._courses_pages([{"Items": []}])
        get_public_courses.lambda_handler(_auth_event(), None)
        self.dynamodb_mock.batch_get_item.assert_not_called()

    def test_missing_created_at_still_looks_up_username(self):
        self._courses_pages([
            {
                "Items": [
                    _public_course("c1", created_at="2026-01-01T00:00:00+00:00"),
                    {"course_id": "c2", "visibility": "PUBLIC", "owner_id": "o1"},
                ]
            }
        ])
        self._usernames({"c1": "alice", "c2": "bob"})
        self._empty_docs()

        resp = get_public_courses.lambda_handler(_auth_event(), None)
        request = self.dynamodb_mock.batch_get_item.call_args.kwargs["RequestItems"][
            get_public_courses.COURSES_TABLE
        ]
        self.assertEqual(
            request["Keys"],
            [{"course_id": "c1"}, {"course_id": "c2"}],
        )
        for key in request["Keys"]:
            self.assertEqual(set(key.keys()), {"course_id"})
        by_id = {c["course_id"]: c for c in json.loads(resp["body"])["courses"]}
        self.assertEqual(by_id["c2"]["owner_username"], "bob")

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
                        "owner_username": "from-gsi",
                        "email": "alice@example.com",
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
        self.dynamodb_mock.batch_get_item.return_value = {
            "Responses": {
                get_public_courses.COURSES_TABLE: [
                    {
                        "course_id": "c1",
                        "owner_username": "alice",
                        "owner_id": "user-a",
                        "email": "alice@example.com",
                        "sub": "user-a",
                    }
                ]
            }
        }

        resp = get_public_courses.lambda_handler(_auth_event(sub="user-a"), None)
        course = json.loads(resp["body"])["courses"][0]
        self.assertEqual(
            set(course.keys()),
            {
                "course_id",
                "course_name",
                "visibility",
                "is_owner",
                "owner_username",
                "document_count",
                "last_updated_at",
            },
        )
        self.assertEqual(course["owner_username"], "alice")
        for forbidden in (
            "owner_id",
            "description",
            "s3_raw_key",
            "s3_processed_key",
            "topics",
            "matrix",
            "email",
            "sub",
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
