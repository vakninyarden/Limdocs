import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DOCUMENTS_TABLE", "documents")
os.environ.setdefault("QUESTIONS_TABLE", "questions")
os.environ.setdefault("QUESTION_SETS_TABLE", "question_sets")
os.environ.setdefault("COURSES_TABLE", "courses")
os.environ.setdefault("PROCESSED_BUCKET", "processed")
os.environ.setdefault("USER_PROGRESS_TABLE", "user_progress")

from generate_questions import (
    _build_question_response_schema,
    _build_system_prompt,
    _evidence_is_in_source,
    _language_instruction_block,
    _normalize_evidence_text,
    _normalize_question,
    _parse_api_request,
    _parse_valid_questions,
    _question_set_generation_metadata,
    _resolve_weak_topic_focus,
    _verify_questions_source_evidence,
)
from openai_helpers import build_canonical_topic_lookup

# Copied from _generate_questions_worker batch.put_item keys.
_QUESTION_PERSIST_FIELDS = (
    "question_id",
    "set_id",
    "question",
    "options",
    "correct_index",
    "explanation",
    "topics",
    "difficulty",
)


def _raw_question(**overrides):
    item = {
        "question": "What is a stack?",
        "options": ["LIFO", "FIFO", "Graph", "Tree"],
        "correct_index": 0,
        "explanation": "A stack is last-in, first-out.",
        "topics": ["Algorithms"],
        "difficulty": "Easy",
        "answer": "LIFO",
        "source_evidence": "A stack is a last-in, first-out data structure.",
    }
    item.update(overrides)
    return item


def _normalized_question(**overrides):
    lookup = build_canonical_topic_lookup(["Algorithms"])
    normalized = _normalize_question(_raw_question(**overrides), canonical_lookup=lookup)
    return normalized


def _persist_item(question, question_id="q-1", set_id="set-1"):
    return {
        "question_id": question_id,
        "set_id": set_id,
        "question": question["question"],
        "options": question["options"],
        "correct_index": question["correct_index"],
        "explanation": question["explanation"],
        "topics": question["topics"],
        "difficulty": question["difficulty"],
    }


def _api_event(body, sub="user-123"):
    return {
        "requestContext": {"authorizer": {"claims": {"sub": sub}}},
        "pathParameters": {"courseId": "course-1"},
        "body": json.dumps(body),
    }


class ParseFocusWeakTopicsTests(unittest.TestCase):
    def test_missing_flag_defaults_false(self):
        parsed, err = _parse_api_request(_api_event({"documentIds": ["d1"]}))
        self.assertIsNone(err)
        self.assertFalse(parsed["focus_weak_topics"])

    def test_true_flag(self):
        parsed, err = _parse_api_request(
            _api_event(
                {
                    "documentIds": ["d1"],
                    "requested_question_count": 5,
                    "quiz_language": "he",
                    "focus_weak_topics": True,
                }
            )
        )
        self.assertIsNone(err)
        self.assertTrue(parsed["focus_weak_topics"])

    def test_invalid_type_returns_400(self):
        _, err = _parse_api_request(
            _api_event({"documentIds": ["d1"], "focus_weak_topics": "yes"})
        )
        self.assertIsNotNone(err)
        self.assertEqual(err["statusCode"], 400)


class WeakFocusResolverTests(unittest.TestCase):
    @patch("generate_questions._dynamodb")
    def test_applied_only_with_canonical_overlap(self, mock_dynamodb):
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "matrix": {
                    "Algorithms": {"Hard": {"correct": 0, "total": 2}},
                    "Other": {"Hard": {"correct": 0, "total": 2}},
                }
            }
        }
        lookup = build_canonical_topic_lookup(["Algorithms"])
        result = _resolve_weak_topic_focus(
            "user-1", "course-1", lookup, "cid-test"
        )
        self.assertTrue(result["progress_found"])
        self.assertTrue(result["applied_focus_weak_topics"])
        self.assertEqual(result["prioritized_weak_topics"], ["Algorithms"])
        self.assertEqual(result["weak_count_before_intersection"], 2)
        self.assertEqual(result["weak_count_after_intersection"], 1)

    @patch("generate_questions._dynamodb")
    def test_no_overlap_not_applied(self, mock_dynamodb):
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "matrix": {
                    "Unrelated": {"Hard": {"correct": 0, "total": 2}},
                }
            }
        }
        lookup = build_canonical_topic_lookup(["Algorithms"])
        result = _resolve_weak_topic_focus(
            "user-1", "course-1", lookup, "cid-test"
        )
        self.assertTrue(result["progress_found"])
        self.assertFalse(result["applied_focus_weak_topics"])
        self.assertEqual(result["prioritized_weak_topics"], [])


