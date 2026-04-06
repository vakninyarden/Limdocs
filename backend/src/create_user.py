import base64
import json
import os

import boto3


USERS_TABLE = os.environ["USERS_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(USERS_TABLE)

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
        if not user_id:
            return _response(401, {"message": "Unauthorized: missing user identity"})

        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded", False):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        body = json.loads(raw_body)

        email = body.get("email")
        username = body.get("username")
        first_name = body.get("first_name")
        last_name = body.get("last_name")
        if not email or not username or not first_name or not last_name:
            return _response(
                400,
                {
                    "message": (
                        "Fields 'email', 'username', 'first_name', and 'last_name' are required"
                    )
                },
            )

        _table.put_item(
            Item={
                "user_id": user_id,
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            }
        )

        return _response(
            200,
            {
                "message": "User created/updated successfully",
                "user": {
                    "user_id": user_id,
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            },
        )
    except json.JSONDecodeError:
        return _response(400, {"message": "Invalid JSON in request body"})
    except Exception as exc:
        return _response(500, {"message": "Internal server error", "error": str(exc)})
