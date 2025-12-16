"""Script to populate database with sample products."""
import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use AWS ALB URL if provided, otherwise default to localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")


SAMPLE_PRODUCTS = [
    # Healthcare Equipment - Adjustable Height Beds
    {
        "name": "Panacea 1500 Low Bed - Full Electric",
        "description": "Full electric low bed with adjustable height 7-27 inches, built-in scale, and quiet motors. Includes head and foot articulation with trendelenburg positioning.",
        "category": "Healthcare Equipment",
        "price": 3299.99
    },
    {
        "name": "Panacea 3000 Bariatric Bed",
        "description": "Heavy-duty bariatric bed supporting up to 1000 lbs, with reinforced frame and extra-wide 48-inch sleeping surface. Full electric controls.",
        "category": "Healthcare Equipment",
        "price": 4899.99
    },
    {
        "name": "Tranquility 8000 Long Term Care Bed",
        "description": "Durable long-term care bed with split safety rails, emergency CPR release, and nurse control lockout. Wood grain finish options available.",
        "category": "Healthcare Equipment",
        "price": 2799.99
    },
    {
        "name": "42-W Laminate End Panels for Panacea Beds",
        "description": "Wild cherry laminate end panels compatible with Panacea 1500, 3000, 3250, 3500, and 8000 series beds. Hardware included.",
        "category": "Healthcare Equipment",
        "price": 449.99
    },
    {
        "name": "Premium Therapeutic Mattress - 80 inch",
        "description": "Pressure redistribution therapeutic mattress with multi-zone foam construction. Fire retardant, fluid-resistant cover with zipper.",
        "category": "Healthcare Equipment",
        "price": 899.99
    },
    
    # Healthcare Equipment - Wheelchairs
    {
        "name": "Comfort-Ride Transport Chair",
        "description": "Lightweight aluminum transport wheelchair with 19-inch seat width, swing-away footrests, and companion brakes. Weight capacity 300 lbs.",
        "category": "Healthcare Equipment",
        "price": 329.99
    },
    {
        "name": "Freedom Recliner Wheelchair",
        "description": "Full reclining wheelchair with elevating legrests, adjustable armrests, and gel seat cushion. Ideal for extended use and pressure relief.",
        "category": "Healthcare Equipment ",
        "price": 1299.99
    },
    {
        "name": "Bariatric Wheelchair - 24 inch Wide",
        "description": "Heavy-duty bariatric wheelchair supporting up to 500 lbs. Reinforced frame, dual axle positioning, and puncture-proof tires.",
        "category": "Healthcare Equipment",
        "price": 799.99
    },
    {
        "name": "Tilt-in-Space Wheelchair with Headrest",
        "description": "Therapeutic tilt wheelchair with 45-degree tilt range, adjustable headrest, and positioning belt system for maximum comfort and stability.",
        "category": "Healthcare Equipment",
        "price": 2199.99
    },
    {
        "name": "Pediatric Wheelchair - Adjustable Growth",
        "description": "Pediatric wheelchair with adjustable seat depth and width to accommodate growing children. Colorful frame options and flip-back arms.",
        "category": "Healthcare Equipment",
        "price": 649.99
    },
    
    # Healthcare Equipment - Patient Lifts & Transfer
    {
        "name": "Hoyer Professional Series Patient Lift",
        "description": "Electric patient lift with 450 lb capacity, emergency lowering system, and six-point cradle. Battery powered for portability.",
        "category": "Healthcare Equipment",
        "price": 1899.99
    },
    {
        "name": "Stand Assist Lift - Compact Design",
        "description": "Stand assist lift for patients with partial weight-bearing ability. Compact base fits under most beds, 400 lb capacity.",
        "category": "Healthcare Equipment",
        "price": 1299.99
    },
    {
        "name": "Transfer Board - Curved with Handles",
        "description": "Smooth curved transfer board with built-in handles for safe patient transfers. Non-slip surface, supports up to 400 lbs.",
        "category": "Healthcare Equipment",
        "price": 89.99
    },
    {
        "name": "Ceiling Track Patient Lift System",
        "description": "Overhead ceiling-mounted lift system with 600 lb capacity. Includes 20-foot track, motor, and sling. Professional installation required.",
        "category": "Healthcare Equipment",
        "price": 5499.99
    },
    
    # Healthcare Clinical - Vital Signs & Monitoring
    {
        "name": "Professional Automatic Blood Pressure Monitor",
        "description": "Clinical-grade automatic BP monitor with large LCD display, irregular heartbeat detection, and memory for 120 readings.",
        "category": "Healthcare Clinical",
        "price": 249.99
    },
    {
        "name": "Digital Thermometer - 3-Second Reading",
        "description": "Fast-reading digital thermometer with flexible tip and fever alarm. Waterproof design with storage case included.",
        "category": "Healthcare Clinical",
        "price": 29.99
    },
    {
        "name": "Pulse Oximeter - Fingertip Model",
        "description": "Portable fingertip pulse oximeter measuring SpO2 and pulse rate. OLED display with multiple viewing angles, includes lanyard.",
        "category": "Healthcare Clinical",
        "price": 79.99
    },
    {
        "name": "Mobile Vital Signs Cart with Monitor",
        "description": "Rolling vital signs cart with integrated monitor, supply storage, and locking casters. Includes BP cuff, thermometer holder.",
        "category": "Healthcare Clinical",
        "price": 1499.99
    },
    
    # Healthcare Clinical - Examination Equipment
    {
        "name": "Stainless Steel Examination Table",
        "description": "Durable exam table with adjustable backrest, pull-out step, and paper roll holder. Weight capacity 500 lbs, easy-clean surface.",
        "category": "Healthcare Clinical",
        "price": 1799.99
    },
    {
        "name": "LED Examination Light - Floor Model",
        "description": "Mobile LED exam light with adjustable arm and intensity control. 50,000-hour LED life, shadow-free illumination.",
        "category": "Healthcare Clinical",
        "price": 899.99
    },
    {
        "name": "Physician Stethoscope - Cardiology Grade",
        "description": "Professional cardiology stethoscope with dual-sided chest piece and tunable diaphragm. Includes spare parts kit.",
        "category": "Healthcare Clinical",
        "price": 199.99
    },
    {
        "name": "Reflex Hammer - Neurological Set",
        "description": "Complete neurological reflex testing set with Taylor hammer, tuning forks (128Hz, 256Hz), and monofilament. Storage case included.",
        "category": "Healthcare Clinical",
        "price": 49.99
    },
    
    # Furnishings - Patient Room Furniture
    {
        "name": "Overbed Table - Tilt Top with Storage",
        "description": "Height-adjustable overbed table with tilting top surface and lower storage shelf. H-base design fits over most beds.",
        "category": "Furnishings",
        "price": 299.99
    },
    {
        "name": "Bedside Cabinet with Locking Drawer",
        "description": "Laminate bedside cabinet with locking drawer, open shelf, and towel bar. Matches Panacea bed panels in wild cherry finish.",
        "category": "Furnishings",
        "price": 449.99
    },
    {
        "name": "Privacy Curtain with Track - Antimicrobial",
        "description": "Flame-retardant privacy curtain with antimicrobial treatment. Includes ceiling track hardware for 10-foot span.",
        "category": "Furnishings",
        "price": 189.99
    },
    {
        "name": "Patient Room Recliner - High Back",
        "description": "Comfortable recliner with moisture-barrier upholstery, trendelenburg positioning, and easy-clean armrests. 400 lb capacity.",
        "category": "Furnishings",
        "price": 1199.99
    },
    {
        "name": "Wall-Mounted TV Bracket - Healthcare Grade",
        "description": "Antimicrobial powder-coated TV mount supporting 32-55 inch displays. Tool-free tilt and swivel, weight capacity 75 lbs.",
        "category": "Furnishings",
        "price": 149.99
    },
    
    # Furnishings - Nurse Station & Office
    {
        "name": "Mobile Nurse Station Desk",
        "description": "Rolling nurse station with locking casters, work surface, file drawer, and supply compartments. Laminate construction.",
        "category": "Furnishings",
        "price": 899.99
    },
    {
        "name": "Ergonomic Task Chair - 24/7 Rated",
        "description": "Heavy-duty task chair rated for 24/7 use. Multi-function controls, lumbar support, and antimicrobial vinyl upholstery.",
        "category": "Furnishings",
        "price": 399.99
    },
    {
        "name": "Medical Chart Binder Rack - Wall Mount",
        "description": "Wall-mounted aluminum chart rack holding 15 binders. Open design for easy chart access and HIPAA-compliant viewing.",
        "category": "Furnishings",
        "price": 179.99
    },
    {
        "name": "Mobile Supply Cart - 3 Shelves",
        "description": "Stainless steel supply cart with three shelves and push handle. Locking casters and bumper guards. 200 lb capacity per shelf.",
        "category": "Furnishings",
        "price": 449.99
    },
    
    # Furnishings - Common Areas
    {
        "name": "Waiting Room Loveseat - Bariatric",
        "description": "Heavy-duty loveseat supporting up to 750 lbs total. Reinforced frame, antimicrobial upholstery, and center armrest.",
        "category": "Furnishings",
        "price": 799.99
    },
    {
        "name": "Side Table - End Table with Magazine Rack",
        "description": "Laminate end table with built-in magazine rack and lower shelf. Rounded corners for safety, wild cherry finish.",
        "category": "Furnishings",
        "price": 199.99
    },
    {
        "name": "Wall-Mounted Coat Rack - 6 Hook",
        "description": "Antimicrobial powder-coated steel coat rack with six hooks. Mounts to wall studs, includes mounting hardware.",
        "category": "Furnishings",
        "price": 79.99
    },
    {
        "name": "Folding Room Divider - 3 Panel",
        "description": "Three-panel folding room divider with vinyl panels and aluminum frame. Creates flexible space division, 6 feet tall.",
        "category": "Furnishings",
        "price": 299.99
    },
    
    # Healthcare Equipment - Mobility Aids
    {
        "name": "Aluminum Walker with Wheels - Folding",
        "description": "Lightweight aluminum rolling walker with 6-inch wheels, hand brakes, and padded seat. Folds for transport and storage.",
        "category": "Healthcare Equipment",
        "price": 129.99
    },
    {
        "name": "Quad Cane - Heavy Duty Base",
        "description": "Quad cane with large base for maximum stability. Adjustable height 29-38 inches, supports up to 300 lbs.",
        "category": "Healthcare Equipment",
        "price": 39.99
    },
    {
        "name": "Forearm Crutches - Ergonomic Pair",
        "description": "Ergonomic forearm crutches with adjustable cuff height and cushioned grips. Lightweight aluminum, 250 lb capacity.",
        "category": "Healthcare Equipment",
        "price": 89.99
    },
    {
        "name": "Bariatric Rollator with Seat",
        "description": "Extra-wide bariatric rollator with 24-inch seat width, weight capacity 500 lbs. Loop brakes and under-seat basket.",
        "category": "Healthcare Equipment",
        "price": 329.99
    },
    
    # Healthcare Equipment - Bathroom Safety
    {
        "name": "Raised Toilet Seat with Arms",
        "description": "Elevated toilet seat adding 5 inches of height with padded armrests. Tool-free installation, fits standard toilets.",
        "category": "Healthcare Equipment",
        "price": 79.99
    },
    {
        "name": "Grab Bar - 24 inch Stainless Steel",
        "description": "ADA-compliant stainless steel grab bar with concealed mounting brackets. 500 lb weight capacity, professional installation recommended.",
        "category": "Healthcare Equipment",
        "price": 59.99
    },
    {
        "name": "Shower Chair with Back - Adjustable",
        "description": "Height-adjustable shower chair with backrest and non-slip rubber tips. Tool-free assembly, weight capacity 300 lbs.",
        "category": "Healthcare Equipment",
        "price": 89.99
    },
    {
        "name": "Transfer Bench - Tub Slider",
        "description": "Bath transfer bench extending into tub for safe entry. Adjustable legs, textured seat, and cut-out for cleaning.",
        "category": "Healthcare Equipment",
        "price": 119.99
    },
    
    # Healthcare Clinical - Infection Control
    {
        "name": "Sharps Container - 5 Quart Biohazard",
        "description": "Red biohazard sharps container with locking lid and clear fill indicator. Meets FDA and OSHA standards.",
        "category": "Healthcare Clinical",
        "price": 12.99
    },
    {
        "name": "Nitrile Exam Gloves - Box of 100",
        "description": "Powder-free nitrile examination gloves, latex-free. Textured fingertips for grip, ambidextrous design. Size large.",
        "category": "Healthcare Clinical",
        "price": 19.99
    },
    {
        "name": "Hand Sanitizer Dispenser - Touchless",
        "description": "Automatic touchless hand sanitizer dispenser with 1200ml capacity. Battery operated, adjustable dose volume.",
        "category": "Healthcare Clinical",
        "price": 89.99
    },
    {
        "name": "Medical Waste Receptacle - 32 Gallon",
        "description": "Red medical waste receptacle with foot pedal and biohazard symbol. Removable liner, leak-proof design.",
        "category": "Healthcare Clinical",
        "price": 149.99
    },
    
    # Healthcare Equipment - Compression Therapy
    {
        "name": "Compression Pump System - Sequential",
        "description": "Sequential compression therapy system with programmable pressure settings. Includes sleeves for leg or arm treatment.",
        "category": "Healthcare Equipment",
        "price": 1499.99
    },
    {
        "name": "Compression Stockings - Knee High 20-30mmHg",
        "description": "Medical-grade compression stockings for edema and venous insufficiency. Moisture-wicking fabric, reinforced heel and toe.",
        "category": "Healthcare Equipment",
        "price": 49.99
    }
]


