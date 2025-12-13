"""Database initialization script.

This script prefers a `DATABASE_URL` environment variable. If a connection
fails due to password/authentication errors it will attempt a fallback using
the `postgres:postgres` credentials (useful for local development when the
system defaults are not configured).
"""
import sys
import os
from sqlalchemy import text, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from shared.database import Base
from shared.config import settings


def init_database():
    """Initialize database with pgvector extension and tables."""
    print("Initializing database...")

    # Determine database URL: prefer env var, then settings
    db_url = os.getenv("DATABASE_URL") or settings.database_url
    print(f"Using DATABASE_URL: {db_url.split('@')[0]}@...")

    # Create a local engine so init can retry with alternate creds if needed
    engine = create_engine(db_url)

    try:
        # Create pgvector extension
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                print("✓ pgvector extension created/verified")
            except Exception as e:
                print(f"⚠ Warning: Could not create pgvector extension: {e}")
                print("  Please ensure pgvector is installed on your PostgreSQL server")

        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created")

        print("\n✅ Database initialization completed successfully!")
        return True

    except OperationalError as op_err:
        # If authentication failed and we're using a default 'user' account,
        # attempt a fallback to the local postgres superuser (postgres:postgres).
        err_text = str(op_err)
        print(f"\n⚠ OperationalError during DB init: {err_text}")

        if "password authentication failed" in err_text.lower():
            try:
                url = make_url(db_url)
                print("Attempting fallback using postgres:postgres credentials...")
                url = url.set(username="postgres", password="postgres")
                fallback_engine = create_engine(str(url))

                with fallback_engine.connect() as conn:
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                        conn.commit()
                        print("✓ pgvector extension created/verified (fallback)")
                    except Exception as e:
                        print(f"⚠ Warning: Could not create pgvector extension on fallback: {e}")

                Base.metadata.create_all(bind=fallback_engine)
                print("✓ Database tables created (fallback)")
                print("\n✅ Database initialization completed successfully with fallback!")
                return True
            except Exception as e:
                print(f"\n❌ Fallback initialization failed: {e}")
                return False

        print(f"\n❌ Error initializing database: {op_err}")
        return False

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