class SystemPromptWeakFocusTests(unittest.TestCase):
    def test_standard_prompt_without_weak_block(self):
        prompt = _build_system_prompt(["Algorithms"], 5, "he")
        self.assertNotIn("WEAK-TOPIC PRIORITY", prompt)
        self.assertNotIn("60", prompt)
        self.assertIn("SOURCE EVIDENCE (STRICT)", prompt)
        self.assertIn("source_evidence (string)", prompt)

    def test_weak_block_when_topics_provided(self):
        prompt = _build_system_prompt(
            ["Algorithms", "Data Structures"],
            10,
            "en",
            prioritized_weak_topics=["Algorithms"],
        )
        self.assertIn("WEAK-TOPIC PRIORITY", prompt)
        self.assertIn("60", prompt)
        self.assertIn("70", prompt)
        self.assertIn("Algorithms", prompt)
        self.assertIn("SOURCE EVIDENCE (STRICT)", prompt)
        self.assertIn("source_evidence (string)", prompt)

    def test_language_block_does_not_require_translated_evidence(self):
        he_block = _language_instruction_block("he")
        en_block = _language_instruction_block("en")
        self.assertNotIn("source_evidence", he_block)
        self.assertNotIn("source_evidence", en_block)
        he_prompt = _build_system_prompt(["Algorithms"], 5, "he")
        language_section = he_prompt.split("TOPIC CONSTRAINT", 1)[0]
        self.assertIn("LANGUAGE (STRICT)", language_section)
        self.assertNotIn("source_evidence", language_section)


class QuestionSetMetadataTests(unittest.TestCase):
    def test_normal_when_not_applied(self):
        meta = _question_set_generation_metadata(False, [])
        self.assertEqual(meta, {"generation_mode": "NORMAL"})
        self.assertNotIn("focused_topics", meta)

    def test_weakness_focused_with_topics(self):
        meta = _question_set_generation_metadata(
            True, ["Algorithms", "Graphs"]
        )
        self.assertEqual(meta["generation_mode"], "WEAKNESS_FOCUSED")
        self.assertEqual(meta["focused_topics"], ["Algorithms", "Graphs"])


class SourceEvidenceNormalizationTests(unittest.TestCase):
    def test_english_excerpt_is_in_source(self):
        source = "A stack is a last-in, first-out data structure used in compilers."
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last-in, first-out data structure",
                source,
            )
        )

    def test_hebrew_excerpt_is_in_source(self):
        source = "מחסנית היא מבנה נתונים מסוג נכנס אחרון יוצא ראשון."
        self.assertTrue(
            _evidence_is_in_source("מחסנית היא מבנה נתונים", source)
        )

    def test_extra_whitespace_and_newlines_match(self):
        source = "A stack is a last-in, first-out data structure."
        self.assertTrue(
            _evidence_is_in_source(
                "  A stack   is a last-in,\nfirst-out\r\n data structure.  ",
                source,
            )
        )

    def test_nbsp_and_doubled_newlines_match(self):
        source = "A stack is a last-in,\n\nfirst-out data structure."
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last-in,\u00a0first-out data structure.",
                source,
            )
        )

    def test_absent_evidence_fails(self):
        self.assertFalse(
            _evidence_is_in_source(
                "Queues are first-in, first-out.",
                "A stack is a last-in, first-out data structure.",
            )
        )

    def test_empty_or_whitespace_evidence_fails(self):
        source = "A stack is a last-in, first-out data structure."
        self.assertFalse(_evidence_is_in_source("", source))
        self.assertFalse(_evidence_is_in_source("   \n\t  ", source))
        self.assertFalse(_evidence_is_in_source(None, source))

    def test_punctuation_quote_dash_and_case_variants_match(self):
        source = "A stack is a last-in, first-out data structure."
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last-in first-out data structure.",
                source,
            )
        )
        self.assertTrue(
            _evidence_is_in_source(
                "a STACK is a last-in, first-out data structure",
                source,
            )
        )
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last\u2013in, first-out data structure.",
                source,
            )
        )
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a \u201clast-in, first-out\u201d data structure.",
                source,
            )
        )

    def test_stitched_fragments_match(self):
        source = "A stack is a last-in, first-out data structure used in compilers."
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last-in, first-out data structure. ... used in compilers.",
                source,
            )
        )

    def test_close_same_language_reword_matches(self):
        source = "A stack is a last-in, first-out data structure."
        self.assertTrue(
            _evidence_is_in_source(
                "A stack is a last-in, first-out structure of data.",
                source,
            )
        )

    def test_hebrew_evidence_against_english_source_fails(self):
        self.assertFalse(
            _evidence_is_in_source(
                "מחסנית היא מבנה נתונים מסוג נכנס אחרון יוצא ראשון.",
                "A stack is a last-in, first-out data structure.",
            )
        )

    def test_loose_paraphrase_is_rejected(self):
        source = "A stack is a last-in, first-out data structure."
        self.assertFalse(
            _evidence_is_in_source(
                "Stacks store items so the newest one comes out first.",
                source,
            )
        )

    def test_non_string_normalizes_to_empty(self):
        self.assertEqual(_normalize_evidence_text(None), "")
        self.assertEqual(_normalize_evidence_text(12), "")

    def test_normalize_casefolds_and_maps_typography(self):
        self.assertEqual(
            _normalize_evidence_text("It\u2019s a \u201clast\u2013in\u201d \u2026 test"),
            "it's a \"last-in\" ... test",
        )

    def test_normalize_strips_hebrew_niqqud(self):
        with_niqqud = "\u05d1\u05bc\u05b0\u05e8\u05b5\u05d0\u05e9\u05b4\u05c1\u05d9\u05ea"
        without_niqqud = "\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea"
        self.assertEqual(_normalize_evidence_text(with_niqqud), without_niqqud)


