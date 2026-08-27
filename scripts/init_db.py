import asyncio

from app.persistence.database import close_database, initialize_schema


async def main() -> None:
    await initialize_schema()
    await close_database()
    print("medical_ai 业务表结构初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
