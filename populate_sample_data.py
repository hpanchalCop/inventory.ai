"""Script to populate database with sample products."""
import requests
import sys


API_URL = "http://localhost:8000"


SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with USB receiver, 2.4GHz connection, 3 buttons",
        "category": "Electronics",
        "price": 29.99
    },
    {
        "name": "Mechanical Keyboard",
        "description": "RGB mechanical keyboard with blue switches, full-size layout, aluminum frame",
        "category": "Electronics",
        "price": 89.99
    },
    {
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI, USB 3.0, SD card reader, and power delivery",
        "category": "Electronics",
        "price": 39.99
    },
    {
        "name": "Laptop Stand",
        "description": "Aluminum laptop stand with adjustable height, ergonomic design, supports up to 17 inch laptops",
        "category": "Accessories",
        "price": 49.99
    },
    {
        "name": "Webcam HD",
        "description": "1080p HD webcam with built-in microphone, auto-focus, wide-angle lens",
        "category": "Electronics",
        "price": 59.99
    },
    {
        "name": "Desk Lamp",
        "description": "LED desk lamp with adjustable brightness, USB charging port, touch control",
        "category": "Office",
        "price": 34.99
    },
    {
        "name": "Monitor 24 inch",
        "description": "24 inch Full HD monitor, IPS panel, 75Hz refresh rate, HDMI and DisplayPort",
        "category": "Electronics",
        "price": 179.99
    },
    {
        "name": "Noise Cancelling Headphones",
        "description": "Over-ear noise cancelling headphones, 30-hour battery life, Bluetooth 5.0",
        "category": "Electronics",
        "price": 149.99
    },
    {
        "name": "Portable SSD 1TB",
        "description": "1TB portable SSD with USB-C connection, read speeds up to 1000MB/s",
        "category": "Storage",
        "price": 119.99
    },
    {
        "name": "Phone Stand",
        "description": "Adjustable phone stand for desk, aluminum construction, fits all smartphones",
        "category": "Accessories",
        "price": 19.99
    }
]


def create_sample_products():
    """Create sample products via API."""
    print(f"🌱 Populating database with sample products...")
    print(f"📡 API URL: {API_URL}")
    
    created_count = 0
    
    for product in SAMPLE_PRODUCTS:
        try:
            response = requests.post(
                f"{API_URL}/products/text-only",
                json=product,
                timeout=10
            )
            
            if response.status_code == 200:
                created_count += 1
                print(f"✓ Created: {product['name']}")
            else:
                print(f"✗ Failed to create {product['name']}: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating {product['name']}: {e}")
    
    print(f"\n✅ Successfully created {created_count}/{len(SAMPLE_PRODUCTS)} products")
    return created_count == len(SAMPLE_PRODUCTS)


if __name__ == "__main__":
    try:
        success = create_sample_products()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
