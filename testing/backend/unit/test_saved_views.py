"""
Unit tests for FilterPreset, SavedViewCreate, and SavedViewUpdate validators in saved_views.py.
"""
import json
import pytest
from pydantic import ValidationError
from backend.secuscan.saved_views_models import FilterPreset, SavedViewCreate, SavedViewUpdate


# FilterPreset tests


class TestFilterPreset:
    def test_default_values(self):
        """Default values are applied when no args are provided."""
        preset = FilterPreset()
        assert preset.severity == "all"
        assert preset.target == "all"
        assert preset.scanner == "all"
        assert preset.sortMode == "severity"
        assert preset.dateFrom == ""
        assert preset.dateTo == ""
        assert preset.searchQuery == ""

    def test_valid_sort_modes(self):
        """All valid sortMode values are accepted."""
        for mode in ("severity", "newest", "oldest", "target"):
            preset = FilterPreset(sortMode=mode)
            assert preset.sortMode == mode

    def test_invalid_sort_mode_raises(self):
        """Invalid sortMode raises ValueError."""
        with pytest.raises(ValidationError):
            FilterPreset(sortMode="invalid_mode")

    def test_valid_severities(self):
        """All valid severity values are accepted."""
        for sev in ("all", "critical", "high", "medium", "low", "info"):
            preset = FilterPreset(severity=sev)
            assert preset.severity == sev

    def test_invalid_severity_raises(self):
        """Invalid severity raises ValueError."""
        with pytest.raises(ValidationError):
            FilterPreset(severity="super_critical")

    def test_all_fields_provided(self):
        """All fields can be set simultaneously."""
        preset = FilterPreset(
            severity="high",
            target="example.com",
            scanner="nmap",
            sortMode="newest",
            dateFrom="2026-01-01",
            dateTo="2026-12-31",
            searchQuery="sql injection",
        )
        assert preset.severity == "high"
        assert preset.target == "example.com"
        assert preset.scanner == "nmap"
        assert preset.sortMode == "newest"


# SavedViewCreate tests


class TestSavedViewCreate:
    def test_valid_name_and_filter(self):
        """Valid name and filter_json are accepted."""
        view = SavedViewCreate(
            name="My View",
            filter_json=json.dumps({"severity": "high", "sortMode": "newest"}),
        )
        assert view.name == "My View"
        assert "high" in view.filter_json

    def test_name_stripped(self):
        """Leading and trailing whitespace is stripped from name."""
        view = SavedViewCreate(name="  Spacy Name  ", filter_json="{}")
        assert view.name == "Spacy Name"

    def test_blank_name_raises(self):
        """Blank name (whitespace only) raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewCreate(name="   ", filter_json="{}")

    def test_empty_name_raises(self):
        """Empty name raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewCreate(name="", filter_json="{}")

    def test_filter_json_must_be_valid_json(self):
        """Non-JSON filter_json raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewCreate(name="Bad JSON", filter_json="not valid json {")

    def test_filter_json_must_pass_preset_validation(self):
        """filter_json that fails FilterPreset validation raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewCreate(name="Bad Preset", filter_json=json.dumps({"sortMode": "invalid"}))

    def test_name_max_length_60(self):
        """Name longer than 60 chars raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewCreate(name="a" * 61, filter_json="{}")

    def test_name_60_chars_ok(self):
        """Name exactly 60 chars is accepted."""
        view = SavedViewCreate(name="a" * 60, filter_json="{}")
        assert len(view.name) == 60


# SavedViewUpdate tests


class TestSavedViewUpdate:
    def test_all_fields_none_by_default(self):
        """All fields default to None."""
        update = SavedViewUpdate()
        assert update.name is None
        assert update.filter_json is None

    def test_name_can_be_set(self):
        """name can be set independently."""
        update = SavedViewUpdate(name="Updated View")
        assert update.name == "Updated View"

    def test_filter_json_can_be_set(self):
        """filter_json can be set independently."""
        update = SavedViewUpdate(filter_json=json.dumps({"severity": "critical"}))
        assert "critical" in update.filter_json

    def test_both_fields_can_be_set(self):
        """Both fields can be set together."""
        update = SavedViewUpdate(
            name="Both",
            filter_json=json.dumps({"severity": "low"}),
        )
        assert update.name == "Both"
        assert "low" in update.filter_json

    def test_filter_json_validated_when_provided(self):
        """filter_json is validated when provided (not None)."""
        with pytest.raises(ValidationError):
            SavedViewUpdate(filter_json="not json")

    def test_name_stripped_when_provided(self):
        """Whitespace is stripped from name when provided."""
        update = SavedViewUpdate(name="  Trimmed  ")
        assert update.name == "Trimmed"

    def test_blank_name_raises(self):
        """Blank name raises ValueError."""
        with pytest.raises(ValidationError):
            SavedViewUpdate(name="  ")
