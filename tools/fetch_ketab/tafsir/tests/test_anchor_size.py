import pytest

from filter_blocks_by_hadith_occurrence import (
    determine_anchor_size,
    SHORT_HADITH_MAX_TOKENS,
)


def test_determine_anchor_size_short():
    # short hadiths (<= SHORT_HADITH_MAX_TOKENS) should use full length
    for n in range(1, SHORT_HADITH_MAX_TOKENS + 1):
        assert determine_anchor_size(n, None) == n


def test_determine_anchor_size_long():
    # longer hadiths should not return the full length (generally smaller)
    long_len = SHORT_HADITH_MAX_TOKENS + 4
    val = determine_anchor_size(long_len, None)
    assert 1 <= val < long_len


def test_anchor_override_respected():
    assert determine_anchor_size(10, 3) == 3
    assert determine_anchor_size(2, 4) == 4  # anchor_override wins (clamped to >=1)
