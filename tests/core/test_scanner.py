# tests/core/test_scanner.py
import unittest
import os
import tempfile
import hashlib
import zipfile
from io import BytesIO

# Adjust import path based on where DupliScan's modules are relative to the test execution context
# Assuming tests are run from the project root directory.
from dupliscan.core.scanner import _calculate_sha256, _scan_single_zip_archive, _calculate_sha256_from_bytes, scan_directory_recursive
from dupliscan.core.models import FileInfo

class TestScanner(unittest.TestCase):

    def test_calculate_sha256_from_bytes(self):
        content = b"hello world"
        stream = BytesIO(content)
        expected_hash = hashlib.sha256(content).hexdigest()
        self.assertEqual(_calculate_sha256_from_bytes(stream), expected_hash)

    def test_calculate_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp: # Use 'wb' for bytes
            tmp.write(b"test content for hashing")
            tmp_path = tmp.name

        expected_hash = hashlib.sha256(b"test content for hashing").hexdigest()
        self.assertEqual(_calculate_sha256(tmp_path), expected_hash)
        os.remove(tmp_path)

    def test_scan_single_zip_archive(self):
        # Create a dummy zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("dir/file2.txt", "content2")

        # Save to a temporary actual file to pass its path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(zip_buffer.getvalue())
            tmp_zip_path = tmp_zip.name

        file_infos, errors = _scan_single_zip_archive(tmp_zip_path)

        self.assertEqual(len(errors), 0, f"Errors found: {errors}")
        self.assertEqual(len(file_infos), 2)

        paths_in_zip = sorted([fi.path for fi in file_infos])
        self.assertEqual(paths_in_zip, sorted(["file1.txt", "dir/file2.txt"]))

        for fi in file_infos:
            self.assertTrue(fi.is_in_zip)
            self.assertEqual(fi.zip_parent_path, tmp_zip_path)
            if fi.path == "file1.txt":
                self.assertEqual(fi.size, len(b"content1"))
                self.assertEqual(fi.hash_sha256, hashlib.sha256(b"content1").hexdigest())
            elif fi.path == "dir/file2.txt":
                self.assertEqual(fi.size, len(b"content2"))
                self.assertEqual(fi.hash_sha256, hashlib.sha256(b"content2").hexdigest())

        os.remove(tmp_zip_path)

    # Test for scan_directory_recursive is more of an integration test.
    # Mocking os.walk and os.path functions can be complex.
    # A simpler test could check its handling of a predefined small directory structure
    # if the test environment allows creating temp dirs and files easily.
    # For now, we'll skip a direct unit test of scan_directory_recursive due to fs interaction complexity
    # in this context, focusing on its helper _calculate_sha256 and _scan_single_zip_archive.

if __name__ == '__main__':
    unittest.main()
