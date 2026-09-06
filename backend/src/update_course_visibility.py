import base64
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from course_access import ACCESS_OWNER, resolve_course_access

COURSES_TABLE = os.environ["COURSES_TABLE"]
_ALLOWED_VISIBILITY = frozenset({"PUBLIC", "PRIVATE"})

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(COURSES_TABLE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_CORS_ALLOW_HEADERS = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
_CORS_ALLOW_METHODS = "PATCH,OPTIONS"


def _response(status_code, payload, allow_methods=_CORS_ALLOW_METHODS):
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


def _public_payload(item):
    return {
        "course_id": item.get("course_id"),
        "visibility": item.get("visibility"),
        "updated_at": item.get("updated_at"),
    }


def _parse_body(event):
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded", False):
        raw_body = base64.b64decode(raw_body).decode("utf-8")
    body = json.loads(raw_body)
    if not isinstance(body, dict):
        raise ValueError("invalid body")
    return body


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
        sub = claims.get("sub")
        if not sub:
            return _response(401, {"message": "Unauthorized: missing user identity"})

        course_id = (event.get("pathParameters") or {}).get("courseId")
        if not course_id:
            return _response(400, {"message": "Missing path parameter: courseId"})

        try:
            body = _parse_body(event)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return _response(400, {"message": "Invalid JSON in request body"})

        visibility = body.get("visibility")
        if visibility not in _ALLOWED_VISIBILITY:
            return _response(400, {"message": "Field 'visibility' must be PUBLIC or PRIVATE"})

        mode, payload = resolve_course_access(_table, course_id, sub)
        if mode != ACCESS_OWNER:
            if mode is None:
                status, body = payload
                return _response(status, body)
            return _response(403, {"message": "Forbidden"})
        item = payload

        if item.get("visibility") == visibility:
            return _response(200, _public_payload(item))

        now = datetime.now(timezone.utc).isoformat()
        existing_created_at = item.get("created_at")
        needs_created_at = not isinstance(existing_created_at, str) or not existing_created_at.strip()

        update_names = ["visibility = :v", "updated_at = :now"]
        expr_values = {":v": visibility, ":now": now, ":sub": sub}
        condition_parts = ["attribute_exists(course_id)", "owner_id = :sub"]

        if needs_created_at:
            update_names.append("created_at = :now")
        else:
            condition_parts.append("created_at = :created_at")
            expr_values[":created_at"] = existing_created_at

        updated = _table.update_item(
            Key={"course_id": course_id},
            UpdateExpression="SET " + ", ".join(update_names),
            ConditionExpression=" AND ".join(condition_parts),
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        new_item = updated.get("Attributes") or {}
        return _response(200, _public_payload(new_item))
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return _response(404, {"message": "Course not found"})
        logger.exception("update_course_visibility failed")
        return _response(500, {"message": "Internal server error"})
    except Exception:
        logger.exception("update_course_visibility failed")
        return _response(500, {"message": "Internal server error"})
