from contextlib import asynccontextmanager
import re
from typing import AsyncIterator

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.mysql.asyncmy import AsyncMySaver

from app.core.config import get_settings


@asynccontextmanager
async def mysql_checkpointer() -> AsyncIterator[AsyncMySaver]:
    async with AsyncMySaver.from_conn_string(get_settings().checkpoint_url) as saver:
        await saver.setup()
        await _ensure_mysql8_checkpoint_collation(saver)
        yield saver


def memory_checkpointer() -> InMemorySaver:
    return InMemorySaver()


async def _ensure_mysql8_checkpoint_collation(saver: AsyncMySaver) -> None:
    """统一 Checkpoint 表与该包 JSON_TABLE 临时列的排序规则。"""
    table_names = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")
    database_name = get_settings().mysql_graph_database
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise ValueError("MYSQL_GRAPH_DATABASE 只能包含字母、数字和下划线")
    async with saver.conn.cursor() as cursor:
        await cursor.execute(
            f"ALTER DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
        for table_name in table_names:
            await cursor.execute(
                "SELECT TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                (table_name,),
            )
            row = await cursor.fetchone()
            collation = row[0] if isinstance(row, tuple) else row.get("TABLE_COLLATION") if row else None
            if collation != "utf8mb4_0900_ai_ci":
                await cursor.execute(
                    f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
            await cursor.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME = 'checkpoint_ns_hash_md5'",
                (table_name,),
            )
            column_row = await cursor.fetchone()
            column_exists = column_row[0] if isinstance(column_row, tuple) else next(iter(column_row.values()))
            if not column_exists:
                # 保留 Checkpointer 依赖的二进制列，同时提供便于人工查看的只读 MD5 明文字段。
                await cursor.execute(
                    f"ALTER TABLE `{table_name}` ADD COLUMN `checkpoint_ns_hash_md5` "
                    "CHAR(32) CHARACTER SET ascii "
                    "GENERATED ALWAYS AS (LOWER(HEX(`checkpoint_ns_hash`))) VIRTUAL"
                )
            await cursor.execute(
                "SELECT EXTRA FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME = 'checkpoint_ns_hash'",
                (table_name,),
            )
            visibility_row = await cursor.fetchone()
            extra = (
                visibility_row[0]
                if isinstance(visibility_row, tuple)
                else visibility_row.get("EXTRA", "")
            )
            if "INVISIBLE" in extra.upper():
                # 保持内部二进制列可见，并用旁边的明文列辅助人工核对。
                await cursor.execute(
                    f"ALTER TABLE `{table_name}` ALTER COLUMN `checkpoint_ns_hash` SET VISIBLE"
                )
