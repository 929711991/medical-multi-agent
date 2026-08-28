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
        if "data_scope" not in patient_columns:
            await connection.execute(
                text("ALTER TABLE patients ADD COLUMN data_scope VARCHAR(20) NOT NULL DEFAULT 'demo'")
            )
        if "source_channel" not in patient_columns:
            await connection.execute(
                text("ALTER TABLE patients ADD COLUMN source_channel VARCHAR(32) NOT NULL DEFAULT 'doctor_web'")
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
