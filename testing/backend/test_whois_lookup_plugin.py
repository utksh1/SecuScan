import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure our local repo root is in the Python search path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Import the lookup function from our target plugin tool
from plugins.whois_lookup.whois_tool import lookup

def test_whois_lookup_missing_binary_graceful_fallback():
    """
    Test that when the system whois wrapper fails (simulating a missing binary or execution fault),
    the plugin catches the failure gracefully and returns an error dictionary instead of crashing.
    """
    mock_error_msg = "Error: whois binary not found on the system host environment."

    # Use a standard Exception which plugins/whois_lookup/whois_tool.py line 18 is built to catch
    with patch("whois.whois", side_effect=Exception(mock_error_msg)):
        result = lookup("example.com")

        # Verify the tool safely intercepted the crash and returned the message string under the "error" key
        assert isinstance(result, dict)
        assert "error" in result
        assert mock_error_msg in result["error"]