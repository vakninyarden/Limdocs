import base64
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3


COURSES_TABLE = os.environ["COURSES_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(COURSES_TABLE)

_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
}


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": _CORS_HEADERS,
        "body": json.dumps(payload),
    }


def lambda_handler(event, context):
    del context
    try:
        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )
        user_id = claims.get("sub")
        owner_username = claims.get("cognito:username") or claims.get("username")
        if not user_id:
            return _response(401, {"message": "Unauthorized: missing user identity"})
        if not owner_username:
            return _response(401, {"message": "Unauthorized: missing username identity"})

        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded", False):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        body = json.loads(raw_body)

        course_name = body.get("course_name")
        description = body.get("description", "")
        is_public = bool(body.get("is_public", False))
        visibility = "PUBLIC" if is_public else "PRIVATE"
        if not course_name:
            return _response(400, {"message": "Field 'course_name' is required"})

        course_item = {
            "course_id": str(uuid4()),
            "owner_id": user_id,
            "owner_username": owner_username,
            "course_name": course_name,
            "visibility": visibility,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _table.put_item(Item=course_item)
        return _response(200, {"message": "Course created successfully", "course": course_item})
    except json.JSONDecodeError:
        return _response(400, {"message": "Invalid JSON in request body"})
    except Exception as exc:
        return _response(500, {"message": "Internal server error", "error": str(exc)})
