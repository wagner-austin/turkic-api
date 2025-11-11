from __future__ import annotations

import pytest

from core.translit import to_ipa


def test_to_ipa_missing_rule_file_for_uz() -> None:
    # There is no uz_ipa.rules (only uz_ipa_lat/cyr), so this should raise
    with pytest.raises(ValueError, match="not supported"):
        to_ipa("O'zbekiston", "uz")
