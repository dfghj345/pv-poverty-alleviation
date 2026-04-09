import asyncio
import asyncpg

from data_pipeline.core.config import pipeline_settings


async def main():
    conn = await asyncpg.connect(dsn=pipeline_settings.pipeline_database_url)
    print("connected")

    val = await conn.fetchval("SELECT 1;")
    print("select result:", val)

    await conn.execute("SELECT current_database();")
    print("query ok")

    await conn.close()
    print("closed")


asyncio.run(main())
