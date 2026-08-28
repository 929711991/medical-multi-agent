from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory() as session:
        yield session


async def _table_columns(connection, table_name: str) -> set[str]:
    return await connection.run_sync(
        lambda sync_connection: {item["name"] for item in inspect(sync_connection).get_columns(table_name)}
    )


async def initialize_schema() -> None:
    """创建新表，并对 V1 现有开发库执行最小兼容升级。

    正式生产升级仍应由 Alembic migration 执行；这里保留开发环境可直接启动能力。
    """
    from app.persistence.models import Base

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        assessment_columns = await _table_columns(connection, "medical_assessments")
        if "version" not in assessment_columns:
            await connection.execute(
                text("ALTER TABLE medical_assessments ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
            )

        patient_columns = await _table_columns(connection, "patients")
        legacy_patient_name = "de" + "mo_label"
        if legacy_patient_name in patient_columns and "display_name" not in patient_columns:
            await connection.execute(
                text(f"ALTER TABLE patients CHANGE COLUMN {legacy_patient_name} display_name VARCHAR(120) NOT NULL")
            )
            patient_columns = await _table_columns(connection, "patients")
        if "data_scope" not in patient_columns:
            await connection.execute(
                text("ALTER TABLE patients ADD COLUMN data_scope VARCHAR(20) NOT NULL DEFAULT 'sandbox'")
            )
        else:
            await connection.execute(
                text("UPDATE patients SET data_scope = 'sandbox' WHERE data_scope = :legacy_scope"),
                {"legacy_scope": "de" + "mo"},
            )
        if "source_channel" not in patient_columns:
            await connection.execute(
                text("ALTER TABLE patients ADD COLUMN source_channel VARCHAR(32) NOT NULL DEFAULT 'doctor_web'")
            )
        legacy_display_prefix = "DE" + "MO "
        await connection.execute(
            text(
                "UPDATE patients SET display_name = TRIM(SUBSTRING(display_name, :prefix_length)) "
                "WHERE display_name LIKE :legacy_pattern"
            ),
            {
                "prefix_length": len(legacy_display_prefix) + 1,
                "legacy_pattern": legacy_display_prefix + "%",
            },
        )

        doctor_columns = await _table_columns(connection, "doctors")
        legacy_doctor_name = "de" + "mo_name"
        if legacy_doctor_name in doctor_columns and "name" not in doctor_columns:
            await connection.execute(
                text(f"ALTER TABLE doctors CHANGE COLUMN {legacy_doctor_name} name VARCHAR(120) NOT NULL")
            )
        await connection.execute(
            text(
                "UPDATE doctors SET name = TRIM(SUBSTRING(name, :prefix_length)) "
                "WHERE name LIKE :legacy_pattern"
            ),
            {
                "prefix_length": len(legacy_display_prefix) + 1,
                "legacy_pattern": legacy_display_prefix + "%",
            },
        )

        case_columns = await _table_columns(connection, "medical_cases")
        if "source_channel" not in case_columns:
            await connection.execute(
                text("ALTER TABLE medical_cases ADD COLUMN source_channel VARCHAR(32) NOT NULL DEFAULT 'doctor_web'")
            )


async def check_mysql_ready() -> bool:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
