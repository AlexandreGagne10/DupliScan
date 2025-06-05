# dupliscan_cli.py
import argparse
import os
import sys
from datetime import datetime

# Assuming 'dupliscan' package is in the same directory or PYTHONPATH
from dupliscan.core import (
    scan_directory_recursive,
    add_zip_contents_to_scan,
    find_duplicates,
    classify_file
)
from dupliscan.ui import generate_html_report
# FileInfo is needed for type hinting if used, but not directly called here.

def main():
    parser = argparse.ArgumentParser(description="DupliScan: Find and report duplicate files.")
    parser.add_argument(
        "scan_directory",
        metavar="DIRECTORY",
        type=str,
        help="The root directory to scan for duplicates."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="dupliscan_report.html",
        help="Path to save the HTML report. Defaults to 'dupliscan_report.html' in the current directory."
    )

    args = parser.parse_args()

    scan_path = args.scan_directory
    report_output_path = args.output

    if not os.path.isdir(scan_path):
        print(f"Error: Scan directory '{scan_path}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Starting DupliScan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scanning directory: {scan_path}...")

    # 1. Scan all files on disk
    all_disk_files, scan_errors = scan_directory_recursive(scan_path)
    if scan_errors:
        print(f"Encountered {len(scan_errors)} errors during initial scan (see report for details).")
        # Consider logging these errors more formally or printing them if verbose

    print(f"Found {len(all_disk_files)} files on disk.")

    # 2. Classify all disk files (updates FileInfo objects in-place)
    print("Classifying files...")
    for f_info in all_disk_files:
        classify_file(f_info)
        # classify_file handles its own errors by setting type to 'unknown'
        # and potentially logging to f_info.magic_number_details

    # 3. Scan contents of ZIP files found among disk files
    print("Scanning contents of ZIP archives...")
    # add_zip_contents_to_scan identifies zips based on extension and is_zipfile check
    files_from_zips, zip_scan_errors = add_zip_contents_to_scan(all_disk_files)
    if zip_scan_errors:
        print(f"Encountered {len(zip_scan_errors)} errors during ZIP content scanning (see report for details).")

    print(f"Found {len(files_from_zips)} files inside ZIP archives.")

    # Combine all FileInfo objects
    all_files_to_check = all_disk_files + files_from_zips

    # Consolidate errors (though the report doesn't display them yet, good to have)
    # all_errors = {**scan_errors, **zip_scan_errors}

    if not all_files_to_check:
        print("No files found to process. Exiting.")
        sys.exit(0)

    # 4. Find duplicates among all files (disk + inside ZIPs)
    print("Finding duplicates...")
    duplicate_groups = find_duplicates(all_files_to_check)

    if not duplicate_groups:
        print("No duplicate files found.")
    else:
        print(f"Found {len(duplicate_groups)} sets of duplicate files.")

    # 5. Generate HTML report
    print(f"Generating HTML report at: {report_output_path}")
    try:
        # The generate_html_report function in the UI module will use the duplicate_groups
        # It might also be useful to pass summary_stats or all_errors to the report generator in the future.
        generate_html_report(duplicate_groups, report_output_path)
        print("Report generated successfully.")
    except Exception as e:
        print(f"Error generating HTML report: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"DupliScan finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
