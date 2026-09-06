import json
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("QUESTION_SETS_TABLE", "question_sets")
os.environ.setdefault("QUESTIONS_TABLE", "questions")
os.environ.setdefault("QUESTION_SETS_COURSE_INDEX", "CourseIdCreatedAtIndex")
os.environ.setdefault("QUESTIONS_SET_INDEX", "SetIdIndex")

import get_questions  # noqa: E402


def _auth_event(sub="owner-1", course_id="c1", set_id=None, method="GET"):
    path = {"courseId": course_id} if course_id is not None else {}
    if set_id is not None:
        path["setId"] = set_id
    return {
        "httpMethod": method,
        "pathParameters": path or None,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }


def _public_course(owner_id="owner-1"):
    return {
        "course_id": "c1",
        "owner_id": owner_id,
        "visibility": "PUBLIC",
        "course_name": "OS",
    }


class GetQuestionsAccessTests(unittest.TestCase):
    def setUp(self):
        self.courses_mock = MagicMock()
        self.sets_mock = MagicMock()
        self.questions_mock = MagicMock()
        get_questions._courses_table = self.courses_mock
        get_questions._question_sets_table = self.sets_mock
        get_questions._questions_table = self.questions_mock

    def test_visitor_list_returns_200(self):
        self.courses_mock.get_item.return_value = {"Item": _public_course()}
        self.sets_mock.query.return_value = {
            "Items": [
                {
                    "set_id": "s1",
                    "name": "Quiz 1",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "question_count": 2,
                    "quiz_language": "he",
                    "generation_mode": "weakness",
                    "focused_topics": ["OS"],
                }
            ]
        }
        resp = get_questions.lambda_handler(_auth_event(sub="visitor"), None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(len(body["sets"]), 1)
        self.assertNotIn("generation_mode", body["sets"][0])
        self.assertNotIn("focused_topics", body["sets"][0])

    def test_visitor_detail_returns_200(self):
        self.courses_mock.get_item.return_value = {"Item": _public_course()}
        self.sets_mock.get_item.return_value = {
            "Item": {
                "set_id": "s1",
                "course_id": "c1",
                "name": "Quiz 1",
                "created_at": "2026-01-01T00:00:00+00:00",
                "question_count": 1,
                "generation_mode": "weakness",
                "focused_topics": ["OS"],
            }
        }
        self.questions_mock.query.return_value = {
            "Items": [
                {
                    "question_id": "q1",
                    "set_id": "s1",
                    "course_id": "c1",
                    "question": "What?",
                    "options": ["a", "b"],
                    "correct_index": 0,
                    "explanation": "Because",
                }
            ]
        }
        resp = get_questions.lambda_handler(
            _auth_event(sub="visitor", set_id="s1"),
            None,
        )
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertNotIn("generation_mode", body["set"])
        self.assertNotIn("focused_topics", body["set"])
        self.assertEqual(body["questions"][0]["correct_index"], 0)
        self.assertEqual(body["questions"][0]["explanation"], "Because")

    def test_visitor_delete_returns_403(self):
        self.courses_mock.get_item.return_value = {"Item": _public_course()}
        resp = get_questions.lambda_handler(
            _auth_event(sub="visitor", set_id="s1", method="DELETE"),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)
        self.sets_mock.delete_item.assert_not_called()

    def test_non_owner_private_get_returns_403(self):
        self.courses_mock.get_item.return_value = {
            "Item": {"course_id": "c1", "owner_id": "owner-1", "visibility": "PRIVATE"}
        }
        resp = get_questions.lambda_handler(_auth_event(sub="visitor"), None)
        self.assertEqual(resp["statusCode"], 403)
        self.sets_mock.query.assert_not_called()

    def test_owner_delete_still_allowed(self):
        self.courses_mock.get_item.return_value = {"Item": _public_course()}
        self.sets_mock.get_item.return_value = {
            "Item": {"set_id": "s1", "course_id": "c1"}
        }
        self.questions_mock.query.return_value = {
            "Items": [{"question_id": "q1", "set_id": "s1"}]
        }
        resp = get_questions.lambda_handler(
            _auth_event(sub="owner-1", set_id="s1", method="DELETE"),
            None,
        )
        self.assertEqual(resp["statusCode"], 200)
        self.sets_mock.delete_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
