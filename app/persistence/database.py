from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.core.snowflake import MIN_PLAUSIBLE_SNOWFLAKE_ID, generate_snowflake_id

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


async def _has_unique_column_index(connection, table_name: str, column_name: str) -> bool:
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    return any(row["Non_unique"] == 0 and row["Column_name"] == column_name for row in rows)


async def _has_secondary_unique_column_index(
    connection, table_name: str, column_name: str
) -> bool:
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    indexes: dict[str, list[str]] = {}
    for row in rows:
        if row["Key_name"] != "PRIMARY" and row["Non_unique"] == 0:
            indexes.setdefault(row["Key_name"], []).append(row["Column_name"])
    return [column_name] in indexes.values()


async def _primary_key_columns(connection, table_name: str) -> list[str]:
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    primary_rows = sorted(
        (row for row in rows if row["Key_name"] == "PRIMARY"),
        key=lambda row: row["Seq_in_index"],
    )
    return [row["Column_name"] for row in primary_rows]


async def _migrate_business_table_to_snowflake_primary(connection, table_name: str) -> None:
    """Keep the public string ID and move the internal primary key to a Snowflake BIGINT."""
    columns = await _table_columns(connection, table_name)
    if "pk_id" not in columns:
        await connection.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN pk_id BIGINT NULL"))

    rows = (
        await connection.execute(
            text(
                f"SELECT id FROM `{table_name}` "
                "WHERE pk_id IS NULL OR pk_id < :snowflake_floor ORDER BY id"
            ),
            {"snowflake_floor": MIN_PLAUSIBLE_SNOWFLAKE_ID},
        )
    ).mappings().all()
    for row in rows:
        await connection.execute(
            text(f"UPDATE `{table_name}` SET pk_id = :pk_id WHERE id = :business_id"),
            {"pk_id": generate_snowflake_id(), "business_id": row["id"]},
        )

    await connection.execute(
        text(f"ALTER TABLE `{table_name}` MODIFY COLUMN pk_id BIGINT NOT NULL")
    )
    if not await _has_secondary_unique_column_index(connection, table_name, "id"):
        await connection.execute(
            text(f"CREATE UNIQUE INDEX ux_{table_name}_business_id ON `{table_name}` (id)")
        )
    if await _primary_key_columns(connection, table_name) != ["pk_id"]:
        await connection.execute(
            text(
                f"ALTER TABLE `{table_name}` DROP PRIMARY KEY, "
                "ADD PRIMARY KEY (pk_id)"
            )
        )


async def _migrate_numeric_table_to_snowflake_primary(connection, table_name: str) -> None:
    """Remove AUTO_INCREMENT and replace legacy small IDs with Snowflake IDs."""
    await connection.execute(
        text(f"ALTER TABLE `{table_name}` MODIFY COLUMN id BIGINT NOT NULL")
    )
    legacy_ids = (
        await connection.execute(
            text(
                f"SELECT id FROM `{table_name}` "
                "WHERE id < :snowflake_floor ORDER BY id"
            ),
            {"snowflake_floor": MIN_PLAUSIBLE_SNOWFLAKE_ID},
        )
    ).scalars().all()
    for legacy_id in legacy_ids:
        await connection.execute(
            text(f"UPDATE `{table_name}` SET id = :new_id WHERE id = :legacy_id"),
            {"new_id": generate_snowflake_id(), "legacy_id": legacy_id},
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
            doctor_columns = await _table_columns(connection, "doctors")
        if "account" not in doctor_columns:
            await connection.execute(text("ALTER TABLE doctors ADD COLUMN account VARCHAR(64) NULL"))
        if "password_hash" not in doctor_columns:
            await connection.execute(text("ALTER TABLE doctors ADD COLUMN password_hash VARCHAR(255) NULL"))
        if not await _has_unique_column_index(connection, "doctors", "account"):
            await connection.execute(text("CREATE UNIQUE INDEX ux_doctors_account ON doctors (account)"))
        settings = get_settings()
        await connection.execute(
            text(
                "UPDATE doctors SET account = :account, password_hash = :password_hash "
                "WHERE id = :doctor_id AND (account IS NULL OR account = '' OR password_hash IS NULL)"
            ),
            {
                "account": settings.login_account,
                "password_hash": hash_password(settings.login_password),
                "doctor_id": settings.login_doctor_id,
            },
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

        for table_name in ("patients", "doctors", "medical_cases", "knowledge_documents"):
            await _migrate_business_table_to_snowflake_primary(connection, table_name)
        for table_name in (
            "medical_visits",
            "lab_results",
            "imaging_reports",
            "medications",
            "allergies",
            "medical_assessments",
        ):
            await _migrate_numeric_table_to_snowflake_primary(connection, table_name)


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
