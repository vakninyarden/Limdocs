import json
import logging
import os

import boto3

from course_access import ACCESS_OWNER, resolve_course_access

COURSES_TABLE = os.environ["COURSES_TABLE"]

_dynamodb = boto3.resource("dynamodb")
_courses_table = _dynamodb.Table(COURSES_TABLE)

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


def _safe_visibility(item):
    value = item.get("visibility")
    if isinstance(value, str) and value.strip() == "PUBLIC":
        return "PUBLIC"
    return "PRIVATE"


def _sanitize_course(item, is_owner):
    return {
        "course_id": item.get("course_id"),
        "course_name": item.get("course_name"),
        "visibility": _safe_visibility(item),
        "is_owner": is_owner,
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

        course_id = (event.get("pathParameters") or {}).get("courseId")
        if not course_id:
            return _response(400, {"message": "Missing path parameter: courseId"})

        mode, payload = resolve_course_access(_courses_table, course_id, user_sub)
        if mode is None:
            status, body = payload
            return _response(status, body)

        return _response(200, _sanitize_course(payload, mode == ACCESS_OWNER))
    except Exception:
        logger.exception("get_course failed")
        return _response(500, {"message": "Internal server error"})
