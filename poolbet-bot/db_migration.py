import asyncio
import asyncpg

db_url = "postgresql://postgres.uchbkfibihvnwiaxegpk:LkcWQcgoNjX%23Chr^59LbX9@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"

async def main():
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT false;")
        print("Migrazione is_banned completata con successo sulla tabella remote.")
    except Exception as e:
        print(f"Errore: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
