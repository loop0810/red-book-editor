from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from red_book_editor_server.domain.contracts import SourceExperienceDto


def test_source_experience_requires_a_scenario_and_action() -> None:
    source = SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=["固定绘本时间"])
    assert source.baby_month == 19


def test_source_experience_rejects_empty_actions() -> None:
    with pytest.raises(ValidationError):
        SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=[])


def test_source_experience_accepts_asset_ids() -> None:
    source = SourceExperienceDto(
        baby_month=19,
        scenario="出门",
        actions=["准备随身物品"],
        asset_ids=[uuid4()],
    )
    assert len(source.asset_ids) == 1
