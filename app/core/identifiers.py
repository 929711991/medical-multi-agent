"""统一管理数据库中的 64 位整数编号以及历史编号兼容转换。"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping


# 保留演示数据原有的可读编号，迁移后仍能通过旧编号访问同一条数据。
KNOWN_IDENTIFIER_IDS: dict[str, int] = {
    "PT-CARDIO": 200000000000000001,
    "PT-GASTRO": 200000000000000002,
    "PT-LOW": 200000000000000003,
    "DEMO-D-001": 100000000000000001,
    "DEMO-D-002": 100000000000000002,
}


def stable_identifier(value: str, namespace: str = "default") -> int:
    """把历史字符串编号稳定转换为正数，保证重复迁移得到相同结果。"""
    raw_value = f"{namespace}:{value}".encode("utf-8")
    # 使用 62 位空间避免超过 MySQL BIGINT 有符号整数的最大值。
    hashed = int.from_bytes(hashlib.sha256(raw_value).digest()[:8], "big")
    return (hashed & ((1 << 62) - 1)) or 1


def identifier_to_bigint(
    value: str | int | None,
    *,
    namespace: str = "default",
    aliases: Mapping[str, int] | None = None,
) -> int | None:
    """把接口或历史数据中的编号转换为数据库使用的 BIGINT。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    normalized = str(value).strip()
    if not normalized:
        return None
    selected_aliases = aliases or KNOWN_IDENTIFIER_IDS
    if normalized in selected_aliases:
        return selected_aliases[normalized]
    try:
        return int(normalized)
    except ValueError:
        return stable_identifier(normalized, namespace)


def identifier_text(value: int | str | None) -> str | None:
    """把数据库编号转换为接口层统一使用的字符串表现形式。"""
    return None if value is None else str(value)
