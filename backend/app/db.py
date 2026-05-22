import os
import asyncpg
import asyncio


async def init_db(app):
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("POSTGRES_DB", "energygrid")
    
    print(f"[DB] Attempting to connect to {host}:{port}/{db} as {user}")
    
    retries = 15
    for attempt in range(retries):
        try:
            pool = await asyncpg.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db,
                min_size=1,
                max_size=10,
                timeout=5,
                command_timeout=10
            )
            app.state.db = pool
            print("[DB] ✓ Database pool connected successfully")
            return
        except Exception as e:
            if attempt < retries - 1:
                wait_time = min(2 ** attempt, 8)
                print(f"[DB] Attempt {attempt+1}/{retries} failed, retrying in {wait_time}s: {type(e).__name__}")
                await asyncio.sleep(wait_time)
            else:
                print(f"[DB] ✗ Failed after {retries} attempts: {e}")
                app.state.db = None
                return


async def close_db(app):
    pool = getattr(app.state, "db", None)
    if pool:
        await pool.close()
        print("[DB] Pool closed")
