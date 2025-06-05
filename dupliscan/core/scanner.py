# dupliscan/core/scanner.py
import os
import hashlib
from typing import List, Tuple, Dict, Optional, Callable, Any
from .models import FileInfo
import zipfile
import io
from tqdm import tqdm

def _calculate_sha256(file_path: str, block_size: int = 65536) -> Optional[str]:
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        return None

def _calculate_sha256_from_bytes(byte_stream: io.BytesIO, block_size: int = 65536) -> Optional[str]:
    sha256 = hashlib.sha256()
    try:
        for block in iter(lambda: byte_stream.read(block_size), b''):
            sha256.update(block)
        return sha256.hexdigest()
    except IOError:
        return None

def _scan_single_zip_archive(zip_file_path: str) -> Tuple[List[FileInfo], Dict[str, str]]:
    internal_files: List[FileInfo] = []
    zip_errors: Dict[str, str] = {}

    if not zipfile.is_zipfile(zip_file_path):
        zip_errors[zip_file_path] = "Not a valid ZIP file or corrupted."
        return internal_files, zip_errors

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            member_info_list = zf.infolist()
            for member_info in tqdm(member_info_list, desc=f"Scanning {os.path.basename(zip_file_path)}", leave=False, unit="entry"):
                if member_info.is_dir():
                    continue

                internal_path_name = member_info.filename
                try:
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
                        path=internal_path_name,
                        size=member_info.file_size,
                        hash_sha256=file_hash,
                        extension=extension,
                        is_in_zip=True,
                        zip_parent_path=zip_file_path
                    )
                    internal_files.append(file_info)
                except Exception as e:
                    zip_errors[f"{zip_file_path}/{internal_path_name}"] = f"Error processing file in zip: {str(e)}"
    except zipfile.BadZipFile:
        zip_errors[zip_file_path] = "Bad ZIP file (corrupted or not a zip)."
    except Exception as e:
        zip_errors[zip_file_path] = f"General error opening or reading zip: {str(e)}"
    return internal_files, zip_errors

def scan_directory_recursive_resumable(
    current_scan_state: Dict[str, Any],
    pause_requested_func: Callable[[], bool]
) -> None:
    """
    Resumable version of scanning a directory. Updates current_scan_state directly.
    """
    root_dir = current_scan_state['scan_parameters']['root_dir']

    if not current_scan_state.get('collected_file_paths_for_scan_phase'):
        print("Collecting file paths for disk scan...")
        all_paths = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                all_paths.append(os.path.join(dirpath, filename))
        current_scan_state['collected_file_paths_for_scan_phase'] = all_paths
        current_scan_state['pending_file_paths_idx'] = 0

    file_paths_to_scan = current_scan_state['collected_file_paths_for_scan_phase']
    start_idx = current_scan_state.get('pending_file_paths_idx', 0)

    if 'processed_disk_files' not in current_scan_state: current_scan_state['processed_disk_files'] = []
    if 'scan_errors' not in current_scan_state: current_scan_state['scan_errors'] = {}

    with tqdm(total=len(file_paths_to_scan),
              initial=start_idx,
              desc="Scanning disk files",
              unit="file") as pbar:
        for i in range(start_idx, len(file_paths_to_scan)):
            file_path = file_paths_to_scan[i]
            pbar.set_description_str(f"Scanning disk ({os.path.basename(file_path)})")
            if pause_requested_func():
                current_scan_state['pending_file_paths_idx'] = i
                print(f"\nDisk scan paused. Processed {i}/{len(file_paths_to_scan)} files.")
                return

            if not os.access(file_path, os.R_OK):
                current_scan_state['scan_errors'][file_path] = "Permission denied"
            elif os.path.islink(file_path):
                pass
            else:
                try:
                    file_size = os.path.getsize(file_path)
                    file_hash = _calculate_sha256(file_path)
                    _, file_ext = os.path.splitext(os.path.basename(file_path))
                    extension = file_ext.lower() if file_ext else None
                    if file_hash is None:
                        current_scan_state['scan_errors'][file_path] = "Could not calculate hash (IOError)"
                    else:
                        file_info = FileInfo(
                            path=file_path, size=file_size, hash_sha256=file_hash, extension=extension
                        )
                        current_scan_state['processed_disk_files'].append(file_info)
                except OSError as e:
                    current_scan_state['scan_errors'][file_path] = str(e)
                except Exception as e:
                    current_scan_state['scan_errors'][file_path] = f"Unexpected error: {str(e)}"
            pbar.update(1)

    current_scan_state['pending_file_paths_idx'] = len(file_paths_to_scan)
    print("\nDisk file scanning phase complete.")

