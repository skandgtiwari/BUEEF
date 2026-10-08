"""Smoke tests for the energy analysis module."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_energy_analyzer_file_exists():
    """The project should include the energy analyzer module."""
    assert (ROOT / "src" / "analysis" / "energy_analyzer.py").exists()


def test_energy_analysis_package_layout_is_valid():
    """The analysis package should exist in the expected project layout."""
    analysis_dir = ROOT / "src" / "analysis"
    assert analysis_dir.is_dir()
    assert (analysis_dir / "__init__.py").exists()
