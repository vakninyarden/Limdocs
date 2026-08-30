import json
import logging
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

COURSES_TABLE = os.environ["COURSES_TABLE"]
DOCUMENTS_TABLE = os.environ["DOCUMENTS_TABLE"]
VISIBILITY_INDEX_NAME = os.environ["VISIBILITY_INDEX_NAME"]
DOCUMENTS_COURSE_INDEX = os.environ["DOCUMENTS_COURSE_INDEX"]

_dynamodb = boto3.resource("dynamodb")
_courses_table = _dynamodb.Table(COURSES_TABLE)
_documents_table = _dynamodb.Table(DOCUMENTS_TABLE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_CORS_ALLOW_HEADERS = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"


def _response(status_code, payload, allow_methods="GET,OPTIONS"):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": allow_methods,
            "Access-Control-Allow-Headers": _CORS_ALLOW_HEADERS,
        },
        "body": json.dumps(payload),
    }


def _parse_iso_ms(value):
    if not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def _max_iso(*candidates):
    best = None
    best_ms = None
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        ms = _parse_iso_ms(candidate)
        if ms is None:
            continue
        if best_ms is None or ms > best_ms:
            best_ms = ms
            best = candidate
    return best


def _query_public_courses():
    params = {
        "IndexName": VISIBILITY_INDEX_NAME,
        "KeyConditionExpression": Key("visibility").eq("PUBLIC"),
        "ScanIndexForward": False,
    }
    items = []
    while True:
        result = _courses_table.query(**params)
        items.extend(result.get("Items", []))
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        params["ExclusiveStartKey"] = last_key
    return items


def _is_public(item):
    value = item.get("visibility")
    return isinstance(value, str) and value.strip() == "PUBLIC"


def _course_document_stats(course_id):
    params = {
        "IndexName": DOCUMENTS_COURSE_INDEX,
        "KeyConditionExpression": Key("course_id").eq(course_id),
        "ProjectionExpression": "#c, #u, #p",
        "ExpressionAttributeNames": {
            "#c": "created_at",
            "#u": "updated_at",
            "#p": "uploaded_at",
        },
    }
    count = 0
    latest_iso = None
    while True:
        result = _documents_table.query(**params)
        for item in result.get("Items", []):
            count += 1
            latest_iso = _max_iso(
                latest_iso,
                item.get("created_at"),
                item.get("updated_at"),
                item.get("uploaded_at"),
            )
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        params["ExclusiveStartKey"] = last_key
    return count, latest_iso


def _last_updated_at(course, docs_latest_iso):
    return _max_iso(course.get("updated_at"), docs_latest_iso, course.get("created_at"))


def _sanitize_public_course(course, user_sub, document_count, last_updated_at):
    return {
        "course_id": course.get("course_id"),
        "course_name": course.get("course_name"),
        "visibility": "PUBLIC",
        "is_owner": course.get("owner_id") == user_sub,
        "document_count": document_count,
        "last_updated_at": last_updated_at,
    }


def lambda_handler(event, context):
    del context
    try:
        method = (event.get("httpMethod") or "").upper()
        if method == "OPTIONS":
            return _response(200, {"message": "OK"})

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )
        user_sub = claims.get("sub")
        if not user_sub:
            return _response(401, {"message": "Unauthorized: missing user identity"})

        results = []
        for course in _query_public_courses():
            if not _is_public(course):
                continue
            course_id = course.get("course_id")
            if not course_id or not str(course_id).strip():
                continue
            doc_count, docs_latest = _course_document_stats(course_id)
            last_updated = _last_updated_at(course, docs_latest)
            results.append(
                _sanitize_public_course(course, user_sub, doc_count, last_updated)
            )

        return _response(200, {"courses": results})
    except Exception:
        logger.exception("get_public_courses failed")
        return _response(500, {"message": "Internal server error"})
