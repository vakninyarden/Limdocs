import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("COURSES_TABLE", "courses")

import update_course_visibility  # noqa: E402


def _auth_event(sub="owner-1", course_id="c1", body=None, method="PATCH"):
    event = {
        "httpMethod": method,
        "pathParameters": {"courseId": course_id} if course_id is not None else None,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }
    if body is not None:
        event["body"] = body if isinstance(body, str) else json.dumps(body)
    return event


def _owner_item(visibility="PRIVATE", **extra):
    item = {
        "course_id": "c1",
        "owner_id": "owner-1",
        "course_name": "OS",
        "visibility": visibility,
        "created_at": "2026-01-01T00:00:00+00:00",
        "description": "secret",
    }
    item.update(extra)
    return item


def _client_error(code):
    return ClientError(
        {"Error": {"Code": code, "Message": "failed"}},
        "UpdateItem",
    )


class UpdateCourseVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.table_mock = MagicMock()
        update_course_visibility._table = self.table_mock

    def test_options_returns_200_with_cors(self):
        resp = update_course_visibility.lambda_handler({"httpMethod": "OPTIONS"}, None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", resp["headers"])
        self.assertIn("PATCH", resp["headers"]["Access-Control-Allow-Methods"])

    def test_missing_sub_returns_401(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(sub=None, body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 401)

    def test_missing_course_id_returns_400(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(course_id=None, body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 400)

    def test_invalid_json_returns_400(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(body="{not-json"),
            None,
        )
        self.assertEqual(resp["statusCode"], 400)

    def test_missing_visibility_returns_400(self):
        resp = update_course_visibility.lambda_handler(_auth_event(body={}), None)
        self.assertEqual(resp["statusCode"], 400)

    def test_lowercase_visibility_returns_400(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "public"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 400)
        self.table_mock.get_item.assert_not_called()

    def test_boolean_visibility_returns_400(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": True}),
            None,
        )
        self.assertEqual(resp["statusCode"], 400)

    def test_unknown_enum_returns_400(self):
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "SHARED"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 400)

    def test_missing_course_returns_404(self):
        self.table_mock.get_item.return_value = {}
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 404)
        self.table_mock.update_item.assert_not_called()

    def test_non_owner_returns_403(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item(owner_id="someone-else")}
        resp = update_course_visibility.lambda_handler(
            _auth_event(sub="owner-1", body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)
        self.table_mock.update_item.assert_not_called()

    def test_owner_private_to_public_sets_updated_at(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PRIVATE")}
        self.table_mock.update_item.return_value = {
            "Attributes": {
                "course_id": "c1",
                "visibility": "PUBLIC",
                "updated_at": "2026-08-30T15:12:00+00:00",
                "owner_id": "owner-1",
            }
        }
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC", "owner_id": "forged"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["course_id"], "c1")
        self.assertEqual(body["visibility"], "PUBLIC")
        self.assertEqual(body["updated_at"], "2026-08-30T15:12:00+00:00")
        kwargs = self.table_mock.update_item.call_args.kwargs
        self.assertIn("updated_at = :now", kwargs["UpdateExpression"])
        self.assertEqual(kwargs["ExpressionAttributeValues"][":v"], "PUBLIC")

    def test_owner_public_to_private(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PUBLIC")}
        self.table_mock.update_item.return_value = {
            "Attributes": {
                "course_id": "c1",
                "visibility": "PRIVATE",
                "updated_at": "2026-08-30T16:00:00+00:00",
            }
        }
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PRIVATE"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(json.loads(resp["body"])["visibility"], "PRIVATE")

    def test_idempotent_same_value_skips_update(self):
        item = _owner_item("PUBLIC", updated_at="2026-01-02T00:00:00+00:00")
        self.table_mock.get_item.return_value = {"Item": item}
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 200)
        self.table_mock.update_item.assert_not_called()
        body = json.loads(resp["body"])
        self.assertEqual(body["visibility"], "PUBLIC")
        self.assertEqual(body["updated_at"], "2026-01-02T00:00:00+00:00")

    def test_idempotent_missing_updated_at_returns_null(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PRIVATE")}
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PRIVATE"}),
            None,
        )
        body = json.loads(resp["body"])
        self.assertIsNone(body["updated_at"])
        self.table_mock.update_item.assert_not_called()

    def test_response_keys_whitelisted(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PRIVATE")}
        self.table_mock.update_item.return_value = {
            "Attributes": {
                "course_id": "c1",
                "visibility": "PUBLIC",
                "updated_at": "2026-08-30T15:12:00+00:00",
                "owner_id": "owner-1",
                "description": "secret",
            }
        }
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        body = json.loads(resp["body"])
        self.assertEqual(set(body.keys()), {"course_id", "visibility", "updated_at"})

    def test_created_at_backfill_only_when_missing(self):
        self.table_mock.get_item.return_value = {
            "Item": _owner_item("PRIVATE", created_at=None)
        }
        self.table_mock.update_item.return_value = {
            "Attributes": {
                "course_id": "c1",
                "visibility": "PUBLIC",
                "updated_at": "now",
                "created_at": "now",
            }
        }
        update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        kwargs = self.table_mock.update_item.call_args.kwargs
        self.assertIn("created_at = :now", kwargs["UpdateExpression"])
        self.assertNotIn("created_at = :created_at", kwargs.get("ConditionExpression", ""))

    def test_created_at_not_overwritten_when_present(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PRIVATE")}
        self.table_mock.update_item.return_value = {
            "Attributes": {
                "course_id": "c1",
                "visibility": "PUBLIC",
                "updated_at": "now",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        }
        update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        kwargs = self.table_mock.update_item.call_args.kwargs
        self.assertNotIn("created_at = :now", kwargs["UpdateExpression"])
        self.assertEqual(
            kwargs["ExpressionAttributeValues"][":created_at"],
            "2026-01-01T00:00:00+00:00",
        )

    def test_conditional_check_failed_returns_404(self):
        self.table_mock.get_item.return_value = {"Item": _owner_item("PRIVATE")}
        self.table_mock.update_item.side_effect = _client_error("ConditionalCheckFailedException")
        resp = update_course_visibility.lambda_handler(
            _auth_event(body={"visibility": "PUBLIC"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 404)

    def test_dynamodb_boom_returns_500_without_leak(self):
        self.table_mock.get_item.side_effect = RuntimeError("boom")
        with patch.object(update_course_visibility.logger, "exception") as log_mock:
            resp = update_course_visibility.lambda_handler(
                _auth_event(body={"visibility": "PUBLIC"}),
                None,
            )
        self.assertEqual(resp["statusCode"], 500)
        body = json.loads(resp["body"])
        self.assertEqual(body, {"message": "Internal server error"})
        self.assertNotIn("error", body)
        self.assertNotIn("boom", resp["body"])
        log_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
