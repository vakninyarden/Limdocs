"""Course access helpers for Cognito-authenticated API Lambdas (same src/ package)."""

ACCESS_OWNER = "owner"
ACCESS_PUBLIC_READ = "public_read"


def _is_public(item):
    value = item.get("visibility")
    return isinstance(value, str) and value.strip() == "PUBLIC"


def resolve_course_access(courses_table, course_id, user_sub):
    """
    Resolve caller access to a course.

    Returns (mode, item) when allowed: mode is ACCESS_OWNER or ACCESS_PUBLIC_READ.
    Returns (None, (http_status, body_dict)) for 404 missing course or 403 forbidden.
    """
    result = courses_table.get_item(Key={"course_id": course_id})
    item = result.get("Item")
    if not item:
        return (None, (404, {"message": "Course not found"}))
    if item.get("owner_id") == user_sub:
        return (ACCESS_OWNER, item)
    if _is_public(item):
        return (ACCESS_PUBLIC_READ, item)
    return (None, (403, {"message": "Forbidden"}))


def require_course_owner(courses_table, course_id, user_sub):
    """
    Returns None if user_sub owns the course.
    Otherwise returns (http_status, body_dict) for 404 missing course or 403 mismatch.
    Public visitors are always 403 (owner-only gate).
    """
    mode, payload = resolve_course_access(courses_table, course_id, user_sub)
    if mode == ACCESS_OWNER:
        return None
    if mode is None:
        return payload
    return (403, {"message": "Forbidden"})
