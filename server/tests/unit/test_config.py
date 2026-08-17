from __future__ import annotations

import pytest

from red_book_editor_server.app.config import Settings
from red_book_editor_server.app.dependencies import build_model_gateway
from red_book_editor_server.domain.ports import ModelGatewayError


def test_server_port_defaults_to_port_outside_godot_ai_range() -> None:
    settings = Settings(model_provider="stub")

    assert settings.server_port == 8100


def test_server_port_can_be_overridden_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERVER_PORT", "8101")

    settings = Settings(model_provider="stub")

    assert settings.server_port == 8101


def test_deepseek_key_is_required_when_building_the_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 不让仓库外部的本地 .env 影响这个配置边界测试。
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    settings = Settings(model_provider="deepseek")

    with pytest.raises(ModelGatewayError, match="model_api_key_missing"):
        build_model_gateway(settings)
