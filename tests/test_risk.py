import pytest

from app.safety.risk import screen_risk


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("突发压榨性胸痛伴大汗", "emergency"),
        ("患者意识不清，叫不醒", "emergency"),
        ("口角歪斜并言语不清", "emergency"),
        ("持续胸痛", "high"),
        ("轻微腹痛", "medium"),
        ("轻微鼻塞，无发热", "low"),
    ],
)
def test_risk_rules(text: str, expected: str) -> None:
    assert screen_risk(text).level == expected


def test_rule_does_not_claim_diagnosis() -> None:
    result = screen_risk("严重呼吸困难")
    assert result.level == "emergency"
    assert all("确诊" not in flag for flag in result.red_flags)

