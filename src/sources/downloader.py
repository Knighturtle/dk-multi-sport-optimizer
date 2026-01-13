import os
from pathlib import Path
import glob
import shutil
from datetime import datetime

def resolve_downloads_dir(watch_dir: str = None) -> Path:
    """
    Returns the Path to the Downloads directory.
    If watch_dir is provided, uses that.
    Otherwise, attempts to detect the standard Windows Downloads folder.
    """
    if watch_dir and str(watch_dir).strip():
        p = Path(watch_dir)
        if not p.exists():
            raise FileNotFoundError(f"Configured watch_dir does not exist: {watch_dir}")
        return p
    
    # Auto-detect for Windows
    # Usually %USERPROFILE%\Downloads
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        p = Path(user_profile) / "Downloads"
        if p.exists():
            return p
            
    # Fallback to standard home
    p = Path.home() / "Downloads"
    if p.exists():
        return p
        
    raise FileNotFoundError("Could not auto-detect Downloads directory. Please configure 'watch_dir' in configs/sources.yaml")

def find_latest_file(directory: Path, patterns: list[str]) -> Path | None:
    """
    Scans directory for files matching any of the patterns.
    Returns the Path of the file with the most recent modification time.
    """
    if not directory.exists():
        return None
        
    candidates = []
    for pat in patterns:
        # glob is case-sensitive on Linux but usually case-insensitive on Windows.
        # We assume standard Windows behavior or precise patterns.
        # pathlib glob doesn't support multiple patterns directly, so loop.
        candidates.extend(directory.glob(pat))
        
    if not candidates:
        return None
        
    # Sort by mtime descending
    try:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return latest
    except ValueError:
        return None

def copy_to_data_auto(src_path: Path, sport: str = "UNKNOWN", dest_dir: str = "data/auto") -> Path:
    """
    Copies the source file to dest_dir with a timestamped name.
    Returns the Path of the new file.
    """
    d_path = Path(dest_dir)
    d_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean sport name for filename
    safe_sport = "".join(c for c in sport if c.isalnum())
    
    new_name = f"{safe_sport}_DKSalaries_{timestamp}.csv"
    dest_path = d_path / new_name
    
    # Use copy2 to preserve metadata if possible, but copy is fine.
    # Atomic-like write: copy to temp then rename is weird for same filesystem,
    # but regular copy is usually fine for local -> local.
    shutil.copy2(src_path, dest_path)
    
    return dest_path
