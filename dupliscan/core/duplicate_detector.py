# dupliscan/core/duplicate_detector.py
from typing import List, Dict
from collections import defaultdict
from .models import FileInfo, DuplicateGroup

def find_duplicates(files: List[FileInfo]) -> List[DuplicateGroup]:
    """
    Identifies duplicate files based on their SHA256 hashes.

    Args:
        files (List[FileInfo]): A list of FileInfo objects.

    Returns:
        List[DuplicateGroup]: A list of DuplicateGroup objects,
                              each representing a set of duplicate files.
    """
    hashes: Dict[str, List[FileInfo]] = defaultdict(list)
    duplicate_groups: List[DuplicateGroup] = []

    for file_info in files:
        if file_info.hash_sha256: # Only consider files that have a hash
            hashes[file_info.hash_sha256].append(file_info)

    for file_hash, file_list in hashes.items():
        if len(file_list) > 1:
            # Create a set of FileInfo objects for the DuplicateGroup
            # This handles cases where the same file path might appear multiple times
            # in the input list, although scanner should ideally return unique paths.
            # Using a set here ensures each unique file path is represented once within a group.
            unique_files_in_group = set(file_list)

            # Check again if after ensuring uniqueness, there's still more than one file.
            # This is a bit redundant if file_list already contains unique FileInfo objects
            # (which it should if FileInfo's __eq__ and __hash__ are path-based).
            # However, it's a safe check.
            if len(unique_files_in_group) > 1:
                group = DuplicateGroup(
                    id=file_hash, # Use the hash as the ID for the group
                    files=unique_files_in_group
                )
                duplicate_groups.append(group)

    return duplicate_groups
