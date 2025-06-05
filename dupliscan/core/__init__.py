# dupliscan/core/__init__.py
from .models import FileInfo, DuplicateGroup, ScanReport
from .scanner import scan_directory_recursive, add_zip_contents_to_scan
from .duplicate_detector import find_duplicates
from .file_classifier import classify_file, group_files_by_type
