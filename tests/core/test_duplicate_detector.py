# tests/core/test_duplicate_detector.py
import unittest
from dupliscan.core.models import FileInfo, DuplicateGroup
from dupliscan.core.duplicate_detector import find_duplicates

class TestDuplicateDetector(unittest.TestCase):

    def test_find_duplicates_none(self):
        files = [
            FileInfo(path="f1", size=10, hash_sha256="h1"),
            FileInfo(path="f2", size=10, hash_sha256="h2"),
        ]
        self.assertEqual(find_duplicates(files), [])

    def test_find_duplicates_one_set(self):
        f1 = FileInfo(path="f1", size=10, hash_sha256="h1")
        f2 = FileInfo(path="f2", size=10, hash_sha256="h2")
        f3 = FileInfo(path="f3", size=10, hash_sha256="h1")
        files = [f1, f2, f3]

        result = find_duplicates(files)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "h1")
        self.assertEqual(result[0].files, {f1, f3})

    def test_find_duplicates_multiple_sets(self):
        f1 = FileInfo(path="f1", size=10, hash_sha256="h1")
        f2 = FileInfo(path="f2", size=10, hash_sha256="h2")
        f3 = FileInfo(path="f3", size=10, hash_sha256="h1")
        f4 = FileInfo(path="f4", size=10, hash_sha256="h2")
        f5 = FileInfo(path="f5", size=10, hash_sha256="h3")
        files = [f1, f2, f3, f4, f5]

        result = find_duplicates(files)
        self.assertEqual(len(result), 2) # h1 and h2 are duplicates

        # Check group h1
        group_h1 = next((g for g in result if g.id == "h1"), None)
        self.assertIsNotNone(group_h1)
        self.assertEqual(group_h1.files, {f1, f3})

        # Check group h2
        group_h2 = next((g for g in result if g.id == "h2"), None)
        self.assertIsNotNone(group_h2)
        self.assertEqual(group_h2.files, {f2, f4})

    def test_find_duplicates_with_none_hash(self):
        files = [
            FileInfo(path="f1", size=10, hash_sha256="h1"),
            FileInfo(path="f2", size=10, hash_sha256=None), # No hash
            FileInfo(path="f3", size=10, hash_sha256="h1"),
        ]
        result = find_duplicates(files)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "h1")

if __name__ == '__main__':
    unittest.main()