def get_auth0_token():
    """Get Auth0 access token using client credentials."""
    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_API_AUDIENCE]):
        print("⚠️  Auth0 credentials not configured in .env")
        print("    Please add: AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_API_AUDIENCE")
        return None
    
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": AUTH0_API_AUDIENCE,
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(token_url, json=payload, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✓ Auth0 token obtained")
            return token
        else:
            print(f"✗ Failed to get Auth0 token: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error getting Auth0 token: {e}")
        return None


def create_sample_products():
    """Create sample products via API."""
    print(f"🌱 Populating database with sample products...")
    print(f"📡 API URL: {API_URL}")
    
    # Get Auth0 token
    token = get_auth0_token()
    if not token:
        print("\n⚠️  Continuing without authentication (will fail if auth is required)")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    created_count = 0
    
    for product in SAMPLE_PRODUCTS:
        try:
            response = requests.post(
                f"{API_URL}/products/text-only",
                json=product,
                headers=headers,
                timeout=60  # Longer timeout for embedding generation
            )
            
            if response.status_code == 200:
                created_count += 1
                print(f"✓ Created: {product['name']}")
            else:
                print(f"✗ Failed to create {product['name']}: {response.status_code}")
                if response.status_code == 401:
                    print("   Authentication required - check Auth0 credentials in .env")
                
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
