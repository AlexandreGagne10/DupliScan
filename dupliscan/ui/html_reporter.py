# dupliscan/ui/html_reporter.py
from typing import List
from dupliscan.core.models import DuplicateGroup, FileInfo # Adjust import path if necessary

def generate_html_report(duplicate_groups: List[DuplicateGroup], output_html_path: str) -> None:
    """
    Generates a basic HTML report listing duplicate files.

    Args:
        duplicate_groups (List[DuplicateGroup]): A list of DuplicateGroup objects.
        output_html_path (str): Path to save the generated HTML file.
    """

    total_duplicate_sets = len(duplicate_groups)
    total_files_in_duplicates = sum(len(group.files) for group in duplicate_groups)

    # Basic inline CSS for readability
    html_style = """
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        h1 { color: #333; border-bottom: 2px solid #337ab7; padding-bottom: 10px; }
        h2 { color: #337ab7; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px;}
        ul { list-style-type: none; padding-left: 0; }
        li { background-color: #fff; border: 1px solid #ddd; margin-bottom: 8px; padding: 10px; border-radius: 4px; }
        li:hover { background-color: #f9f9f9; }
        .file-path { font-weight: bold; }
        .file-details { font-size: 0.9em; color: #555; }
        .zip-info { font-style: italic; color: #777; }
        .summary { background-color: #e7f3fe; border-left: 6px solid #2196F3; padding: 15px; margin-bottom: 20px; }
        .group-header { margin-bottom: 10px;}
        .open-folder-btn {
            margin-left: 10px;
            padding: 3px 8px;
            font-size: 0.8em;
            color: white;
            background-color: #5cb85c;
            border: none;
            border-radius: 3px;
            text-decoration: none;
            cursor: pointer; /* To show it's clickable, though not functional */
        }
         .open-folder-btn:hover { background-color: #4cae4c; }
    </style>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DupliScan Report</title>
        {html_style}
    </head>
    <body>
        <h1>DupliScan - Duplicate File Report</h1>

        <div class="summary">
            <p><strong>Summary:</strong></p>
            <p>Total duplicate sets found: {total_duplicate_sets}</p>
            <p>Total files involved in duplicates: {total_files_in_duplicates}</p>
        </div>
    """

    for i, group in enumerate(duplicate_groups):
        group_size_mb = group.total_size_bytes / (1024 * 1024)
        potential_savings_mb = group.potential_savings_bytes / (1024 * 1024)

        html_content += f"""
        <div class="group-header">
            <h2>Duplicate Set {i + 1} (Hash: {group.id})</h2>
            <p class="file-details">
                Number of files: {group.total_files} |
                Total size: {group_size_mb:.2f} MB |
                Potential savings: {potential_savings_mb:.2f} MB
            </p>
        </div>
        <ul>
        """
        # Sort files by path for consistent order in report
        sorted_files = sorted(list(group.files), key=lambda f: f.path)

        for file_info in sorted_files:
            zip_info_str = ""
            if file_info.is_in_zip and file_info.zip_parent_path:
                zip_info_str = f"""
                <span class="zip-info"> (File is inside ZIP:
                <span class="file-path">{file_info.zip_parent_path}</span>,
                internal path: <span class="file-path">{file_info.path}</span>)
                </span>
                """
            else:
                 zip_info_str = f"""
                 <span class="file-path">{file_info.path}</span>
                 """

            file_size_mb = file_info.size / (1024 * 1024)

            html_content += f"""
            <li>
                {zip_info_str}
                <button class="open-folder-btn" title="This feature is not yet implemented">Open Folder</button>
                <br>
                <span class="file-details">Size: {file_size_mb:.2f} MB | SHA256: {file_info.hash_sha256}</span>
            </li>
            """
        html_content += "</ul>"

    html_content += """
    </body>
    </html>
    """

    try:
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except IOError as e:
        # In a real app, this might raise an error or log it.
        # For now, we can print to stderr or store it if we had an error aggregation mechanism.
        print(f"Error writing HTML report to {output_html_path}: {e}")


if __name__ == '__main__':
    # Example Usage (for testing the reporter directly)
    # Create some dummy data
    f1 = FileInfo(path="/test/fileA.txt", size=1024, hash_sha256="hash123", extension=".txt", file_type="document")
    f2 = FileInfo(path="/test/fileA_copy.txt", size=1024, hash_sha256="hash123", extension=".txt", file_type="document")
    f3 = FileInfo(path="/another/fileB.jpg", size=2048, hash_sha256="hash456", extension=".jpg", file_type="image")
    f4 = FileInfo(path="/another/fileB_variant.jpg", size=2050, hash_sha256="hash456", extension=".jpg", file_type="image")
    f5 = FileInfo(path="archive_content/img1.png", size=500, hash_sha256="hash789", extension=".png", file_type="image", is_in_zip=True, zip_parent_path="/docs/my_archive.zip")
    f6 = FileInfo(path="data/photo_collections/img1.png", size=500, hash_sha256="hash789", extension=".png", file_type="image")


    group1 = DuplicateGroup(id="hash123", files={f1, f2})
    group2 = DuplicateGroup(id="hash456", files={f3, f4})
    group3 = DuplicateGroup(id="hash789", files={f5, f6})

    mock_duplicate_groups = [group1, group2, group3]

    report_path = "dupliscan_report_test.html"
    generate_html_report(mock_duplicate_groups, report_path)
    print(f"Generated dummy report: {report_path}")
