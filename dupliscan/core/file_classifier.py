# dupliscan/core/file_classifier.py
import magic
import os # Required for os.path.exists, though commented out in provided code
from typing import List, Dict, Optional
from .models import FileInfo # Assuming FileInfo is in models.py

# Basic extension mapping
# This can be expanded significantly
EXTENSION_TO_TYPE_MAP = {
    # Images
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
    '.bmp': 'image', '.tiff': 'image', '.webp': 'image', '.heic': 'image',
    # Videos
    '.mp4': 'video', '.avi': 'video', '.mkv': 'video', '.mov': 'video',
    '.wmv': 'video', '.flv': 'video',
    # Audio
    '.mp3': 'audio', '.wav': 'audio', '.aac': 'audio', '.flac': 'audio',
    '.ogg': 'audio',
    # Documents
    '.doc': 'document', '.docx': 'document', '.pdf': 'document', '.txt': 'document',
    '.rtf': 'document', '.odt': 'document', '.xls': 'document', '.xlsx': 'document',
    '.ppt': 'document', '.pptx': 'document', '.md': 'document',
    # Archives
    '.zip': 'archive', '.rar': 'archive', '.tar': 'archive', '.gz': 'archive',
    '.7z': 'archive',
    # Code
    '.py': 'code', '.js': 'code', '.java': 'code', '.c': 'code', '.cpp': 'code',
    '.cs': 'code', '.html': 'code', '.css': 'code', '.php': 'code', '.rb': 'code',
    '.go': 'code', '.swift': 'code', '.kt': 'code', '.pl': 'code', '.sh': 'code',
    '.json': 'data', '.xml': 'data', '.csv': 'data', '.yaml': 'data', '.yml': 'data',
    # Executables / System
    '.exe': 'executable', '.dll': 'library', '.so': 'library', '.app': 'application'
}

def classify_file(file_info: FileInfo) -> None:
    """
    Classifies a file based on its extension or magic number.
    Updates the file_info object directly with file_type and magic_number_details.
    """
    if file_info.extension and file_info.extension in EXTENSION_TO_TYPE_MAP:
        file_info.file_type = EXTENSION_TO_TYPE_MAP[file_info.extension]
    else:
        # Try using python-magic
        try:
            # Ensure the file exists before trying to open with magic
            # os.path.exists(file_info.path) # scanner should ensure path is valid
            mime_type = magic.from_file(file_info.path, mime=True)
            file_info.magic_number_details = mime_type

            # Basic interpretation of mime types
            # This can be made more sophisticated
            if mime_type:
                primary_type = mime_type.split('/')[0]
                if primary_type in ['image', 'video', 'audio', 'text']:
                    if primary_type == 'text' and file_info.extension and file_info.extension in EXTENSION_TO_TYPE_MAP:
                        # Prefer extension map for text-based code files like .py, .js if text/* is returned
                        file_info.file_type = EXTENSION_TO_TYPE_MAP[file_info.extension]
                    elif primary_type == 'text':
                         file_info.file_type = 'document' # Generic text is a document
                    else:
                        file_info.file_type = primary_type
                elif 'zip' in mime_type or 'compressed' in mime_type or 'archive' in mime_type:
                    file_info.file_type = 'archive'
                elif 'xml' in mime_type or 'json' in mime_type:
                    file_info.file_type = 'data'
                elif 'octet-stream' in mime_type:
                     # For application/octet-stream, if we have an extension map, use it.
                     if file_info.extension and file_info.extension in EXTENSION_TO_TYPE_MAP:
                        file_info.file_type = EXTENSION_TO_TYPE_MAP[file_info.extension]
                     else:
                        file_info.file_type = 'binary_unknown' # Generic binary
                else:
                    file_info.file_type = 'unknown' # Could not determine from mime
            else:
                file_info.file_type = 'unknown'
        except magic.MagicException: # Handles errors from python-magic, e.g. file not found by magic
            file_info.magic_number_details = "Error with magic number detection"
            file_info.file_type = 'unknown' # Fallback if magic fails
        except FileNotFoundError: # Specific catch for file not found before magic is even called
            file_info.magic_number_details = "File not found for magic number detection"
            file_info.file_type = 'unknown'
        except Exception as e: # Catch other potential errors like file not accessible
            file_info.magic_number_details = f"File not accessible or other error: {str(e)}"
            file_info.file_type = 'unknown'

    if not file_info.file_type: # Final fallback
        file_info.file_type = 'unknown'


def group_files_by_type(files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
    """
    Classifies a list of files and groups them by their determined file type.

    Args:
        files (List[FileInfo]): A list of FileInfo objects.

    Returns:
        Dict[str, List[FileInfo]]: A dictionary where keys are file types
                                 and values are lists of FileInfo objects.
    """
    typed_files: Dict[str, List[FileInfo]] = {}
    for file_info in files:
        classify_file(file_info) # classify_file updates file_info directly
        if file_info.file_type not in typed_files:
            typed_files[file_info.file_type] = []
        typed_files[file_info.file_type].append(file_info)
    return typed_files
