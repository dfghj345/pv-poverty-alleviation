import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        user="pipeline_user",
        password="pipeline",
        database="pipeline_db",
        host="127.0.0.1",
        port=5432,
    )
    print("connected")

    val = await conn.fetchval("SELECT 1;")
    print("select result:", val)

    await conn.execute("SELECT current_database();")
    print("query ok")

    await conn.close()
    print("closed")


asyncio.run(main())