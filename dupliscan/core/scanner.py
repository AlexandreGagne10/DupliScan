# dupliscan/core/scanner.py
import os
import hashlib
from typing import List, Tuple, Dict, Optional
from .models import FileInfo
import zipfile
import io

def _calculate_sha256(file_path: str, block_size: int = 65536) -> Optional[str]:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        # Could log this error if a logging mechanism was in place
        return None

def _calculate_sha256_from_bytes(byte_stream: io.BytesIO, block_size: int = 65536) -> Optional[str]:
    """Calculate SHA256 hash from a byte stream."""
    sha256 = hashlib.sha256()
    try:
        for block in iter(lambda: byte_stream.read(block_size), b''):
            sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        return None

def _scan_single_zip_archive(zip_file_path: str) -> Tuple[List[FileInfo], Dict[str, str]]:
    """
    Scans a single ZIP archive and returns FileInfo objects for its contents.
    """
    internal_files: List[FileInfo] = []
    zip_errors: Dict[str, str] = {}

    if not zipfile.is_zipfile(zip_file_path):
        zip_errors[zip_file_path] = "Not a valid ZIP file or corrupted."
        return internal_files, zip_errors

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            for member_info in zf.infolist():
                if member_info.is_dir():
                    continue  # Skip directories

                # Path for error reporting and identification within the zip
                internal_path_name = member_info.filename

                try:
                    # Read file content into memory
                    with zf.open(member_info, 'r') as member_file:
                        content_bytes = member_file.read()

                    content_stream = io.BytesIO(content_bytes)
                    file_hash = _calculate_sha256_from_bytes(content_stream)

                    if file_hash is None:
                        zip_errors[f"{zip_file_path}/{internal_path_name}"] = "Could not calculate hash (IOError in zip)"
                        continue

                    _, file_ext = os.path.splitext(internal_path_name)
                    extension = file_ext.lower() if file_ext else None

                    file_info = FileInfo(
                        path=internal_path_name, # Path inside the zip
                        size=member_info.file_size, # Uncompressed size
                        hash_sha256=file_hash,
                        extension=extension,
                        is_in_zip=True,
                        zip_parent_path=zip_file_path
                        # file_type for files inside zip will be classified later like other files
                    )
                    internal_files.append(file_info)
                except Exception as e:
                    zip_errors[f"{zip_file_path}/{internal_path_name}"] = f"Error processing file in zip: {str(e)}"
    except zipfile.BadZipFile:
        zip_errors[zip_file_path] = "Bad ZIP file (corrupted or not a zip)."
    except Exception as e:
        zip_errors[zip_file_path] = f"General error opening or reading zip: {str(e)}"

    return internal_files, zip_errors

def scan_directory_recursive(root_dir: str) -> Tuple[List[FileInfo], Dict[str, str]]:
    """
    Recursively scans a directory, calculates SHA256 hashes for files,
    and gathers file information.

    Args:
        root_dir (str): The root directory to start scanning.

    Returns:
        Tuple[List[FileInfo], Dict[str, str]]:
            A list of FileInfo objects for all accessible files,
            and a dictionary of errors (path: error_message).
    """
    all_files: List[FileInfo] = []
    errors: Dict[str, str] = {}

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            if not os.access(file_path, os.R_OK):
                errors[file_path] = "Permission denied"
                continue

            if os.path.islink(file_path): # Skip symlinks to avoid issues like recursive loops or hashing the link itself
                continue

            try:
                file_size = os.path.getsize(file_path)
                file_hash = _calculate_sha256(file_path)

                _, file_ext = os.path.splitext(filename)
                extension = file_ext.lower() if file_ext else None

                if file_hash is None:
                    errors[file_path] = "Could not calculate hash (IOError)"
                    continue

                file_info = FileInfo(
                    path=file_path,
                    size=file_size,
                    hash_sha256=file_hash,
                    extension=extension
                    # file_type will be determined later
                )
                all_files.append(file_info)

            except OSError as e:
                errors[file_path] = str(e)
            except Exception as e: # Catch any other unexpected error for a specific file
                errors[file_path] = f"An unexpected error occurred: {str(e)}"

    return all_files, errors

def add_zip_contents_to_scan(
    discovered_files: List[FileInfo]
    ) -> Tuple[List[FileInfo], Dict[str, str]]:
    """
    Scans inside ZIP files found in the initial list of discovered files
    and adds FileInfo objects for their contents.

    Args:
        discovered_files (List[FileInfo]): Files already found by scan_directory_recursive.
                                           It's assumed these might have been classified by type already.

    Returns:
        Tuple[List[FileInfo], Dict[str, str]]:
            A list containing *only* the FileInfo objects for files *inside* ZIPs.
            An errors dictionary for issues encountered during ZIP processing.
    """
    files_inside_zips: List[FileInfo] = []
    zip_processing_errors: Dict[str, str] = {}

    for file_info in discovered_files:
        # Condition to identify a ZIP file:
        # Check extension and then verify with zipfile.is_zipfile
        # Also ensure the file path actually exists before calling is_zipfile on it.
        is_zip = (file_info.extension == '.zip' and
                    os.path.exists(file_info.path) and # Ensure file exists on disk
                    zipfile.is_zipfile(file_info.path))

        # If type classification has run, one might use:
        # is_zip = file_info.file_type == 'archive' and file_info.extension == '.zip'
        # However, for robustness, confirming with zipfile.is_zipfile is good practice
        # if file_info.file_type == 'archive' and file_info.extension == '.zip':
        #    if not (os.path.exists(file_info.path) and zipfile.is_zipfile(file_info.path)):
        #        # Log inconsistency or handle error if type says archive but it's not a valid zip
        #        zip_processing_errors[file_info.path] = "File typed as archive/zip but not a valid zip file."
        #        continue


        if is_zip:
            if not os.access(file_info.path, os.R_OK):
                zip_processing_errors[file_info.path] = "Permission denied to read ZIP file for content scanning."
                continue

            # file_info.path is the path to the .zip file itself
            internal_files, single_zip_errors = _scan_single_zip_archive(file_info.path)
            files_inside_zips.extend(internal_files)
            zip_processing_errors.update(single_zip_errors)

    return files_inside_zips, zip_processing_errors
