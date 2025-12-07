"""Database initialization script."""
import sys
from shared.database import engine, Base
from sqlalchemy import text


def init_database():
    """Initialize database with pgvector extension and tables."""
    print("Initializing database...")
    
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
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
