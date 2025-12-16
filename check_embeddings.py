"""Check if embeddings are being stored in RDS database."""
import os
from sqlalchemy import create_engine, text

# RDS connection details
DATABASE_URL = "postgresql://postgres:InventoryDB2143!Pass@inventory-ai-db.cwjko2wgq241.us-east-1.rds.amazonaws.com:5432/inventory_db"

def check_embeddings():
    """Query RDS to check embedding status."""
    print("Connecting to RDS...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if products exist and if they have embeddings
            result = conn.execute(text("""
                SELECT 
                    id, 
                    name,
                    text_embedding IS NULL as text_null, 
                    multimodal_embedding IS NULL as multimodal_null,
                    category,
                    created_at
                FROM products 
                ORDER BY created_at DESC
                LIMIT 10;
            """))
            
            products = result.fetchall()
            
            if not products:
                print("\n❌ No products found in database!")
                return
            
            print(f"\n✅ Found {len(products)} products (showing last 10):\n")
            print(f"{'ID':<5} {'Name':<40} {'Text Null':<12} {'Multimodal Null':<16} {'Created'}")
            print("=" * 110)
            
            text_null_count = 0
            multimodal_null_count = 0
            
            for p in products:
                id_val, name, text_null, multimodal_null, category, created = p
                print(f"{id_val:<5} {name[:38]:<40} {str(text_null):<12} {str(multimodal_null):<16} {created}")
                
                if text_null:
                    text_null_count += 1
                if multimodal_null:
                    multimodal_null_count += 1
            
            print("\n" + "=" * 110)
            print(f"\n📊 Summary:")
            print(f"   Text embeddings NULL: {text_null_count}/{len(products)}")
            print(f"   Multimodal embeddings NULL: {multimodal_null_count}/{len(products)}")
            
            if text_null_count == len(products):
                print("\n❌ ISSUE CONFIRMED: All text embeddings are NULL!")
                print("   This is why search returns 0 results.")
                print("   The ML models are not generating embeddings in the ECS container.\n")
            else:
                print("\n✅ Some embeddings are present - search should work!\n")
            
            # Get total count
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            total = result.fetchone()[0]
            print(f"   Total products in database: {total}")
            
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        print("\nMake sure:")
        print("1. Your IP is in the RDS security group")
        print("2. RDS is publicly accessible (if connecting from outside AWS)")
        print("3. Database credentials are correct")

if __name__ == "__main__":
    check_embeddings()