class SourceEvidenceVerificationTests(unittest.TestCase):
    def test_all_questions_must_pass(self):
        source = "A stack is a last-in, first-out data structure."
        questions = [
            {"source_evidence": "A stack is a last-in, first-out data structure."},
            {"source_evidence": "Queues are first-in, first-out."},
        ]
        with self.assertRaises(ValueError) as ctx:
            _verify_questions_source_evidence(questions, source)
        self.assertIn("Question 1", str(ctx.exception))

    def test_missing_key_fails(self):
        with self.assertRaises(ValueError) as ctx:
            _verify_questions_source_evidence([{"question": "What is a stack?"}], "source")
        self.assertIn("missing source_evidence", str(ctx.exception))

    def test_empty_evidence_fails(self):
        with self.assertRaises(ValueError) as ctx:
            _verify_questions_source_evidence(
                [{"source_evidence": "   "}],
                "A stack is a last-in, first-out data structure.",
            )
        self.assertIn("empty source_evidence", str(ctx.exception))

    def test_valid_set_does_not_raise(self):
        source = "A stack is a last-in, first-out data structure."
        questions = [
            {"source_evidence": "A stack is a last-in, first-out data structure."},
        ]
        _verify_questions_source_evidence(questions, source)


class QuestionSchemaSourceEvidenceTests(unittest.TestCase):
    def test_schema_requires_source_evidence(self):
        schema = _build_question_response_schema(["Algorithms"], 5)
        item_schema = schema["schema"]["properties"]["questions"]["items"]
        self.assertIn("source_evidence", item_schema["required"])
        for field in (
            "question",
            "options",
            "correct_index",
            "explanation",
            "topics",
            "difficulty",
            "answer",
        ):
            self.assertIn(field, item_schema["required"])
        evidence_schema = item_schema["properties"]["source_evidence"]
        self.assertEqual(evidence_schema["type"], "string")
        self.assertEqual(evidence_schema["minLength"], 1)
        self.assertFalse(item_schema["additionalProperties"])
        self.assertFalse(schema["schema"]["additionalProperties"])
        self.assertTrue(schema["strict"])


class NormalizeAndParseSourceEvidenceTests(unittest.TestCase):
    def test_normalize_keeps_stripped_source_evidence(self):
        lookup = build_canonical_topic_lookup(["Algorithms"])
        normalized = _normalize_question(
            _raw_question(source_evidence="  A stack is a last-in, first-out data structure.  "),
            canonical_lookup=lookup,
        )
        self.assertEqual(
            normalized["source_evidence"],
            "A stack is a last-in, first-out data structure.",
        )
        self.assertEqual(
            set(normalized),
            {
                "question",
                "options",
                "correct_index",
                "explanation",
                "topics",
                "difficulty",
                "source_evidence",
            },
        )

    def test_normalize_keeps_application_fields_without_evidence(self):
        lookup = build_canonical_topic_lookup(["Algorithms"])
        raw = _raw_question()
        raw.pop("source_evidence")
        normalized = _normalize_question(raw, canonical_lookup=lookup)
        self.assertNotIn("source_evidence", normalized)
        self.assertEqual(
            set(normalized),
            {
                "question",
                "options",
                "correct_index",
                "explanation",
                "topics",
                "difficulty",
            },
        )
        self.assertNotIn("answer", normalized)

    def test_parse_valid_questions_keeps_structurally_valid_items_with_evidence(self):
        payload = json.dumps({"questions": [_raw_question()]})
        lookup = build_canonical_topic_lookup(["Algorithms"])
        valid, discarded, _ = _parse_valid_questions(payload, canonical_lookup=lookup)
        self.assertEqual(discarded, 0)
        self.assertEqual(len(valid), 1)
        self.assertEqual(
            valid[0]["source_evidence"],
            "A stack is a last-in, first-out data structure.",
        )

    def test_successful_verify_and_strip_matches_persist_shape(self):
        source = "A stack is a last-in, first-out data structure."
        questions = [_normalized_question()]
        _verify_questions_source_evidence(questions, source)
        for question in questions:
            question.pop("source_evidence", None)
        persisted = _persist_item(questions[0])
        self.assertEqual(set(persisted), set(_QUESTION_PERSIST_FIELDS))
        self.assertNotIn("source_evidence", persisted)
        self.assertNotIn("source_evidence", questions[0])
        self.assertNotIn("answer", persisted)


if __name__ == "__main__":
    unittest.main()
