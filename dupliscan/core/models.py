# dupliscan/core/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

@dataclass
class FileInfo:
    path: str
    size: int # in bytes
    hash_sha256: Optional[str] = None
    file_type: Optional[str] = None # e.g., "image", "document", "video"
    extension: Optional[str] = None
    magic_number_details: Optional[str] = None # For files without extension
    is_in_zip: bool = False
    zip_parent_path: Optional[str] = None

    def __hash__(self):
        # Hash based on path for uniqueness in sets, if hash_sha256 is not yet computed
        return hash(self.path)

    def __eq__(self, other):
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.path == other.path

@dataclass
class DuplicateGroup:
    id: str # Typically the hash of the files in the group
    files: Set[FileInfo] = field(default_factory=set)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def potential_savings_bytes(self) -> int:
        if not self.files:
            return 0
        # Assuming we keep one file
        return self.total_size_bytes - min(f.size for f in self.files)


@dataclass
class ScanReport:
    scanned_directory: str
    total_files_scanned: int = 0
    total_size_scanned_bytes: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict) # path: error_message

    @property
    def total_duplicate_files(self) -> int:
        return sum(group.total_files for group in self.duplicate_groups)

    @property
    def total_space_consumed_by_duplicates_bytes(self) -> int:
        return sum(group.total_size_bytes for group in self.duplicate_groups)

    @property
    def potential_total_savings_bytes(self) -> int:
        return sum(group.potential_savings_bytes for group in self.duplicate_groups)
