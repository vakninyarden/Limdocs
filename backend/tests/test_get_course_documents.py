import json
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("DOCUMENTS_TABLE", "documents")
os.environ.setdefault("INDEX_NAME", "CourseIdIndex")

import get_course_documents  # noqa: E402


def _auth_event(sub="owner-1", course_id="c1"):
    return {
        "httpMethod": "GET",
        "pathParameters": {"courseId": course_id} if course_id is not None else None,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": sub} if sub is not None else {},
            },
        },
    }


def _full_document():
    return {
        "document_id": "d1",
        "original_file_name": "notes.pdf",
        "created_at": "2026-01-01T00:00:00+00:00",
        "processing_status": "READY",
        "topics": [{"en": "OS", "he": "מערכות הפעלה"}],
        "s3_raw_key": "uploads/raw",
        "s3_processed_key": "processed/out",
        "uploader_user_name": "alice",
        "course_id": "c1",
    }


class GetCourseDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.courses_mock = MagicMock()
        self.docs_mock = MagicMock()
        get_course_documents._courses_table = self.courses_mock
        get_course_documents._table = self.docs_mock

    def test_owner_returns_full_items(self):
        self.courses_mock.get_item.return_value = {
            "Item": {"course_id": "c1", "owner_id": "owner-1", "visibility": "PRIVATE"}
        }
        self.docs_mock.query.return_value = {"Items": [_full_document()]}
        resp = get_course_documents.lambda_handler(_auth_event(), None)
        self.assertEqual(resp["statusCode"], 200)
        doc = json.loads(resp["body"])["documents"][0]
        self.assertEqual(doc["document_id"], "d1")
        self.assertEqual(doc["original_file_name"], "notes.pdf")
        self.assertEqual(doc["created_at"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(doc["processing_status"], "READY")
        self.assertEqual(doc["topics"], [{"en": "OS", "he": "מערכות הפעלה"}])
        self.assertEqual(doc["s3_raw_key"], "uploads/raw")

    def test_visitor_public_filename_only_whitelist(self):
        self.courses_mock.get_item.return_value = {
            "Item": {"course_id": "c1", "owner_id": "owner-1", "visibility": "PUBLIC"}
        }
        self.docs_mock.query.return_value = {"Items": [_full_document()]}
        resp = get_course_documents.lambda_handler(_auth_event(sub="visitor"), None)
        self.assertEqual(resp["statusCode"], 200)
        doc = json.loads(resp["body"])["documents"][0]
        self.assertEqual(set(doc.keys()), {"document_id", "original_file_name"})
        self.assertEqual(doc["document_id"], "d1")
        self.assertEqual(doc["original_file_name"], "notes.pdf")
        for forbidden in (
            "created_at",
            "processing_status",
            "topics",
            "s3_raw_key",
            "s3_processed_key",
            "uploader_user_name",
            "course_id",
        ):
            self.assertNotIn(forbidden, doc)

    def test_non_owner_private_returns_403(self):
        self.courses_mock.get_item.return_value = {
            "Item": {"course_id": "c1", "owner_id": "owner-1", "visibility": "PRIVATE"}
        }
        resp = get_course_documents.lambda_handler(_auth_event(sub="visitor"), None)
        self.assertEqual(resp["statusCode"], 403)
        self.docs_mock.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
