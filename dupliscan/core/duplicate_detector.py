# dupliscan/core/duplicate_detector.py
from typing import List, Dict
from collections import defaultdict
from .models import FileInfo, DuplicateGroup
from tqdm import tqdm # Added import

def find_duplicates(files: List[FileInfo]) -> List[DuplicateGroup]:
    hashes: Dict[str, List[FileInfo]] = defaultdict(list)
    duplicate_groups: List[DuplicateGroup] = []

    for file_info in tqdm(files, desc="Finding duplicates"): # tqdm added here
        if file_info.hash_sha256:
            hashes[file_info.hash_sha256].append(file_info)

    for file_hash, file_list in hashes.items():
        if len(file_list) > 1:
            # Ensure all files in this list are unique before forming a group
            # This handles the edge case where the same FileInfo object might appear multiple times
            # if, for example, a file inside a zip has the same hash as an external file
            # and they were somehow represented by the same FileInfo instance (though unlikely with current structure).
            # More importantly, it ensures that if multiple FileInfo objects represent the same file path
            # (e.g. due to symlinks or case sensitivity issues not handled earlier), they are treated as one.
            # However, FileInfo objects are distinct based on path (especially for zip internal paths),
            # so this set conversion primarily ensures that we don't have literally the same FileInfo object instance twice.
            unique_files_in_group = set(file_list) # Using set to ensure unique FileInfo objects

            if len(unique_files_in_group) > 1:
                group = DuplicateGroup(
                    id=file_hash, # Using hash as a unique ID for the group
                    files=unique_files_in_group # Storing the set of unique FileInfo objects
                )
                duplicate_groups.append(group)

    return duplicate_groups
