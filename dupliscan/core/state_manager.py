# dupliscan/core/state_manager.py
import pickle
from typing import Any, Optional
import os

# Define a structure for the scan state (can be expanded)
# For now, using Any, but ideally, this would be a TypedDict or a dataclass
ScanState = Any

DEFAULT_STATE_FILE_NAME = ".dupliscan_state.pkl"

def save_scan_state(state: ScanState, file_path: str = DEFAULT_STATE_FILE_NAME) -> None:
    """Saves the scan state to a file using pickle."""
    try:
        with open(file_path, 'wb') as f:
            pickle.dump(state, f)
        print(f"Scan state saved to {file_path}")
    except Exception as e:
        print(f"Error saving scan state to {file_path}: {e}")

def load_scan_state(file_path: str = DEFAULT_STATE_FILE_NAME) -> Optional[ScanState]:
    """Loads the scan state from a file using pickle."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'rb') as f:
            state = pickle.load(f)
        print(f"Scan state loaded from {file_path}")
        return state
    except Exception as e:
        print(f"Error loading scan state from {file_path}: {e}. Starting fresh.")
        # Optionally, delete the corrupted state file: os.remove(file_path)
        return None

def delete_scan_state(file_path: str = DEFAULT_STATE_FILE_NAME) -> None:
    """Deletes the scan state file."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Scan state file {file_path} deleted.")
        except Exception as e:
            print(f"Error deleting scan state file {file_path}: {e}")
    else:
        print(f"Scan state file {file_path} not found, nothing to delete.")
