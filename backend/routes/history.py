import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException 


router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("")
def list_scans():
    """Scan history index — reads all logs in output directory and summarizes them"""
    return scans

@router.get("/{scan_id}")
def get_scan(scan_id: str):
    """Scan details engine — returns the complete structural payload of a specific file"""
    path = OUTPUT_DIR / f"{scan_id}.json"
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="Scan record not found")
        
    try:
        with open(path, "r") as fp:
            return json.load(fp)
    except (json.JSONDecodeError, IOError):
        raise HTTPException(status_code=500, detail="Failed to parse scan file")