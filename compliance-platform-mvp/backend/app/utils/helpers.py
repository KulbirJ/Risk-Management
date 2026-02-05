"""Utilities for common operations."""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary."""
    if d is None or not isinstance(d, dict):
        return default
    return d.get(key, default)


def serialize_dict(d: Dict[str, Any]) -> str:
    """Serialize a dictionary to JSON string."""
    try:
        return json.dumps(d, default=str)
    except Exception as e:
        logger.error(f"Error serializing dict: {e}")
        return "{}"


def deserialize_dict(s: str) -> Dict[str, Any]:
    """Deserialize a JSON string to dictionary."""
    try:
        return json.loads(s)
    except Exception as e:
        logger.error(f"Error deserializing JSON: {e}")
        return {}


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string."""
    if dt is None:
        return ""
    return dt.strftime(fmt)


def severity_from_impact_likelihood(impact: str, likelihood: str) -> str:
    """
    Compute severity from impact and likelihood (simple rule-based approach for Phase 0).
    
    Severity matrix:
    - If either is Critical → Critical
    - If both are High → High
    - If one is High → High
    - Otherwise → Medium or Low
    
    Args:
        impact: One of {Low, Medium, High, Critical}
        likelihood: One of {Low, Medium, High, Critical}
        
    Returns:
        Severity level
    """
    values = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    
    impact_val = values.get(impact, 2)
    likelihood_val = values.get(likelihood, 2)
    
    combined = impact_val * likelihood_val
    
    if combined >= 12:  # Critical * High or higher
        return "Critical"
    elif combined >= 9:  # High * High
        return "High"
    elif combined >= 6:  # High * Medium or Medium * High
        return "Medium"
    else:
        return "Low"


def parse_audit_changes(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse before/after dictionaries into audit change delta.
    
    Args:
        before: State before change
        after: State after change
        
    Returns:
        Dictionary with changed fields
    """
    if not before or not after:
        return {"before": before, "after": after}
    
    changes = {}
    for key in set(list((before or {}).keys()) + list((after or {}).keys())):
        before_val = (before or {}).get(key)
        after_val = (after or {}).get(key)
        if before_val != after_val:
            changes[key] = {"before": before_val, "after": after_val}
    
    return changes if changes else {"before": before, "after": after}
