import json
import os

import boto3
from boto3.dynamodb.conditions import Key


COURSES_TABLE = os.environ["COURSES_TABLE"]
DOCUMENTS_TABLE = os.environ["DOCUMENTS_TABLE"]
UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]
INDEX_NAME = os.environ["INDEX_NAME"]

_dynamodb = boto3.resource("dynamodb")
_courses_table = _dynamodb.Table(COURSES_TABLE)
_documents_table = _dynamodb.Table(DOCUMENTS_TABLE)
_s3 = boto3.client("s3")

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
        sub = claims.get("sub")
        if not sub:
            return _response(401, {"message": "Unauthorized: missing user identity"})

        course_id = event.get("pathParameters", {}).get("courseId")
        if not course_id:
            return _response(400, {"message": "Missing path parameter: courseId"})

        course_result = _courses_table.get_item(Key={"course_id": course_id})
        course_item = course_result.get("Item")
        if not course_item:
            return _response(404, {"message": "Course not found"})

        if course_item.get("owner_id") != sub:
            return _response(403, {"message": "Forbidden"})

        docs_result = _documents_table.query(
            IndexName=INDEX_NAME,
            KeyConditionExpression=Key("course_id").eq(course_id),
        )
        documents = docs_result.get("Items", [])

        for doc in documents:
            document_id = doc.get("document_id")
            s3_raw_key = doc.get("s3_raw_key")
            if not document_id or not s3_raw_key:
                return _response(
                    500,
                    {"message": "Failed to delete course assets due to invalid document metadata"},
                )

            try:
                _s3.delete_object(Bucket=UPLOAD_BUCKET, Key=s3_raw_key)
                _documents_table.delete_item(Key={"document_id": document_id})
                # TODO: When Textract pipeline artifacts are added, also delete processed outputs here.
            except Exception as exc:
                # Keep the course record when any child cleanup fails, so users can retry safely.
                return _response(
                    500,
                    {
                        "message": "Failed to fully delete course documents. Please retry.",
                        "error": str(exc),
                    },
                )

        _courses_table.delete_item(Key={"course_id": course_id})
        return _response(200, {"message": "Course deleted successfully"})
    except Exception as exc:
        return _response(500, {"message": "Internal server error", "error": str(exc)})
