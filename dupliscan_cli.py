import signal
import os
import sys
from datetime import datetime
import argparse
from typing import Optional, Dict, List, Any # For type hinting
from collections import defaultdict
from tqdm import tqdm # Added for classification loop
from dupliscan.core import (
    scan_directory_recursive_resumable, # Changed
    add_zip_contents_to_scan_resumable, # Changed
    find_duplicates, # Will be find_duplicates_resumable later
    classify_file
)
from dupliscan.core.models import FileInfo, DuplicateGroup # For state structure and report
from dupliscan.ui import generate_html_report
from dupliscan.core.state_manager import load_scan_state, save_scan_state, delete_scan_state, DEFAULT_STATE_FILE_NAME

current_scan_state: Optional[Dict[str, Any]] = None
pause_requested: bool = False

def signal_handler(signum, frame):
    global pause_requested
    if not pause_requested: # Print message only once
        print("\nCtrl+C detected. Requesting pause.")
        print("Attempting to save state. Please wait for current operation to complete...")
    pause_requested = True

def main():
    global current_scan_state
    global pause_requested

    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="DupliScan: Find and report duplicate files. Supports resumable scans.")
    parser.add_argument("scan_directory", metavar="DIRECTORY", type=str, help="The root directory to scan for duplicates.")
    parser.add_argument("-o", "--output", type=str, default="dupliscan_report.html", help="Path to save the HTML report.")
    parser.add_argument("--resume", action="store_true", help="Resume a previously paused scan.")
    parser.add_argument("--fresh-start", action="store_true", help=f"Force a new scan, deleting any saved state file ({DEFAULT_STATE_FILE_NAME}).")
    args = parser.parse_args()

    scan_path_arg = args.scan_directory
    report_output_path_arg = args.output
    state_file_path = DEFAULT_STATE_FILE_NAME

    if args.fresh_start:
        print(f"Fresh start requested. Deleting state file: {state_file_path}...")
        delete_scan_state(state_file_path)
        current_scan_state = None

    if args.resume:
        if args.fresh_start:
            print("Warning: --resume is ignored when --fresh-start is also specified.")
        else:
            print(f"Attempting to resume scan from state file: {state_file_path}...")
            current_scan_state = load_scan_state(state_file_path)
            if not current_scan_state:
                print(f"Error: --resume specified, but no saved state found at {state_file_path} or state file corrupted. Exiting.")
                sys.exit(1)
            else:
                print(f"Successfully loaded saved state. Resuming from phase: {current_scan_state.get('current_scan_phase', 'UNKNOWN')}")

    if current_scan_state:
        scan_path = current_scan_state['scan_parameters']['root_dir']
        report_output_path = current_scan_state['scan_parameters']['report_output_path']
        if scan_path_arg != scan_path:
            print(f"Warning: Scan directory argument '{scan_path_arg}' is different from saved state's directory '{scan_path}'. Using saved state's directory.")
        if report_output_path_arg != report_output_path:
             print(f"Warning: Output path argument '{report_output_path_arg}' is different from saved state's path '{report_output_path}'. Using saved state's output path.")
    else:
        scan_path = scan_path_arg
        report_output_path = report_output_path_arg
        print(f"Starting a new scan for directory: {scan_path}")
        if not args.fresh_start and os.path.exists(state_file_path):
            print(f"Warning: Existing state file {state_file_path} found. It will be overwritten if this scan is paused/completes without --resume.")

        current_scan_state = {
            'scan_parameters': {'root_dir': scan_path, 'report_output_path': report_output_path},
            'current_scan_phase': 'INIT',
            'collected_file_paths_for_scan_phase': [], 'pending_file_paths_idx': 0,
            'processed_disk_files': [], 'scan_errors': {},
            'classification_idx': 0, # Added for resumable classification
            'zip_files_to_scan_info': [], 'pending_zip_info_idx': 0,
            'zip_files_to_scan_info_collected': False, # To track if zip_files_to_scan_info is populated
            'files_from_zips_accumulator': [], 'zip_scan_errors': {},
            'all_files_to_check_for_duplicate_phase': [],
            'processed_duplication_check_idx': 0,
            'hashes_dict_accumulator': defaultdict(list),
        }

    if not os.path.isdir(scan_path):
        print(f"Error: Scan directory '{scan_path}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"DupliScan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Phase 1: Scan Disk
        if current_scan_state['current_scan_phase'] == 'INIT':
            current_scan_state['current_scan_phase'] = 'SCANNING_DISK'

        if current_scan_state['current_scan_phase'] == 'SCANNING_DISK':
            print("Phase: Scanning disk files...")
            scan_directory_recursive_resumable(current_scan_state, lambda: pause_requested)
            print(f"Disk scan phase: {len(current_scan_state.get('processed_disk_files',[]))} files processed.")
            if pause_requested: raise KeyboardInterrupt
            current_scan_state['current_scan_phase'] = 'CLASSIFYING'

        # Phase 2: Classify Files
        if current_scan_state['current_scan_phase'] == 'CLASSIFYING':
            print("Phase: Classifying disk files...")
            files_to_classify = current_scan_state.get('processed_disk_files', [])
            if 'classification_idx' not in current_scan_state:
                 current_scan_state['classification_idx'] = 0

            start_idx = current_scan_state.get('classification_idx', 0)

            with tqdm(total=len(files_to_classify),
                      initial=start_idx,
                      desc="Classifying files",
                      unit="file") as pbar_classify:
                for i in range(start_idx, len(files_to_classify)):
                    # Ensure f_info is a FileInfo object, especially if state was loaded
                    f_data = files_to_classify[i]
                    if isinstance(f_data, dict): # If loaded from older state or error
                        f_info = FileInfo(**f_data)
                        files_to_classify[i] = f_info # Replace dict with object
                    else:
                        f_info = f_data

                    if not f_info.file_type:
                        classify_file(f_info)
                    current_scan_state['classification_idx'] = i + 1
                    pbar_classify.update(1)
                    if pause_requested: break

            if pause_requested: raise KeyboardInterrupt
            current_scan_state['current_scan_phase'] = 'SCANNING_ZIPS'

        # Phase 3: Scan ZIP contents
        if current_scan_state['current_scan_phase'] == 'SCANNING_ZIPS':
            print("Phase: Scanning ZIP contents...")
            add_zip_contents_to_scan_resumable(current_scan_state, lambda: pause_requested)
            print(f"ZIP scan phase: {len(current_scan_state.get('files_from_zips_accumulator',[]))} files found in ZIPs.")
            if pause_requested: raise KeyboardInterrupt
            current_scan_state['current_scan_phase'] = 'FINDING_DUPLICATES'

        # Phase 4: Find Duplicates
        duplicate_groups: List[DuplicateGroup] = []
        if current_scan_state['current_scan_phase'] == 'FINDING_DUPLICATES':
            print("Phase: Finding duplicates...")
            processed_disk_files_state = current_scan_state.get('processed_disk_files', [])
            files_from_zips_state = current_scan_state.get('files_from_zips_accumulator', [])

            # Ensure all elements are FileInfo objects before concatenation
            all_files_for_dup_check = []
            for item_list in [processed_disk_files_state, files_from_zips_state]:
                for item_data in item_list:
                    if isinstance(item_data, dict):
                        all_files_for_dup_check.append(FileInfo(**item_data))
                    elif isinstance(item_data, FileInfo):
                        all_files_for_dup_check.append(item_data)

            current_scan_state['all_files_to_check_for_duplicate_phase'] = all_files_for_dup_check

            if not current_scan_state['all_files_to_check_for_duplicate_phase']:
                print("No files found to check for duplicates.")
            else:
                print("(Placeholder for resumable_find_duplicates call)")
                # Simulate for reporting using existing find_duplicates for now:
                # This part will be replaced by resumable_find_duplicates in the next step.
                # For now, if resuming and hashes_dict_accumulator has data, try to build groups.
                # Otherwise, run the non-resumable version if it's a new scan or this part wasn't reached.
                start_dup_find_idx = current_scan_state.get('processed_duplication_check_idx', 0)

                if start_dup_find_idx > 0 and current_scan_state['hashes_dict_accumulator']:
                     print(f"Resuming duplicate finding (partially, from accumulated hashes)...")
                     for file_hash, file_info_data_list in current_scan_state['hashes_dict_accumulator'].items():
                        if len(file_info_data_list) > 1:
                            files = set()
                            for fi_data in file_info_data_list:
                                if isinstance(fi_data, dict): files.add(FileInfo(**fi_data))
                                else: files.add(fi_data) # Assume FileInfo
                            if len(files) > 1: # check after potential conversion
                                duplicate_groups.append(DuplicateGroup(id=file_hash, files=files))
                elif not current_scan_state['hashes_dict_accumulator']: # Only run if no prior accumulation
                    print("Running non-resumable find_duplicates as placeholder...")
                    duplicate_groups = find_duplicates(current_scan_state['all_files_to_check_for_duplicate_phase'])


            if not duplicate_groups: print("No duplicate files found (yet).")
            else: print(f"Found {len(duplicate_groups)} sets of duplicate files.")
            if pause_requested: raise KeyboardInterrupt
            current_scan_state['current_scan_phase'] = 'REPORTING'

        # Phase 5: Generate Report
        if current_scan_state['current_scan_phase'] == 'REPORTING':
            print("Phase: Generating HTML report...")
            if not duplicate_groups and current_scan_state.get('hashes_dict_accumulator'):
                # Try to build groups one last time if not built in FINDING_DUPLICATES phase (e.g., if resumed straight to reporting)
                print("Attempting to build duplicate groups for report from accumulated hashes...")
                for file_hash, file_info_data_list in current_scan_state['hashes_dict_accumulator'].items():
                    if len(file_info_data_list) > 1:
                        files = set()
                        for fi_data in file_info_data_list:
                            if isinstance(fi_data, dict): files.add(FileInfo(**fi_data))
                            else: files.add(fi_data)
                        if len(files) > 1:
                           duplicate_groups.append(DuplicateGroup(id=file_hash, files=files))

            if not duplicate_groups:
                print("No duplicates to report.")
            else:
                print(f"Generating HTML report at: {report_output_path} for {len(duplicate_groups)} groups.")

            generate_html_report(duplicate_groups, report_output_path)
            print("Report generated successfully.")

            print(f"Scan complete. Deleting state file: {state_file_path}")
            delete_scan_state(state_file_path)
            current_scan_state['current_scan_phase'] = 'COMPLETED'

    except KeyboardInterrupt:
        if pause_requested and current_scan_state:
            print("\nScan paused by user. Saving state...")
            save_scan_state(current_scan_state, state_file_path)
            print(f"State saved to {state_file_path}. To resume, run with --resume for directory '{scan_path}'.")
        else:
            print("\nScan interrupted by user (not a planned pause or no state to save).")
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred during phase {current_scan_state.get('current_scan_phase', 'UNKNOWN')}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if current_scan_state and current_scan_state.get('current_scan_phase') not in ['COMPLETED', None]:
            print("Attempting to save state due to error...")
            save_scan_state(current_scan_state, state_file_path)
            print(f"State saved to {state_file_path}. You might be able to resume after fixing the issue.")
        sys.exit(1)
    finally:
        print(f"DupliScan finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