def add_zip_contents_to_scan_resumable(
    current_scan_state: Dict[str, Any],
    pause_requested_func: Callable[[], bool]
) -> None:
    """
    Resumable version of scanning ZIP contents. Updates current_scan_state directly.
    """
    if 'zip_files_to_scan_info' not in current_scan_state or not current_scan_state.get('zip_files_to_scan_info_collected', False):
        print("Identifying ZIP files from disk scan results...")
        discovered_files = current_scan_state.get('processed_disk_files', [])
        zips_found = []
        for file_info in tqdm(discovered_files, desc="Filtering for ZIPs", unit="file"):
            # Ensure file_info is a FileInfo object, not a dict from deserialization if issue occurs
            path_to_check = file_info.path if isinstance(file_info, FileInfo) else file_info['path']
            ext_to_check = file_info.extension if isinstance(file_info, FileInfo) else file_info['extension']

            if (ext_to_check == '.zip' and
                os.path.exists(path_to_check) and
                zipfile.is_zipfile(path_to_check)):
                # Store FileInfo object directly
                zips_found.append(file_info if isinstance(file_info, FileInfo) else FileInfo(**file_info))

        current_scan_state['zip_files_to_scan_info'] = zips_found
        current_scan_state['pending_zip_info_idx'] = 0
        current_scan_state['zip_files_to_scan_info_collected'] = True # Mark collection as done

    zip_files_to_process = current_scan_state['zip_files_to_scan_info']
    start_idx = current_scan_state.get('pending_zip_info_idx', 0)

    if 'files_from_zips_accumulator' not in current_scan_state: current_scan_state['files_from_zips_accumulator'] = []
    if 'zip_scan_errors' not in current_scan_state: current_scan_state['zip_scan_errors'] = {}

    with tqdm(total=len(zip_files_to_process),
              initial=start_idx,
              desc="Scanning ZIP contents",
              unit="zip") as pbar:
        for i in range(start_idx, len(zip_files_to_process)):
            zip_file_info_obj = zip_files_to_process[i]
            # Ensure it's a FileInfo object
            zip_file_path_to_scan = zip_file_info_obj.path if isinstance(zip_file_info_obj, FileInfo) else zip_file_info_obj['path']

            pbar.set_description_str(f"Scanning ZIP ({os.path.basename(zip_file_path_to_scan)})")
            if pause_requested_func():
                current_scan_state['pending_zip_info_idx'] = i
                print(f"\nZIP content scanning paused. Processed {i}/{len(zip_files_to_process)} ZIP files.")
                return

            if not os.access(zip_file_path_to_scan, os.R_OK):
                current_scan_state['zip_scan_errors'][zip_file_path_to_scan] = "Permission denied to read ZIP."
            else:
                internal_files, single_zip_errors = _scan_single_zip_archive(zip_file_path_to_scan)
                current_scan_state['files_from_zips_accumulator'].extend(internal_files)
                current_scan_state['zip_scan_errors'].update(single_zip_errors)
            pbar.update(1)

    current_scan_state['pending_zip_info_idx'] = len(zip_files_to_process)
    print("\nZIP content scanning phase complete.")
