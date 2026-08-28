from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.snowflake import MIN_PLAUSIBLE_SNOWFLAKE_ID, generate_snowflake_id
from app.persistence.database import BUSINESS_TABLES, get_engine, get_session_factory, initialize_schema
from app.persistence.models import Base, MedicalVisit, Patient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_business_tables_use_snowflake_primary_keys() -> None:
    await initialize_schema()
    business_tables = ("patients", "doctors", "medical_cases", "knowledge_documents")
    numeric_tables = (
        "medical_visits",
        "lab_results",
        "imaging_reports",
        "medications",
        "allergies",
        "medical_assessments",
    )

    async with get_engine().connect() as connection:
        for table_name, column_name in (
            ("patients", "id"),
            ("doctors", "id"),
            ("medical_cases", "id"),
            ("medical_visits", "patient_id"),
            ("lab_results", "patient_id"),
            ("imaging_reports", "patient_id"),
            ("medications", "patient_id"),
            ("allergies", "patient_id"),
            ("medical_assessments", "case_id"),
            ("medical_assessments", "reviewer_id"),
            ("knowledge_documents", "id"),
        ):
            column = (
                await connection.execute(
                    text(f"SHOW COLUMNS FROM `{table_name}` WHERE Field = '{column_name}'")
                )
            ).mappings().one()
            assert column["Type"] == "bigint"

        for table_name in business_tables:
            indexes = (
                await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))
            ).mappings().all()
            primary_columns = [
                row["Column_name"] for row in indexes if row["Key_name"] == "PRIMARY"
            ]
            assert primary_columns == ["pk_id"]
            assert any(
                row["Key_name"] != "PRIMARY"
                and row["Non_unique"] == 0
                and row["Column_name"] == "id"
                for row in indexes
            )
            legacy_count = await connection.scalar(
                text(
                    f"SELECT COUNT(*) FROM `{table_name}` "
                    "WHERE pk_id < :snowflake_floor"
                ),
                {"snowflake_floor": MIN_PLAUSIBLE_SNOWFLAKE_ID},
            )
            assert legacy_count == 0

        for table_name in numeric_tables:
            column = (
                await connection.execute(
                    text(f"SHOW COLUMNS FROM `{table_name}` WHERE Field = 'id'")
                )
            ).mappings().one()
            assert column["Type"] == "bigint"
            assert "auto_increment" not in column["Extra"]
            legacy_count = await connection.scalar(
                text(
                    f"SELECT COUNT(*) FROM `{table_name}` "
                    "WHERE id < :snowflake_floor"
                ),
                {"snowflake_floor": MIN_PLAUSIBLE_SNOWFLAKE_ID},
            )
            assert legacy_count == 0

        for table_name in BUSINESS_TABLES:
            table_comment = await connection.scalar(
                text(
                    "SELECT TABLE_COMMENT FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
                ),
                {"table_name": table_name},
            )
            assert table_comment == Base.metadata.tables[table_name].comment

            columns = {
                row["Field"]: row
                for row in (
                    await connection.execute(text(f"SHOW FULL COLUMNS FROM `{table_name}`"))
                ).mappings().all()
            }
            auto_id = columns["auto_id"]
            assert auto_id["Type"] == "bigint"
            assert auto_id["Null"] == "NO"
            assert "auto_increment" in auto_id["Extra"]
            assert all(
                columns[column.name]["Comment"] == column.comment
                for column in Base.metadata.tables[table_name].columns
            )
            indexes = (
                await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))
            ).mappings().all()
            assert any(
                row["Key_name"] != "PRIMARY"
                and row["Non_unique"] == 0
                and row["Column_name"] == "auto_id"
                for row in indexes
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_assigns_snowflake_ids_to_new_rows() -> None:
    patient_code = generate_snowflake_id()
    async with get_session_factory()() as session:
        patient = Patient(
            id=patient_code,
            display_name="雪花主键测试患者",
            summary_json={"sandbox": True},
            data_scope="sandbox",
            source_channel="test",
        )
        visit = MedicalVisit(
            patient_id=patient_code,
            visit_time=datetime.now(UTC),
            department="测试科室",
            chief_complaint="雪花主键测试",
            record_json={},
        )
        session.add(patient)
        await session.flush()
        session.add(visit)
        await session.flush()

        assert patient.pk_id >= MIN_PLAUSIBLE_SNOWFLAKE_ID
        assert visit.id >= MIN_PLAUSIBLE_SNOWFLAKE_ID
        assert patient.pk_id != visit.id
        await session.refresh(patient)
        await session.refresh(visit)
        assert patient.auto_id > 0
        assert visit.auto_id > 0
        await session.rollback()
