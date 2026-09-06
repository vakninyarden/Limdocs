import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from course_access import (  # noqa: E402
    ACCESS_OWNER,
    ACCESS_PUBLIC_READ,
    require_course_owner,
    resolve_course_access,
)


class CourseAccessTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()

    def _item(self, **extra):
        item = {
            "course_id": "c1",
            "owner_id": "owner-1",
            "course_name": "OS",
            "visibility": "PRIVATE",
        }
        item.update(extra)
        return item

    def test_owner_private_is_owner(self):
        self.table.get_item.return_value = {"Item": self._item(visibility="PRIVATE")}
        mode, item = resolve_course_access(self.table, "c1", "owner-1")
        self.assertEqual(mode, ACCESS_OWNER)
        self.assertEqual(item["course_id"], "c1")
        self.assertIsNone(require_course_owner(self.table, "c1", "owner-1"))

    def test_owner_public_is_owner(self):
        self.table.get_item.return_value = {"Item": self._item(visibility="PUBLIC")}
        mode, _item = resolve_course_access(self.table, "c1", "owner-1")
        self.assertEqual(mode, ACCESS_OWNER)
        self.assertIsNone(require_course_owner(self.table, "c1", "owner-1"))

    def test_non_owner_public_is_public_read(self):
        self.table.get_item.return_value = {"Item": self._item(visibility="PUBLIC")}
        mode, item = resolve_course_access(self.table, "c1", "visitor")
        self.assertEqual(mode, ACCESS_PUBLIC_READ)
        self.assertEqual(item["owner_id"], "owner-1")
        gate = require_course_owner(self.table, "c1", "visitor")
        self.assertEqual(gate, (403, {"message": "Forbidden"}))

    def test_public_with_surrounding_whitespace_is_public_read(self):
        self.table.get_item.return_value = {"Item": self._item(visibility=" PUBLIC ")}
        mode, _item = resolve_course_access(self.table, "c1", "visitor")
        self.assertEqual(mode, ACCESS_PUBLIC_READ)

    def test_non_owner_private_is_403(self):
        self.table.get_item.return_value = {"Item": self._item(visibility="PRIVATE")}
        mode, payload = resolve_course_access(self.table, "c1", "visitor")
        self.assertIsNone(mode)
        self.assertEqual(payload, (403, {"message": "Forbidden"}))
        self.assertEqual(
            require_course_owner(self.table, "c1", "visitor"),
            (403, {"message": "Forbidden"}),
        )

    def test_missing_course_is_404(self):
        self.table.get_item.return_value = {}
        mode, payload = resolve_course_access(self.table, "missing", "owner-1")
        self.assertIsNone(mode)
        self.assertEqual(payload, (404, {"message": "Course not found"}))
        self.assertEqual(
            require_course_owner(self.table, "missing", "owner-1"),
            (404, {"message": "Course not found"}),
        )


if __name__ == "__main__":
    unittest.main()
