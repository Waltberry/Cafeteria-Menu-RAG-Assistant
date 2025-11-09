import time, os, sys
import psycopg

dsn = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@db:5432/menu_rag")
dsn = dsn.replace("+psycopg","")

for i in range(30):
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                print("DB is ready.")
                sys.exit(0)
    except Exception as e:
        print("Waiting for DB...", str(e))
        time.sleep(2)

print("DB not ready after timeout.", file=sys.stderr)
sys.exit(1)
