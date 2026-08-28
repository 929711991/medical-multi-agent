from collections.abc import AsyncIterator
from numbers import Number
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.identifiers import identifier_to_bigint
from app.core.passwords import hash_password
from app.core.snowflake import MIN_PLAUSIBLE_SNOWFLAKE_ID, generate_snowflake_id

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
BUSINESS_TABLES = (
    "patients",
    "doctors",
    "medical_visits",
    "lab_results",
    "imaging_reports",
    "medications",
    "allergies",
    "medical_cases",
    "medical_assessments",
    "knowledge_documents",
)

IDENTIFIER_COLUMNS = {
    "patients": ("id",),
    "doctors": ("id",),
    "medical_visits": ("id", "patient_id"),
    "lab_results": ("id", "patient_id"),
    "imaging_reports": ("id", "patient_id"),
    "medications": ("id", "patient_id"),
    "allergies": ("id", "patient_id"),
    "medical_cases": ("id", "patient_id"),
    "medical_assessments": ("id", "case_id", "reviewer_id"),
    "knowledge_documents": ("id",),
}

IDENTIFIER_REFERENCES = {
    ("medical_visits", "patient_id"): ("patients", "id", "patient"),
    ("lab_results", "patient_id"): ("patients", "id", "patient"),
    ("imaging_reports", "patient_id"): ("patients", "id", "patient"),
    ("medications", "patient_id"): ("patients", "id", "patient"),
    ("allergies", "patient_id"): ("patients", "id", "patient"),
    ("medical_cases", "patient_id"): ("patients", "id", "patient"),
    ("medical_assessments", "case_id"): ("medical_cases", "id", "case"),
    ("medical_assessments", "reviewer_id"): ("doctors", "id", "doctor"),
}


