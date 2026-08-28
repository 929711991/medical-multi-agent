import asyncio

from app.persistence.database import close_database, initialize_schema


async def main() -> None:
    """初始化业务表结构，并在命令行进程结束前释放数据库连接。"""
    await initialize_schema()
    await close_database()
    print("medical_ai 业务表结构初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
