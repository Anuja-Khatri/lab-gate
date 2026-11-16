"""The numbers-lock scan ignores identifiers (URLs, DOIs) but still flags results.

Before this fix the scan read the Zenodo DOI prefix in README.md ("10.5281") as a
result-like decimal not derivable from the registry, so `make ci` failed on a fresh
clone.
"""

from __future__ import annotations

from eval.numbers_lock import check, result_tokens


def test_doi_and_url_are_not_results():
    assert result_tokens("PDF: https://doi.org/10.5281/zenodo.23954617.") == []
    assert result_tokens("measurements associated with doi:10.1039/C8MH01641K.") == []
    assert result_tokens("see 10.26434/chemrxiv-2023 for details") == []
    assert result_tokens("pinned at https://example.org/v1.2/x and v3.4") == ["3.4"]


def test_results_outside_identifiers_still_flagged():
    assert result_tokens("the gate let through 0.28 of attacks (see doi:10.5281/z.1)") == ["0.28"]
    assert result_tokens("a 12.5% rate and 40% more") == ["12.5", "40%"]


def test_repo_numbers_lock_passes():
    assert check() == 0
