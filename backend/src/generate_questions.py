import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3

DOCUMENTS_TABLE = os.environ["DOCUMENTS_TABLE"]
QUESTIONS_TABLE = os.environ["QUESTIONS_TABLE"]
QUESTION_SETS_TABLE = os.environ["QUESTION_SETS_TABLE"]
PROCESSED_BUCKET = os.environ["PROCESSED_BUCKET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL_NAME = os.environ["OPENAI_MODEL_NAME"]

_MAX_SOURCE_CHARS = 12000
_ALLOWED_DIFFICULTIES = {"Easy", "Medium", "Hard"}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
_documents_table = _dynamodb.Table(DOCUMENTS_TABLE)
_questions_table = _dynamodb.Table(QUESTIONS_TABLE)
_question_sets_table = _dynamodb.Table(QUESTION_SETS_TABLE)

_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
}

_SYSTEM_PROMPT = (
    "You are an expert academic assistant. Generate 5 high-quality multiple-choice "
    "questions in Hebrew based on the provided text. Categorize each question with "
    "relevant topics and assign difficulty as Easy, Medium, or Hard based on the "
    "academic depth of the text. Ensure at least 1-2 questions synthesize or compare "
    "information across multiple provided documents. Return ONLY a valid JSON array of objects."
)


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": _CORS_HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _clean_model_json(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text


def _truncate_source_text(text):
    if len(text) <= _MAX_SOURCE_CHARS:
        return text
    return text[:_MAX_SOURCE_CHARS]


