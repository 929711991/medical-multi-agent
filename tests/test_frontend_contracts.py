import pytest
from pydantic import ValidationError

from app.schemas.diagnosis import DoctorReviewRequest


def test_review_contract_requires_version_and_does_not_accept_reviewer_identity() -> None:
    payload = DoctorReviewRequest.model_validate({"action": "approve", "expected_version": 3})
    assert payload.expected_version == 3
    assert "reviewer_id" not in payload.model_dump()


def test_edit_review_requires_structured_result() -> None:
    with pytest.raises(ValidationError):
        DoctorReviewRequest.model_validate({"action": "edit", "expected_version": 1})
