import asyncio
import asyncpg
import os
import sys

# Formato Supabase: postgresql://postgres.[project_ref]:[password]...
db_url = "postgresql://postgres.uchbkfibihvnwiaxegpk:LkcWQcgoNjX%23Chr^59LbX9@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"

async def main():
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key          TEXT PRIMARY KEY,
                value        TEXT NOT NULL,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Tabella system_settings creata con successo.")
        
        # Inserisci alcuni valori di default
        await conn.execute("""
            INSERT INTO system_settings (key, value) VALUES 
            ('tip_fee', '0.05'),
            ('withdraw_fee', '1.0'),
            ('minigame_edge', '0.05')
            ON CONFLICT (key) DO NOTHING;
        """)
        print("Valori di default inseriti.")
    except Exception as e:
        print(f"Errore: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
