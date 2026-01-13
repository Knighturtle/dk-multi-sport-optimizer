import os
from datetime import datetime
from pathlib import Path
import json # Added import for json
import pandas as pd # Added for DataFrame handling

def append_journal(entry_dict: dict, log_path: str = "logs/learning_journal.md", language: str = "English") -> str:
    """
    Appends a formatted entry to the journal (Markdown or JSONL).
    """
    entry_dict["language"] = language
    entry_dict["timestamp"] = datetime.now().isoformat()
    p = Path(log_path)
    
    # Ensure directory exists
    p.parent.mkdir(parents=True, exist_ok=True)

    if p.suffix == ".jsonl":
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")
    else:
        # Markdown Fallback
        md_content = f"\n## {entry_dict.get('type', 'Entry').title()} - {entry_dict['timestamp']}\n"
        if "content" in entry_dict:
            md_content += f"{entry_dict['content']}\n"
        
        if "user_notes" in entry_dict and entry_dict['user_notes']:
            md_content += f"\n### User Notes\n{entry_dict['user_notes']}\n"
            
        md_content += "\n---\n"
        
        with open(p, "a", encoding="utf-8") as f:
            f.write(md_content)
        
    return str(p.absolute())

def read_journal_jsonl(path: str) -> pd.DataFrame:
    """
    Reads a JSONL journal file into a pandas DataFrame safely.
    Handles missing files, JSON errors, and timestamp conversion.
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=["timestamp", "type", "content", "language", "user_notes"])
    
    data = []
    errors = 0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                errors += 1
                
    df = pd.DataFrame(data)
    
    # Ensure specific columns exist to avoid KeyErrors
    expected_cols = ["timestamp", "type", "content", "language", "user_notes"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
            
    # Convert timestamp to datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        
    return df
