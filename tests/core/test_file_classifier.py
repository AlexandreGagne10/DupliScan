# tests/core/test_file_classifier.py
import unittest
from unittest import mock # For mocking 'magic' module

from dupliscan.core.models import FileInfo
from dupliscan.core.file_classifier import classify_file, EXTENSION_TO_TYPE_MAP

class TestFileClassifier(unittest.TestCase):

    def test_classify_by_extension(self):
        # Test a few common extensions
        for ext, type_val in EXTENSION_TO_TYPE_MAP.items():
            if type_val == 'data': continue # Skip .json, .xml etc for this specific simple test

            # Create a dummy file path, does not need to exist for extension testing
            file_info = FileInfo(path=f"testfile{ext}", size=100, extension=ext)
            classify_file(file_info)
            self.assertEqual(file_info.file_type, type_val, f"Failed for extension {ext}")

    @mock.patch('dupliscan.core.file_classifier.magic')
    def test_classify_by_magic_image(self, mock_magic):
        mock_magic.from_file.return_value = "image/jpeg"
        # File with no extension, or an unknown one
        file_info = FileInfo(path="testfile_no_ext", size=100, extension=None)

        classify_file(file_info)

        mock_magic.from_file.assert_called_once_with(file_info.path, mime=True)
        self.assertEqual(file_info.file_type, "image")
        self.assertEqual(file_info.magic_number_details, "image/jpeg")

    @mock.patch('dupliscan.core.file_classifier.magic')
    def test_classify_by_magic_unknown_mime(self, mock_magic):
        mock_magic.from_file.return_value = "application/octet-stream"
        file_info = FileInfo(path="testfile_bin", size=100, extension=".bin") # unknown ext

        classify_file(file_info)
        self.assertEqual(file_info.file_type, "binary_unknown") # Default for octet-stream with unknown ext

        # Test octet-stream with a known extension (e.g. .exe)
        file_info_exe = FileInfo(path="testfile.exe", size=100, extension=".exe") # Known ext
        # Reset mock for the new call if needed, or ensure it's set up for this specific call if it behaves differently
        mock_magic.from_file.return_value = "application/octet-stream" # Ensure it's still this for the .exe case
        classify_file(file_info_exe)
        # Since .exe is in EXTENSION_TO_TYPE_MAP, it should be classified by extension first.
        # The provided code for classify_file prioritizes extension.
        # So, magic won't be called if extension is known.
        # Let's adjust the test to reflect that logic.

        # If extension is known, magic is not called.
        # So, for .exe, it should be 'executable' directly from map.
        file_info_exe_test = FileInfo(path="testfile.exe", size=100, extension=".exe")
        classify_file(file_info_exe_test)
        self.assertEqual(file_info_exe_test.file_type, "executable")
        mock_magic.from_file.assert_any_call("testfile_bin", mime=True) # this was from previous call
        # To ensure it was not called for file_info_exe_test, we'd need to check call count or reset mock.
        # For simplicity, this test focuses on the outcome for .bin (unknown) vs .exe (known by extension)

        # Let's test a case where extension is NOT in map, and magic returns octet-stream
        file_info_unknown_ext_octet = FileInfo(path="somefile.unk", size=100, extension=".unk")
        mock_magic.from_file.return_value = "application/octet-stream"
        classify_file(file_info_unknown_ext_octet)
        self.assertEqual(file_info_unknown_ext_octet.file_type, "binary_unknown")
        mock_magic.from_file.assert_called_with("somefile.unk", mime=True)


    @mock.patch('dupliscan.core.file_classifier.magic')
    def test_classify_magic_exception(self, mock_magic):
        # Ensure the mock is re-created or reset for this test method
        fresh_mock_magic = mock.Mock()
        fresh_mock_magic.from_file.side_effect = fresh_mock_magic.MagicException("Magic error")

        # Patch the magic object specifically for this test's scope if MagicException is part of magic module
        # This is tricky because MagicException in the file_classifier is imported from 'magic'
        # We need to make sure that the 'magic' module itself, when imported by file_classifier, has this MagicException
        # For this test, we assume that 'mock_magic.MagicException' will correctly be caught.
        # A better way would be to mock 'magic.MagicException' itself if it's a distinct class.
        # Let's assume 'magic.MagicException' is a type that can be raised by the mock.

        mock_magic.MagicException = Exception # Make it a generic exception for the mock to raise
        mock_magic.from_file.side_effect = mock_magic.MagicException("Magic error")

        file_info = FileInfo(path="testfile_error", size=100, extension=None)

        classify_file(file_info)
        self.assertEqual(file_info.file_type, "unknown")
        self.assertEqual(file_info.magic_number_details, "Error with magic number detection")

    def test_classify_unknown_no_magic(self):
        # Test without mocking magic, relying on fallback for truly unknown extension
        # This assumes magic won't be available or won't identify it
        file_info = FileInfo(path="testfile.unknownext", size=100, extension=".unknownext")
        # To ensure magic is not used, or if it is, it returns None or error
        with mock.patch('dupliscan.core.file_classifier.magic') as mock_m:
            mock_m.from_file.return_value = None # Simulate magic not finding a type
            classify_file(file_info)
        self.assertEqual(file_info.file_type, "unknown")

if __name__ == '__main__':
    unittest.main()
