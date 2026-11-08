"""发言归属的补充称呼可以从环境变量给。

名字是每台部署自己的事：不该写进代码（仓库可能是公开的），而配置文件放在
持久卷里不好改。环境变量里的名字和 config.yaml 的 attribution 两张表合并。
"""

from __future__ import annotations

import pytest
import yaml

from ombrebrain.storage.attribution import names_from_config
from ombrebrain.storage.quote_store import render_quotes
from utils import load_config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("OMBRE_SELF_NAMES", "OMBRE_USER_NAMES"):
        monkeypatch.delenv(name, raising=False)


def _write(tmp_path, mapping):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8")
    return str(path)


def test_env_names_are_read_with_chinese_and_english_separators(tmp_path, monkeypatch):
    monkeypatch.setenv("OMBRE_SELF_NAMES", "小夜")
    monkeypatch.setenv("OMBRE_USER_NAMES", "阿青, 青青，小青、 ")
    config = load_config(_write(tmp_path, {"buckets_dir": str(tmp_path / "b")}))

    assert config["attribution"]["self_names"] == ["小夜"]
    assert config["attribution"]["user_names"] == ["阿青", "青青", "小青"]


def test_env_names_merge_with_config_file_instead_of_replacing(tmp_path, monkeypatch):
    monkeypatch.setenv("OMBRE_USER_NAMES", "阿青,小青")
    config = load_config(_write(tmp_path, {
        "buckets_dir": str(tmp_path / "b"),
        "attribution": {"self_names": ["小夜"], "user_names": ["小青"]},
    }))

    assert config["attribution"]["self_names"] == ["小夜"]
    assert config["attribution"]["user_names"] == ["小青", "阿青"]


def test_without_env_names_config_is_unchanged(tmp_path):
    config = load_config(_write(tmp_path, {
        "buckets_dir": str(tmp_path / "b"),
        "attribution": {"self_names": ["小夜"], "user_names": []},
    }))

    assert config["attribution"] == {"self_names": ["小夜"], "user_names": []}


def test_registered_names_are_not_rendered_as_third_party(tmp_path, monkeypatch):
    """登记过的名字，原话照常显示，不会被拆进「第三方说的话」那一块。"""
    quotes = [
        {"text": "我都要挂在你身上", "speaker": "阿青"},
        {"text": "那就挂着", "speaker": "小夜"},
    ]
    before = render_quotes(quotes)
    assert "non_user_speech" in before

    monkeypatch.setenv("OMBRE_SELF_NAMES", "小夜")
    monkeypatch.setenv("OMBRE_USER_NAMES", "阿青")
    config = load_config(_write(tmp_path, {"buckets_dir": str(tmp_path / "b")}))
    after = render_quotes(quotes, **names_from_config(config))

    assert "non_user_speech" not in after
    assert "🗣️ 「我都要挂在你身上」  —— 阿青" in after
    assert "🗣️ 「那就挂着」  —— 小夜" in after
