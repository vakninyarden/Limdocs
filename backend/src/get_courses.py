import json
import os

import boto3
from boto3.dynamodb.conditions import Key


COURSES_TABLE = os.environ["COURSES_TABLE"]
INDEX_NAME = os.environ["INDEX_NAME"]
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
        authenticated_user_id = claims.get("sub")
        if not authenticated_user_id:
            return _response(401, {"message": "Unauthorized: missing user identity"})

        requested_user_id = event.get("pathParameters", {}).get("userId")
        if not requested_user_id:
            return _response(400, {"message": "Missing path parameter: userId"})

        if authenticated_user_id != requested_user_id:
            return _response(403, {"message": "Forbidden: cannot access other users' courses"})

        query_result = _table.query(
            IndexName=INDEX_NAME,
            KeyConditionExpression=Key("owner_id").eq(requested_user_id),
        )
        items = query_result.get("Items", [])

        return _response(200, {"courses": items})
    except Exception as exc:
        return _response(500, {"message": "Internal server error", "error": str(exc)})
