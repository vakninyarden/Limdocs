import json
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("DOCUMENTS_TABLE", "documents")
os.environ.setdefault("UPLOAD_BUCKET", "raw-bucket")
os.environ.setdefault("PROCESSED_BUCKET", "processed-bucket")
os.environ.setdefault("QUESTIONS_TABLE", "questions")
os.environ.setdefault("QUESTION_SETS_TABLE", "question_sets")
os.environ.setdefault("ATTEMPTS_TABLE", "attempts")
os.environ.setdefault("ATTEMPT_ANSWERS_TABLE", "attempt_answers")
os.environ.setdefault("USER_PROGRESS_TABLE", "user_progress")
os.environ.setdefault("WORKER_FUNCTION_NAME", "worker")

import delete_document  # noqa: E402
import generate_questions  # noqa: E402
import generate_upload_url  # noqa: E402
import get_attempt_answers  # noqa: E402
import get_course_attempts  # noqa: E402
import get_user_progress  # noqa: E402
import submit_attempt  # noqa: E402


PUBLIC_COURSE = {
    "course_id": "c1",
    "owner_id": "owner-1",
    "visibility": "PUBLIC",
    "course_name": "OS",
}


def _claims_event(sub, method, path, body=None):
    event = {
        "httpMethod": method,
        "pathParameters": path,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


class PublicCourseOwnerOnlyTests(unittest.TestCase):
    def setUp(self):
        self.courses_mock = MagicMock()
        self.courses_mock.get_item.return_value = {"Item": PUBLIC_COURSE}
        generate_upload_url._courses_table = self.courses_mock
        delete_document._courses_table = self.courses_mock
        generate_questions._courses_table = self.courses_mock
        submit_attempt._courses_table = self.courses_mock
        get_course_attempts._courses_table = self.courses_mock
        get_attempt_answers._courses_table = self.courses_mock
        get_user_progress._courses_table = self.courses_mock

    def test_upload_url_visitor_403(self):
        resp = generate_upload_url.lambda_handler(
            _claims_event(
                "visitor",
                "POST",
                {"courseId": "c1"},
                {"file_name": "a.pdf", "file_type": "application/pdf", "file_size_bytes": 10},
            ),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_delete_document_visitor_403(self):
        resp = delete_document.lambda_handler(
            _claims_event("visitor", "DELETE", {"courseId": "c1", "documentId": "d1"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_generate_quiz_visitor_403(self):
        context = MagicMock()
        context.aws_request_id = "cid-1"
        resp = generate_questions.api_handler(
            _claims_event("visitor", "POST", {"courseId": "c1"}, {"documentIds": ["d1"]}),
            context,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_submit_attempt_visitor_403(self):
        resp = submit_attempt.lambda_handler(
            _claims_event(
                "visitor",
                "POST",
                {"courseId": "c1", "setId": "s1"},
                {"answers": {"q1": 0}, "time_spent_seconds": 12},
            ),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_attempts_list_visitor_403(self):
        resp = get_course_attempts.lambda_handler(
            _claims_event("visitor", "GET", {"courseId": "c1"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_attempt_answers_visitor_403(self):
        resp = get_attempt_answers.lambda_handler(
            _claims_event("visitor", "GET", {"courseId": "c1", "attemptId": "a1"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_progress_visitor_403(self):
        resp = get_user_progress.lambda_handler(
            _claims_event("visitor", "GET", {"courseId": "c1"}),
            None,
        )
        self.assertEqual(resp["statusCode"], 403)


if __name__ == "__main__":
    unittest.main()