def _allocate_budgets(texts, total_budget):
    if not texts or total_budget <= 0:
        return [0 for _ in texts]

    budgets = [0] * len(texts)
    remaining_budget = total_budget
    remaining_indexes = list(range(len(texts)))

    while remaining_indexes and remaining_budget > 0:
        share = max(1, remaining_budget // len(remaining_indexes))
        next_indexes = []
        for idx in remaining_indexes:
            remaining_len = max(0, len(texts[idx]) - budgets[idx])
            take = min(share, remaining_len, remaining_budget)
            budgets[idx] += take
            remaining_budget -= take
            if budgets[idx] < len(texts[idx]) and remaining_budget > 0:
                next_indexes.append(idx)
            if remaining_budget <= 0:
                break
        remaining_indexes = next_indexes

    return budgets


def _build_balanced_context(texts):
    budgets = _allocate_budgets(texts, _MAX_SOURCE_CHARS)
    parts = [texts[idx][:budgets[idx]] for idx in range(len(texts)) if budgets[idx] > 0]
    return "\n\n".join(parts), budgets


def _normalize_question(item):
    if not isinstance(item, dict):
        return None

    question = item.get("question")
    options = item.get("options")
    correct_index = item.get("correct_index")
    explanation = item.get("explanation")
    topics = item.get("topics")
    difficulty = item.get("difficulty")

    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(explanation, str) or not explanation.strip():
        return None
    if not isinstance(options, list) or len(options) != 4:
        return None
    if any(not isinstance(opt, str) or not opt.strip() for opt in options):
        return None
    if not isinstance(correct_index, int) or correct_index < 0 or correct_index > 3:
        return None
    if not isinstance(topics, list) or any(not isinstance(topic, str) or not topic.strip() for topic in topics):
        return None
    if not isinstance(difficulty, str) or difficulty not in _ALLOWED_DIFFICULTIES:
        return None

    return {
        "question": question.strip(),
        "options": [opt.strip() for opt in options],
        "correct_index": correct_index,
        "explanation": explanation.strip(),
        "topics": [topic.strip() for topic in topics if topic.strip()],
        "difficulty": difficulty,
    }


def _parse_valid_questions(raw_response):
    cleaned = _clean_model_json(raw_response)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise ValueError("Model response must be a JSON array")

    valid = []
    discarded = 0
    for item in parsed:
        normalized = _normalize_question(item)
        if normalized is None:
            discarded += 1
            continue
        valid.append(normalized)
    return valid, discarded


def lambda_handler(event, context):
    del context
    try:
        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )
        if not claims.get("sub"):
            return _response(401, {"message": "Unauthorized: missing user identity"})

        path_parameters = event.get("pathParameters", {})
        course_id = path_parameters.get("courseId")
        if not course_id:
            return _response(400, {"message": "Missing path parameter: courseId"})

        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded", False):
            import base64
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        body = json.loads(raw_body)

        document_ids = body.get("documentIds")
        if not isinstance(document_ids, list) or not document_ids:
            return _response(400, {"message": "Field 'documentIds' must be a non-empty list"})
        if any(not isinstance(doc_id, str) or not doc_id.strip() for doc_id in document_ids):
            return _response(400, {"message": "Field 'documentIds' must contain non-empty strings"})

        normalized_document_ids = [doc_id.strip() for doc_id in document_ids]

        source_texts = []
        for document_id in normalized_document_ids:
            result = _documents_table.get_item(Key={"document_id": document_id})
            item = result.get("Item")
            if not item:
                return _response(404, {"message": f"Document not found: {document_id}"})

            if item.get("course_id") != course_id:
                return _response(403, {"message": f"Forbidden for document: {document_id}"})

            processed_key = item.get("s3_processed_key")
            if not processed_key:
                return _response(400, {"message": f"Document is not processed yet: {document_id}"})

            try:
                s3_obj = _s3.get_object(Bucket=PROCESSED_BUCKET, Key=processed_key)
                source_text = s3_obj["Body"].read().decode("utf-8", errors="replace")
                source_texts.append(source_text)
            except Exception:
                logger.exception(
                    "Failed reading processed text from S3 for document_id=%s key=%s",
                    document_id,
                    processed_key,
                )
                return _response(500, {"message": "Failed to load processed document text"})

        input_text, budgets = _build_balanced_context(source_texts)
        logger.info(
            "Built balanced context documents=%s total_input_len=%s budgets=%s",
            len(normalized_document_ids),
            len(input_text),
            budgets,
        )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=OPENAI_API_KEY)
            completion = client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": input_text},
                ],
                temperature=0.2,
            )
            raw_response = completion.choices[0].message.content or ""
            valid_questions, discarded_count = _parse_valid_questions(raw_response)
        except Exception:
            logger.exception(
                "OpenAI generation/parsing failed for document_ids=%s model=%s",
                normalized_document_ids,
                OPENAI_MODEL_NAME,
            )
            return _response(502, {"message": "Failed generating questions from AI response"})

        logger.info(
            "AI generation complete for document_ids=%s valid=%s discarded=%s",
            normalized_document_ids,
            len(valid_questions),
            discarded_count,
        )
        if not valid_questions:
            return _response(
                422,
                {"message": "AI response contained no valid questions"},
            )

        set_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        _question_sets_table.put_item(
            Item={
                "set_id": set_id,
                "document_ids": normalized_document_ids,
                "course_id": course_id,
                "title": f"Combined Quiz - {len(normalized_document_ids)} Materials",
                "created_at": created_at,
            }
        )

        with _questions_table.batch_writer() as batch:
            for question in valid_questions:
                batch.put_item(
                    Item={
                        "question_id": str(uuid4()),
                        "set_id": set_id,
                        "question": question["question"],
                        "options": question["options"],
                        "correct_index": question["correct_index"],
                        "explanation": question["explanation"],
                        "topics": question["topics"],
                        "difficulty": question["difficulty"],
                    }
                )

        for document_id in normalized_document_ids:
            result = _documents_table.get_item(Key={"document_id": document_id})
            existing_item = result.get("Item", {})
            if existing_item.get("processing_status") == "GENERATED":
                logger.info("Document already GENERATED document_id=%s", document_id)
                continue
            _documents_table.update_item(
                Key={"document_id": document_id},
                UpdateExpression="SET processing_status = :status",
                ExpressionAttributeValues={":status": "GENERATED"},
            )

        logger.info(
            "Persisted question set document_ids=%s set_id=%s inserted=%s",
            normalized_document_ids,
            set_id,
            len(valid_questions),
        )
        return _response(
            200,
            {
                "message": "Questions generated successfully",
                "set_id": set_id,
                "course_id": course_id,
                "documents_processed": len(normalized_document_ids),
                "inserted_questions": len(valid_questions),
                "discarded_questions": discarded_count,
            },
        )
    except Exception as exc:
        logger.exception("Unhandled error in generate_questions for event")
        return _response(500, {"message": "Internal server error", "error": str(exc)})