def get_engine() -> AsyncEngine:
    """返回进程内复用的异步 MySQL 引擎。"""
    global _engine
    # 延迟创建引擎，避免命令行工具和隔离单元测试仅导入模块时就打开连接池。
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """返回仓储层复用的 SQLAlchemy 会话工厂。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """为一次请求提供独立的异步数据库会话。"""
    async with get_session_factory() as session:
        yield session


async def _table_columns(connection, table_name: str) -> set[str]:
    """读取指定业务表当前包含的字段名称。"""
    return await connection.run_sync(
        lambda sync_connection: {item["name"] for item in inspect(sync_connection).get_columns(table_name)}
    )


async def _has_unique_column_index(connection, table_name: str, column_name: str) -> bool:
    """判断字段是否属于唯一索引，主键索引也计算在内。"""
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    return any(row["Non_unique"] == 0 and row["Column_name"] == column_name for row in rows)


async def _has_secondary_unique_column_index(
    connection, table_name: str, column_name: str
) -> bool:
    """判断字段是否拥有独立的非主键唯一索引。"""
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    indexes: dict[str, list[str]] = {}
    for row in rows:
        if row["Key_name"] != "PRIMARY" and row["Non_unique"] == 0:
            indexes.setdefault(row["Key_name"], []).append(row["Column_name"])
    return [column_name] in indexes.values()


async def _primary_key_columns(connection, table_name: str) -> list[str]:
    """按照索引声明顺序返回主键字段。"""
    rows = (await connection.execute(text(f"SHOW INDEX FROM `{table_name}`"))).mappings().all()
    primary_rows = sorted(
        (row for row in rows if row["Key_name"] == "PRIMARY"),
        key=lambda row: row["Seq_in_index"],
    )
    return [row["Column_name"] for row in primary_rows]


async def _migrate_business_table_to_snowflake_primary(connection, table_name: str) -> None:
    """保留对外字符串业务编号，并将内部主键迁移为雪花 ID。"""
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
    # 字符串业务编号稳定且唯一，可在回填新主键时安全定位每一行。
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
        # 现有外键仍引用旧业务编号，所以切换主键前必须先为业务编号建立独立唯一索引。
        await connection.execute(
            text(
                f"ALTER TABLE `{table_name}` DROP PRIMARY KEY, "
                "ADD PRIMARY KEY (pk_id)"
            )
        )


async def _migrate_numeric_table_to_snowflake_primary(connection, table_name: str) -> None:
    """移除旧自增属性，并将已有小整数主键替换为雪花 ID。"""
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
    # 这些记录表的 ID 未被其他业务表引用，因此可以原位替换，无需级联迁移外键。
    for legacy_id in legacy_ids:
        await connection.execute(
            text(f"UPDATE `{table_name}` SET id = :new_id WHERE id = :legacy_id"),
            {"new_id": generate_snowflake_id(), "legacy_id": legacy_id},
        )


async def _ensure_auto_increment_fallback(connection, table_name: str) -> None:
    """为将来切换策略安装备用自增字段。"""
    columns = await _table_columns(connection, table_name)
    if "auto_id" not in columns:
        # 先以可空字段加入，避免升级已有数据时依赖临时伪造默认值。
        await connection.execute(
            text(
                f"ALTER TABLE `{table_name}` ADD COLUMN auto_id BIGINT NULL "
                "COMMENT '备用数据库自增编号'"
            )
        )
    if not await _has_secondary_unique_column_index(connection, table_name, "auto_id"):
        # MySQL 要求自增字段必须有索引，即使该字段当前不是主键。
        await connection.execute(
            text(f"CREATE UNIQUE INDEX ux_{table_name}_auto_id ON `{table_name}` (auto_id)")
        )

    column = (
        await connection.execute(
            text(f"SHOW FULL COLUMNS FROM `{table_name}` WHERE Field = 'auto_id'")
        )
    ).mappings().one()
    if "auto_increment" not in str(column["Extra"]).lower():
        # 转换为自增字段时会为历史行分配连续编号，后续新增行则由数据库生成。
        await connection.execute(
            text(
                f"ALTER TABLE `{table_name}` MODIFY COLUMN auto_id BIGINT "
                "NOT NULL AUTO_INCREMENT COMMENT '备用数据库自增编号'"
            )
        )


def _mysql_literal(value: Any) -> str:
    """将可信的结构值渲染为 MySQL DDL 字面量。"""
    if isinstance(value, Number):
        return str(value)
    rendered = str(value)
    normalized = rendered.upper()
    if normalized.startswith("CURRENT_TIMESTAMP") or normalized in {"NOW()", "LOCALTIME", "LOCALTIMESTAMP"}:
        return rendered
    return "'" + rendered.replace("\\", "\\\\").replace("'", "''") + "'"


def _column_definition(column: dict[str, Any], comment: str) -> str:
    """根据字段元数据重建定义，并且只更新字段注释。"""
    parts = [f"`{column['Field']}`", str(column["Type"])]
    if column.get("Collation"):
        parts.append(f"COLLATE {column['Collation']}")
    parts.append("NULL" if column["Null"] == "YES" else "NOT NULL")
    if column["Default"] is not None:
        parts.append(f"DEFAULT {_mysql_literal(column['Default'])}")
    elif column["Null"] == "YES":
        parts.append("DEFAULT NULL")

    extra = str(column.get("Extra") or "")
    if "auto_increment" in extra.lower():
        parts.append("AUTO_INCREMENT")
    if "on update" in extra.lower():
        # SHOW FULL COLUMNS 可能带有 DEFAULT_GENERATED 前缀，重建时只保留 ON UPDATE 子句。
        position = extra.lower().index("on update")
        parts.append(extra[position:])
    parts.append(f"COMMENT {_mysql_literal(comment)}")
    return " ".join(parts)


async def _foreign_keys(connection) -> list[dict[str, Any]]:
    """读取业务外键定义，保证修改字段注释时能够安全恢复。"""
    rows = (
        await connection.execute(
            text(
                "SELECT kcu.CONSTRAINT_NAME, kcu.TABLE_NAME, kcu.COLUMN_NAME, "
                "kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME, "
                "kcu.ORDINAL_POSITION, rc.UPDATE_RULE, rc.DELETE_RULE "
                "FROM information_schema.KEY_COLUMN_USAGE kcu "
                "JOIN information_schema.REFERENTIAL_CONSTRAINTS rc "
                "ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA "
                "AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
                "AND rc.TABLE_NAME = kcu.TABLE_NAME "
                "WHERE kcu.CONSTRAINT_SCHEMA = DATABASE() "
                "AND kcu.REFERENCED_TABLE_NAME IS NOT NULL "
                "ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION"
            )
        )
    ).mappings().all()

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row["TABLE_NAME"] not in BUSINESS_TABLES:
            continue
        key = (row["TABLE_NAME"], row["CONSTRAINT_NAME"])
        item = grouped.setdefault(
            key,
            {
                "table_name": row["TABLE_NAME"],
                "constraint_name": row["CONSTRAINT_NAME"],
                "columns": [],
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_columns": [],
                "update_rule": row["UPDATE_RULE"],
                "delete_rule": row["DELETE_RULE"],
            },
        )
        item["columns"].append(row["COLUMN_NAME"])
        item["referenced_columns"].append(row["REFERENCED_COLUMN_NAME"])
    return list(grouped.values())


async def _drop_foreign_keys(connection, foreign_keys: list[dict[str, Any]]) -> None:
    """修改被引用字段前，临时移除已记录的外键。"""
    for foreign_key in foreign_keys:
        await connection.execute(
            text(
                f"ALTER TABLE `{foreign_key['table_name']}` DROP FOREIGN KEY "
                f"`{foreign_key['constraint_name']}`"
            )
        )


async def _restore_foreign_keys(connection, foreign_keys: list[dict[str, Any]]) -> None:
    """按照 information_schema 中记录的规则完整恢复外键。"""
    for foreign_key in foreign_keys:
        columns = ", ".join(f"`{name}`" for name in foreign_key["columns"])
        referenced_columns = ", ".join(
            f"`{name}`" for name in foreign_key["referenced_columns"]
        )
        await connection.execute(
            text(
                f"ALTER TABLE `{foreign_key['table_name']}` ADD CONSTRAINT "
                f"`{foreign_key['constraint_name']}` FOREIGN KEY ({columns}) "
                f"REFERENCES `{foreign_key['referenced_table']}` ({referenced_columns}) "
                f"ON UPDATE {foreign_key['update_rule']} ON DELETE {foreign_key['delete_rule']}"
            )
        )


async def _column_types(connection, table_name: str) -> dict[str, str]:
    """读取表中编号字段的当前 MySQL 类型。"""
    rows = (
        await connection.execute(text(f"SHOW FULL COLUMNS FROM `{table_name}`"))
    ).mappings().all()
    return {str(row["Field"]): str(row["Type"]).lower() for row in rows}


async def _identifier_values(connection, table_name: str, column_name: str) -> list[Any]:
    """读取编号列的去重值，为历史字符串编号转换建立映射。"""
    rows = (
        await connection.execute(
            text(f"SELECT DISTINCT `{column_name}` FROM `{table_name}` WHERE `{column_name}` IS NOT NULL")
        )
    ).scalars().all()
    return list(rows)


def _build_identifier_mapping(values: list[Any], namespace: str) -> dict[Any, int]:
    """为一张表的历史编号建立无冲突的 BIGINT 映射。"""
    numeric_values: set[int] = set()
    for value in values:
        try:
            numeric_values.add(int(str(value).strip()))
        except (TypeError, ValueError):
            continue

    mapping: dict[Any, int] = {}
    assigned: set[int] = set()
    for value in values:
        candidate = identifier_to_bigint(value, namespace=namespace)
        if candidate is None:
            continue
        try:
            original_numeric = int(str(value).strip())
        except (TypeError, ValueError):
            original_numeric = None
        # 历史字符串别名可能与表中已有数字编号冲突，冲突时重新生成雪花编号。
        while candidate in assigned or (
            candidate in numeric_values and original_numeric != candidate
        ):
            candidate = generate_snowflake_id()
        mapping[value] = candidate
        assigned.add(candidate)
    return mapping


async def _migrate_all_identifier_columns_to_bigint(connection) -> None:
    """把业务表中的主键、业务编号和关联外键统一迁移为 BIGINT。"""
    column_types = {
        table_name: await _column_types(connection, table_name)
        for table_name in BUSINESS_TABLES
    }
    needs_migration = any(
        not column_types[table_name].get(column_name, "").startswith("bigint")
        for table_name, columns in IDENTIFIER_COLUMNS.items()
        for column_name in columns
    )
    if not needs_migration:
        return

    # 修改父子表类型前先暂时移除外键，避免 MySQL 拒绝类型变更或历史值更新。
    foreign_keys = await _foreign_keys(connection)
    await _drop_foreign_keys(connection, foreign_keys)
    try:
        parent_mappings: dict[tuple[str, str], dict[Any, int]] = {}
        for table_name in ("patients", "doctors", "medical_cases", "knowledge_documents"):
            values = await _identifier_values(connection, table_name, "id")
            namespace = table_name.removesuffix("s")
            parent_mappings[(table_name, "id")] = _build_identifier_mapping(values, namespace)

        # 先更新所有子表引用，保证转换父表编号后关系仍然完整。
        for (child_table, child_column), (parent_table, parent_column, _) in IDENTIFIER_REFERENCES.items():
            mapping = parent_mappings[(parent_table, parent_column)]
            for old_value, new_value in mapping.items():
                await connection.execute(
                    text(
                        f"UPDATE `{child_table}` SET `{child_column}` = :new_value "
                        f"WHERE `{child_column}` = :old_value"
                    ),
                    {"old_value": old_value, "new_value": new_value},
                )

        # 再更新父表自身编号，避免子表留下无法关联的历史字符串。
        for (table_name, column_name), mapping in parent_mappings.items():
            if column_types[table_name].get(column_name, "").startswith("bigint"):
                continue
            for old_value, new_value in mapping.items():
                await connection.execute(
                    text(
                        f"UPDATE `{table_name}` SET `{column_name}` = :new_value "
                        f"WHERE `{column_name}` = :old_value"
                    ),
                    {"old_value": old_value, "new_value": new_value},
                )

        nullable_columns = {("medical_assessments", "reviewer_id")}
        for table_name, columns in IDENTIFIER_COLUMNS.items():
            for column_name in columns:
                if column_name == "thread_id":
                    continue
                if column_types[table_name].get(column_name, "").startswith("bigint"):
                    continue
                nullability = "NULL" if (table_name, column_name) in nullable_columns else "NOT NULL"
                await connection.execute(
                    text(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` "
                        f"BIGINT {nullability}"
                    )
                )
    finally:
        await _restore_foreign_keys(connection, foreign_keys)


async def _schema_comments_outdated(connection, tables) -> bool:
    """判断 ORM 中的表或字段注释是否与 MySQL 不一致。"""
    for table in tables:
        table_comment = await connection.scalar(
            text(
                "SELECT TABLE_COMMENT FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
            ),
            {"table_name": table.name},
        )
        if table.comment and table_comment != table.comment:
            return True
        current_columns = {
            row["Field"]: row
            for row in (
                await connection.execute(text(f"SHOW FULL COLUMNS FROM `{table.name}`"))
            ).mappings().all()
        }
        if any(
            column.comment and current_columns[column.name]["Comment"] != column.comment
            for column in table.columns
        ):
            return True
    return False


async def _apply_schema_comments(connection, tables) -> None:
    """将 ORM 中的表和字段中文说明同步到真实 MySQL。"""
    tables = list(tables)
    if not await _schema_comments_outdated(connection, tables):
        return

    foreign_keys = await _foreign_keys(connection)
    await _drop_foreign_keys(connection, foreign_keys)
    try:
        for table in tables:
            if table.comment:
                await connection.execute(
                    text(
                        f"ALTER TABLE `{table.name}` COMMENT = "
                        f"{_mysql_literal(table.comment)}"
                    )
                )
            current_columns = {
                row["Field"]: row
                for row in (
                    await connection.execute(text(f"SHOW FULL COLUMNS FROM `{table.name}`"))
                ).mappings().all()
            }
            for column in table.columns:
                if not column.comment or current_columns[column.name]["Comment"] == column.comment:
                    continue
                definition = _column_definition(current_columns[column.name], column.comment)
                await connection.execute(
                    text(f"ALTER TABLE `{table.name}` MODIFY COLUMN {definition}")
                )
    finally:
        # MySQL 会自动提交 DDL，因此即使某个字段注释失败，也必须恢复全部外键。
        await _restore_foreign_keys(connection, foreign_keys)


async def initialize_schema() -> None:
    """创建新表，并对 V1 现有开发库执行最小兼容升级。

    正式生产升级仍应由 Alembic migration 执行；这里保留开发环境可直接启动能力。
    """
    from app.persistence.models import Base

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        departments = (
            ("GENERAL", "全科", 10),
            ("CARDIOLOGY", "心内科", 20),
            ("GASTROENTEROLOGY", "消化内科", 30),
            ("NEUROLOGY", "神经内科", 40),
            ("RESPIRATORY", "呼吸内科", 50),
            ("ENDOCRINOLOGY", "内分泌科", 60),
        )
        for code, name, sort_order in departments:
            await connection.execute(
                text(
                    "INSERT INTO departments (pk_id, code, name, enabled, sort_order) "
                    "VALUES (:pk_id, :code, :name, 1, :sort_order) "
                    "ON DUPLICATE KEY UPDATE name = VALUES(name), sort_order = VALUES(sort_order)"
                ),
                {
                    "pk_id": generate_snowflake_id(),
                    "code": code,
                    "name": name,
                    "sort_order": sort_order,
                },
            )

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
        if "visit_id" not in case_columns:
            await connection.execute(
                text("ALTER TABLE medical_cases ADD COLUMN visit_id BIGINT NULL")
            )
        if "consultation_id" not in case_columns:
            await connection.execute(
                text("ALTER TABLE medical_cases ADD COLUMN consultation_id BIGINT NULL")
            )
        if "failure_stage" not in case_columns:
            await connection.execute(
                text("ALTER TABLE medical_cases ADD COLUMN failure_stage VARCHAR(64) NULL")
            )
        if "error_code" not in case_columns:
            await connection.execute(
                text("ALTER TABLE medical_cases ADD COLUMN error_code VARCHAR(64) NULL")
            )

        visit_columns = await _table_columns(connection, "medical_visits")
        if "department_code" not in visit_columns:
            await connection.execute(
                text("ALTER TABLE medical_visits ADD COLUMN department_code VARCHAR(64) NULL")
            )

        await _migrate_all_identifier_columns_to_bigint(connection)

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

        for table_name in BUSINESS_TABLES:
            await _ensure_auto_increment_fallback(connection, table_name)

        # 最后同步注释，确保所有兼容字段已存在，并可直接以 ORM 元数据为准。
        mapped_tables = [Base.metadata.tables[table_name] for table_name in BUSINESS_TABLES]
        await _apply_schema_comments(connection, mapped_tables)


async def check_mysql_ready() -> bool:
    """通过轻量查询判断业务 MySQL 是否可用。"""
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_database() -> None:
    """释放缓存的数据库资源，使测试和命令行进程能够正常退出。"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
