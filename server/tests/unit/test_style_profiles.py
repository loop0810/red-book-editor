from __future__ import annotations

import pytest
from pydantic import ValidationError

from red_book_editor_server.domain.contracts import StyleForm, StyleProfile
from red_book_editor_server.modules.content_workflow.styling.models import StyleFormArg
from red_book_editor_server.modules.content_workflow.styling.profiles import (
    load_all_profiles,
    load_style_profile,
)


def test_all_profiles_load_and_validate() -> None:
    profiles = load_all_profiles()
    assert set(profiles) == set(StyleForm)
    for profile in profiles.values():
        assert profile.display_name
        assert profile.hooks
        assert profile.structures
        assert profile.rewrite_rules
        assert profile.tags.generic
        assert profile.tags.precise
        assert profile.tags.trending
        assert profile.cover.pattern
        assert profile.cta
        low, high = profile.rich_text.tag_count_range
        assert 0 < low <= high


def test_load_each_form_by_name() -> None:
    for form in StyleForm:
        profile = load_style_profile(form)
        assert isinstance(profile, StyleProfile)


def test_unknown_form_value_rejected() -> None:
    with pytest.raises(ValidationError):
        StyleFormArg.model_validate({"form": "unknown"})


def test_style_profile_schema_rejects_bad_yaml_shape() -> None:
    with pytest.raises(ValidationError):
        StyleProfile.model_validate({"display_name": "缺 form"})
