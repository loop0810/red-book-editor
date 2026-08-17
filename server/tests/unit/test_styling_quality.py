from __future__ import annotations

from red_book_editor_server.domain.contracts import ContentBriefDto
from red_book_editor_server.modules.content_workflow.styling.quality import (
    enrichment_issues,
    source_overlap_issues,
)


def _brief(material: str) -> ContentBriefDto:
    return ContentBriefDto(focus="宝宝周岁宴", raw_material=material)


def test_source_overlap_flags_a_copied_opening() -> None:
    brief = _brief("没有邀请很多人，只邀请父母和朋友参加周岁宴，大家都很开心。")
    body = (
        "没有邀请很多人，只邀请父母和朋友参加周岁宴，大家都很开心。\n\n"
        "这次记录再补充一点过程。\n\n"
        "最后把主题收束回来。"
    )

    issues = source_overlap_issues(brief, body)

    assert any("开头" in issue for issue in issues)


def test_source_overlap_flags_paragraph_splitting_reuse() -> None:
    brief = _brief(
        "我们先确定只办小范围的小型家庭聚餐。再邀请父母和朋友参加周岁宴，最后记录大家都很开心。"
    )
    body = (
        "这篇先把周岁宴的取舍讲清楚。\n\n"
        "我们先确定只办小范围的小型家庭聚餐。\n\n"
        "再邀请父母和朋友参加周岁宴，最后记录大家都很开心。"
    )

    issues = source_overlap_issues(brief, body)

    assert any("连续复用" in issue for issue in issues)


def test_source_overlap_allows_natural_paraphrase_and_short_required_facts() -> None:
    brief = _brief("宝宝12个月，只和父母吃饭。")
    body = (
        "周岁这件事，我们把重点放在一家人一起吃顿饭。\n\n"
        "没有安排大规模聚会，而是邀请父母参与这次简单的庆祝。\n\n"
        "宝宝12个月这个时间点仍然保留在记录里。"
    )

    assert source_overlap_issues(brief, body) == []


def test_enrichment_requires_structure_but_accepts_numbered_body() -> None:
    brief = _brief("宝宝喜欢爬沙发，买了软包楼梯。")

    assert enrichment_issues(brief, "太短了")
    assert (
        enrichment_issues(
            brief,
            "1. 先记录宝宝的动作和选择，把已经发生的过程交代清楚。\n"
            "2. 再补充这次经历的观察和边界，避免把个人记录写成普遍建议。",
        )
        == []
    )
