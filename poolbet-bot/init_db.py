import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def init_db():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        with open("db/schema.sql", "r") as f:
            schema = f.read()
        print("Applying schema.sql...")
        await conn.execute(schema)
        print("Database schema successfully applied.")
        await conn.close()
    except Exception as e:
        print(f"Error applying schema: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
