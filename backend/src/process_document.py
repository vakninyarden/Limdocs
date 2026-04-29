import json
import logging
import os
import re
import time
from urllib.parse import unquote_plus

import boto3

DOCUMENTS_TABLE = os.environ["DOCUMENTS_TABLE"]
PROCESSED_BUCKET = os.environ["PROCESSED_BUCKET"]

_SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpeg", ".jpg"}
_BASENAME_DOC_ID_PATTERN = re.compile(
    r"^(?P<document_id>[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-"
    r"[0-9a-fA-F]{12})_.+"
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3 = boto3.client("s3")
_textract = boto3.client("textract")
_dynamodb = boto3.resource("dynamodb")
_documents_table = _dynamodb.Table(DOCUMENTS_TABLE)


def _extract_document_id(source_key):
    basename = source_key.split("/")[-1]
    match = _BASENAME_DOC_ID_PATTERN.match(basename)
    if match:
        return match.group("document_id")

    raise ValueError(f"Could not extract document_id from key: {source_key}")


def _mark_document_failed(document_id, reason):
    logger.error("Marking document as FAILED: %s", reason)
    if not document_id:
        return

    _documents_table.update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET processing_status = :status",
        ExpressionAttributeValues={":status": "FAILED"},
    )


def _collect_textract_lines(job_id):
    all_lines = []
    next_token = None

    while True:
        response = _textract.get_document_text_detection(
            JobId=job_id,
            NextToken=next_token,
        ) if next_token else _textract.get_document_text_detection(JobId=job_id)

        status = response.get("JobStatus")
        if status in ("FAILED", "PARTIAL_SUCCESS"):
            raise RuntimeError(f"Textract job failed with status: {status}")

        if status != "SUCCEEDED":
            logger.info("Textract job %s status: %s. Retrying in 5s.", job_id, status)
            time.sleep(5)
            continue

        blocks = response.get("Blocks", [])
        for block in blocks:
            if block.get("BlockType") == "LINE" and block.get("Text"):
                all_lines.append(block["Text"])

        next_token = response.get("NextToken")
        if not next_token:
            break

    return all_lines


def lambda_handler(event, context):
    del context
    logger.info("Received S3 event: %s", json.dumps(event))

    record = event["Records"][0]["s3"]
    source_bucket = record["bucket"]["name"]
    source_key = unquote_plus(record["object"]["key"])
    document_id = _extract_document_id(source_key)

    extension = os.path.splitext(source_key)[1].lower()
    if extension not in _SUPPORTED_EXTENSIONS:
        _mark_document_failed(
            document_id,
            f"Unsupported file extension '{extension}' for key '{source_key}'",
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Unsupported file type. Marked as FAILED.",
                    "document_id": document_id,
                    "source_key": source_key,
                }
            ),
        }

    try:
        start_response = _textract.start_document_text_detection(
            DocumentLocation={
                "S3Object": {
                    "Bucket": source_bucket,
                    "Name": source_key,
                }
            }
        )
        job_id = start_response["JobId"]
        logger.info("Started Textract job %s for key %s", job_id, source_key)

        extracted_lines = _collect_textract_lines(job_id)
        extracted_text = "\n".join(extracted_lines)

        processed_key = f"extracted_text/{document_id}.txt"
        _s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=processed_key,
            Body=extracted_text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

        logger.info("Updating document record using document_id=%s", document_id)
        _documents_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET processing_status = :s, s3_processed_key = :k",
            ConditionExpression="attribute_exists(document_id)",
            ExpressionAttributeValues={
                ":s": "EXTRACTED",
                ":k": processed_key,
            },
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Document processed successfully",
                    "document_id": document_id,
                    "processed_key": processed_key,
                }
            ),
        }
    except Exception as exc:
        logger.exception("Failed processing document_id=%s key=%s", document_id, source_key)
        try:
            _mark_document_failed(document_id, str(exc))
        except Exception:
            logger.exception("Failed to update DynamoDB failed status for %s", document_id)
        raise
