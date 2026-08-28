from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import BigInteger

from app.core.snowflake import MIN_PLAUSIBLE_SNOWFLAKE_ID, SnowflakeGenerator
from app.persistence.models import (
    Allergy,
    Doctor,
    ImagingReport,
    KnowledgeDocument,
    LabResult,
    MedicalAssessment,
    MedicalCase,
    MedicalVisit,
    Medication,
    Patient,
)


def test_snowflake_ids_are_unique_and_ordered() -> None:
    generator = SnowflakeGenerator(worker_id=7)
    ids = [generator.next_id() for _ in range(10_000)]

    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert ids[0] >= MIN_PLAUSIBLE_SNOWFLAKE_ID


def test_snowflake_generator_is_thread_safe() -> None:
    generator = SnowflakeGenerator(worker_id=8)
    with ThreadPoolExecutor(max_workers=8) as executor:
        ids = list(executor.map(lambda _: generator.next_id(), range(20_000)))

    assert len(ids) == len(set(ids))


def test_every_business_table_uses_a_snowflake_primary_key() -> None:
    business_models = (Patient, Doctor, MedicalCase, KnowledgeDocument)
    numeric_models = (
        MedicalVisit,
        LabResult,
        ImagingReport,
        Medication,
        Allergy,
        MedicalAssessment,
    )

    for model in business_models:
        primary_key = list(model.__table__.primary_key.columns)
        assert [column.name for column in primary_key] == ["pk_id"]
        assert isinstance(primary_key[0].type, BigInteger)
        assert model.__table__.c.id.unique
        assert model.__table__.c.auto_id.unique
        assert model.__table__.comment
        assert all(column.comment for column in model.__table__.columns)

    for model in numeric_models:
        primary_key = list(model.__table__.primary_key.columns)
        assert [column.name for column in primary_key] == ["id"]
        assert isinstance(primary_key[0].type, BigInteger)
        assert primary_key[0].autoincrement is False
        assert model.__table__.c.auto_id.unique
        assert model.__table__.comment
        assert all(column.comment for column in model.__table__.columns)
