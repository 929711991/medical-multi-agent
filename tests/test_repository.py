import pytest

from app.persistence.database import get_session_factory
from app.persistence.repositories import PatientRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_reads_seeded_patient() -> None:
    async with get_session_factory()() as session:
        result = await PatientRepository(session).all_records("PT-CARDIO")
    assert result["found"] is True
    assert result["records"]["visits"]
    assert result["records"]["labs"]

