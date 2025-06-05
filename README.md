# DupliScan
Analyseur intelligent de doublons avec rapport interactif.

DupliScan is a Python tool designed to help you find duplicate files within a specified directory. It recursively scans through folders and can also delve into ZIP archives to identify redundant files. After the scan, DupliScan generates an HTML report that clearly lists all sets of duplicate files found, making it easy to see where you have identical copies.

## How to Use

To use DupliScan, run the `dupliscan_cli.py` script from your terminal.

**Command:**
```bash
python dupliscan_cli.py <directory_to_scan> [options]
```

**Arguments:**
-   `<directory_to_scan>`: (Required) The path to the directory you want to scan for duplicate files.
-   `-o <output_file_path>`, `--output <output_file_path>`: (Optional) The path where the HTML report will be saved. If not specified, the report will be saved as `dupliscan_report.html` in the current working directory.

**Example:**
To scan a folder named `MyDocuments` located in your user's home directory and save the report to `~/duplicates_report.html`:
```bash
python dupliscan_cli.py ~/MyDocuments -o ~/duplicates_report.html
```
If you want to save the report in the current directory with the default name (`dupliscan_report.html`):
```bash
python dupliscan_cli.py /path/to/your/folder
```

## Features

-   **Recursive Directory Scanning:** Scans the specified root directory and all its subdirectories.
-   **ZIP Archive Scanning:** Identifies and scans the contents of ZIP files for potential duplicates.
-   **File Classification:** Attempts to classify files based on their content (though this is more of an internal step visible if errors occur).
-   **Duplicate Detection:** Efficiently finds files that are identical based on their content.
-   **HTML Report Generation:** Produces a user-friendly HTML report listing all identified duplicate sets, showing their paths for easy review.

## Installation

1.  **Python:** Ensure you have Python installed on your system (version 3.6 or newer is recommended).
2.  **Dependencies:** DupliScan relies on a few external libraries. You can install them using pip and the provided `requirements.txt` file.
    - It's recommended to use a virtual environment to manage dependencies for your Python projects.

    ```bash
    # (Optional, but recommended) Create and activate a virtual environment
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    ```
    The main dependency is `python-magic`, which is used for identifying file types. Depending on your operating system, `python-magic` might have its own system-level dependencies (like `libmagic`). Please refer to the `python-magic` documentation for installation troubleshooting if you encounter issues.

## Output

DupliScan generates an HTML file (default name: `dupliscan_report.html`) that contains the results of the scan.

The report lists:
-   Sets of duplicate files found.
-   For each file in a duplicate set, its full path is provided.

This allows you to easily review the identical files and decide on any actions you might want to take (e.g., deleting redundant copies to save space).
