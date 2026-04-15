import json
import os

import boto3
from boto3.dynamodb.conditions import Key


DOCUMENTS_TABLE = os.environ["DOCUMENTS_TABLE"]
INDEX_NAME = os.environ["INDEX_NAME"]
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(DOCUMENTS_TABLE)

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
        if not claims.get("sub"):
            return _response(401, {"message": "Unauthorized: missing user identity"})

        course_id = event.get("pathParameters", {}).get("courseId")
        if not course_id:
            return _response(400, {"message": "Missing path parameter: courseId"})

        query_result = _table.query(
            IndexName=INDEX_NAME,
            KeyConditionExpression=Key("course_id").eq(course_id),
        )
        items = query_result.get("Items", [])

        return _response(200, {"documents": items})
    except Exception as exc:
        return _response(500, {"message": "Internal server error", "error": str(exc)})
