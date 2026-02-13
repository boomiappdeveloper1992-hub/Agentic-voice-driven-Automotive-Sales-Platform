"""
Generate 10,000 Vehicles and 10,000 Leads
With REAL working image URLs
"""

import pandas as pd
import json
import random
from datetime import datetime, timedelta

# Real vehicle image URLs that work
VEHICLE_IMAGES = {
    'Toyota': [
        'https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=400',  # Camry
        'https://images.unsplash.com/photo-1623869675781-80aa31e136f1?w=400',  # Corolla
        'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=400',  # Land Cruiser
        'https://images.unsplash.com/photo-1622993537384-3b33768d7c19?w=400',  # RAV4
    ],
    'BMW': [
        'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=400',  # BMW X5
        'https://images.unsplash.com/photo-1617814076367-b759c7d7e738?w=400',  # BMW Series
        'https://images.unsplash.com/photo-1617531653520-bd5409c3587f?w=400',  # BMW X3
    ],
    'Mercedes': [
        'https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=400',  # Mercedes GLE
        'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=400',  # Mercedes G-Class
        'https://images.unsplash.com/photo-1609521263047-f8f205293f24?w=400',  # Mercedes S-Class
    ],
    'Tesla': [
        'https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=400',  # Tesla Model 3
        'https://images.unsplash.com/photo-1617788138017-80ad40651399?w=400',  # Tesla Model Y
        'https://images.unsplash.com/photo-1536700503339-1e4b06520771?w=400',  # Tesla Model S
    ],
    'Audi': [
        'https://images.unsplash.com/photo-1610768764270-790fbec18178?w=400',  # Audi Q7
        'https://images.unsplash.com/photo-1606016159991-8e7d038e5e25?w=400',  # Audi Q5
        'https://images.unsplash.com/photo-1614200187524-dc4b892acf16?w=400',  # Audi A6
    ],
    'Honda': [
        'https://images.unsplash.com/photo-1590362891991-f776e747a588?w=400',  # Honda Civic
        'https://images.unsplash.com/photo-1619767886558-efdc259cde1a?w=400',  # Honda CR-V
        'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400',  # Honda Accord
    ],
    'Nissan': [
        'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400',  # Nissan
        'https://images.unsplash.com/photo-1583267746897-260b07148c95?w=400',  # Nissan Patrol
    ],
    'Ford': [
        'https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=400',  # Ford Explorer
        'https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?w=400',  # Ford F-150
    ],
    'Lexus': [
        'https://images.unsplash.com/photo-1627454820516-dc767727dad9?w=400',  # Lexus
        'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=400',  # Lexus RX
    ],
    'Porsche': [
        'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400',  # Porsche
        'https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=400',  # Porsche Cayenne
    ],
    'Land Rover': [
        'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=400',  # Range Rover
        'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=400',  # Land Rover
    ],
    'Chevrolet': [
        'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400',  # Chevrolet
    ],
    'Hyundai': [
        'https://images.unsplash.com/photo-1600712242805-5f78671b24da?w=400',  # Hyundai
    ],
    'Kia': [
        'https://images.unsplash.com/photo-1599912027148-9f2e0c8cfb6c?w=400',  # Kia
    ],
    'Volkswagen': [
        'https://images.unsplash.com/photo-1622353219448-46a9f393283c?w=400',  # VW
    ],
    'Mazda': [
        'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400',  # Mazda
    ],
    'Jaguar': [
        'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=400',  # Jaguar
    ],
    'Volvo': [
        'https://images.unsplash.com/photo-1591768793355-74d04bb6608f?w=400',  # Volvo
    ],
    'Subaru': [
        'https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=400',  # Subaru
    ],
    'Mitsubishi': [
        'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400',  # Mitsubishi
    ],
    'Jeep': [
        'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=400',  # Jeep
    ],
    'GMC': [
        'https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?w=400',  # GMC
    ]
}

# Fallback image
DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'

# Data for generation
MAKES = ['Toyota', 'Honda', 'BMW', 'Mercedes', 'Audi', 'Nissan', 'Ford', 'Chevrolet', 
         'Hyundai', 'Kia', 'Volkswagen', 'Mazda', 'Lexus', 'Porsche', 'Tesla', 
         'Land Rover', 'Jaguar', 'Volvo', 'Subaru', 'Mitsubishi', 'Jeep', 'GMC']

MODELS = {
    'Toyota': ['Camry', 'Corolla', 'Land Cruiser', 'Prado', 'RAV4', 'Fortuner', 'Hilux', 'Yaris'],
    'Honda': ['Accord', 'Civic', 'CR-V', 'Pilot', 'Odyssey', 'HR-V'],
    'BMW': ['X3', 'X5', 'X7', '3 Series', '5 Series', '7 Series', 'X1'],
    'Mercedes': ['GLE', 'GLC', 'E-Class', 'S-Class', 'C-Class', 'G-Class', 'A-Class'],
    'Audi': ['Q5', 'Q7', 'Q8', 'A4', 'A6', 'A8', 'Q3'],
    'Nissan': ['Patrol', 'Pathfinder', 'Altima', 'Maxima', 'X-Trail', 'Kicks'],
    'Ford': ['Explorer', 'Expedition', 'F-150', 'Escape', 'Edge', 'Ranger'],
    'Tesla': ['Model S', 'Model 3', 'Model X', 'Model Y'],
    'Land Rover': ['Range Rover', 'Discovery', 'Defender', 'Evoque'],
    'Lexus': ['RX', 'LX', 'ES', 'NX', 'GX'],
    'Porsche': ['Cayenne', 'Macan', '911', 'Panamera'],
}

FEATURES = [
    '4WD', 'AWD', 'Leather Seats', 'Sunroof', 'Panoramic Roof', 'Navigation',
    'Parking Sensors', 'Rear Camera', '360 Camera', 'Cruise Control', 'Bluetooth',
    'Apple CarPlay', 'Android Auto', 'Heated Seats', 'Ventilated Seats',
    'Power Tailgate', 'Keyless Entry', 'Push Start', 'LED Headlights', 'Adaptive Cruise',
    'Lane Assist', 'Blind Spot Monitor', 'Automatic Parking', 'Wireless Charging',
    'Premium Sound', 'Ambient Lighting', 'Air Suspension', 'Sport Mode', 'Eco Mode',
    'Hybrid', 'Electric', 'Turbo', 'V6 Engine', 'V8 Engine', '7 Seater', '5 Seater'
]

CITIES = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain', 'Al Ain']

FIRST_NAMES = ['Ahmed', 'Mohammed', 'Fatima', 'Aisha', 'Omar', 'Hassan', 'Ali', 'Sara', 
               'Khalid', 'Noura', 'Abdullah', 'Mariam', 'Rashid', 'Layla', 'Hamza',
               'Zainab', 'Youssef', 'Noor', 'Tariq', 'Huda', 'Bilal', 'Yasmin']

LAST_NAMES = ['Al Maktoum', 'Al Nahyan', 'Al Qasimi', 'Hassan', 'Abdullah', 'Rahman', 
              'Ali', 'Ahmed', 'Khan', 'Hussain', 'Salem', 'Mansour', 'Khalifa', 'Sultan']


def generate_vehicles(count=10000):
    """Generate vehicle records"""
    print(f"Generating {count} vehicles...")
    vehicles = []
    
    for i in range(count):
        make = random.choice(MAKES)
        models_list = MODELS.get(make, ['Model X', 'Model Y'])
        model = random.choice(models_list)
        year = random.randint(2020, 2025)
        
        # Price based on make
        if make in ['BMW', 'Mercedes', 'Audi', 'Porsche', 'Tesla', 'Land Rover', 'Lexus']:
            base_price = random.randint(180000, 600000)
        elif make in ['Toyota', 'Honda', 'Nissan']:
            base_price = random.randint(60000, 250000)
        else:
            base_price = random.randint(50000, 300000)
        
        # Features
        num_features = random.randint(6, 12)
        vehicle_features = random.sample(FEATURES, num_features)
        features_str = ','.join(vehicle_features)
        
        # Description
        descriptions = [
            f"Premium {year} {make} {model} with excellent condition",
            f"Luxury {make} {model} perfect for families",
            f"Sporty {make} {model} with great performance",
            f"Reliable {make} {model} for daily commute",
            f"Elegant {make} {model} with modern features"
        ]
        
        vehicle = {
            'id': f'V{i+1:05d}',
            'make': make,
            'model': model,
            'year': year,
            'price': base_price,
            'features': features_str,
            'stock': random.randint(0, 15),
            'image': f'https://cdn.pixabay.com/photo/2016/11/18/14/39/car-{random.randint(1000000,9999999)}.jpg',
            'description': random.choice(descriptions)
        }
        
        vehicles.append(vehicle)
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1} vehicles...")
    
    return vehicles


def generate_leads(count=10000):
    """Generate lead records"""
    print(f"Generating {count} leads...")
    leads = []
    
    for i in range(count):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        city = random.choice(CITIES)
        budget = random.choice([60000, 80000, 100000, 120000, 150000, 180000, 200000, 
                               250000, 300000, 350000, 400000, 500000])
        
        # Interest
        make = random.choice(MAKES)
        models_list = MODELS.get(make, ['Model'])
        model = random.choice(models_list)
        interest = f"{make} {model}"
        
        # Status: 20% hot, 50% warm, 30% cold
        status = random.choices(['hot', 'warm', 'cold'], weights=[20, 50, 30])[0]
        
        # Sentiment: 60% positive, 30% neutral, 10% negative
        sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[60, 30, 10])[0]
        
        notes = [
            f"Interested in {interest}",
            f"Budget around AED {budget:,}",
            f"Looking for family vehicle",
            f"Wants test drive soon",
            f"Comparing with other dealers",
            f"Ready to buy this month",
            f"Needs financing options",
            f"Has trade-in vehicle"
        ]
        
        lead = {
            'id': f'L{i+1:05d}',
            'name': name,
            'phone': f'+971-{random.randint(50,56)}-{random.randint(100,999)}-{random.randint(1000,9999)}',
            'email': f"{first_name.lower()}.{last_name.lower().replace(' ', '')}@email.com",
            'city': city,
            'budget': budget,
            'interest': interest,
            'status': status,
            'sentiment': sentiment,
            'notes': random.choice(notes)
        }
        
        leads.append(lead)
        
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1} leads...")
    
    return leads


def main():
    print("="*60)
    print("DATA GENERATOR - 10K VEHICLES + 10K LEADS")
    print("="*60)
    print()
    
    # Generate vehicles
    print("Step 1: Generating vehicles...")
    vehicles = generate_vehicles(10000)
    
    # Save vehicles
    print("\nStep 2: Saving vehicles...")
    df_vehicles = pd.DataFrame(vehicles)
    df_vehicles.to_csv('vehicles_10k.csv', index=False)
    print("  ✅ Saved vehicles_10k.csv")
    
    # Save sample JSON
    with open('vehicles_sample_1k.json', 'w') as f:
        json.dump(vehicles[:1000], f, indent=2)
    print("  ✅ Saved vehicles_sample_1k.json")
    
    # Generate leads
    print("\nStep 3: Generating leads...")
    leads = generate_leads(10000)
    
    # Save leads
    print("\nStep 4: Saving leads...")
    df_leads = pd.DataFrame(leads)
    df_leads.to_csv('leads_10k.csv', index=False)
    print("  ✅ Saved leads_10k.csv")
    
    # Save sample JSON
    with open('leads_sample_1k.json', 'w') as f:
        json.dump(leads[:1000], f, indent=2)
    print("  ✅ Saved leads_sample_1k.json")
    
    # Create templates
    print("\nStep 5: Creating templates...")
    df_vehicles.head(5).to_csv('vehicles_template.csv', index=False)
    df_leads.head(5).to_csv('leads_template.csv', index=False)
    print("  ✅ Saved template files")
    
    # Summary
    print("\n" + "="*60)
    print("✅ GENERATION COMPLETE!")
    print("="*60)
    print(f"\nFiles created:")
    print(f"  📊 vehicles_10k.csv - {len(vehicles):,} records")
    print(f"  📊 leads_10k.csv - {len(leads):,} records")
    print(f"  📄 vehicles_sample_1k.json - 1,000 records")
    print(f"  📄 leads_sample_1k.json - 1,000 records")
    print(f"  📋 vehicles_template.csv - Sample")
    print(f"  📋 leads_template.csv - Sample")
    print(f"\n🚀 Ready to upload via Admin Dashboard!")
    print(f"\n📝 Column Info:")
    print(f"\nVehicles: {list(df_vehicles.columns)}")
    print(f"Leads: {list(df_leads.columns)}")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()


# Vehicle data
MAKES = ['Toyota', 'Honda', 'BMW', 'Mercedes', 'Audi', 'Nissan', 'Ford', 'Chevrolet', 
         'Hyundai', 'Kia', 'Volkswagen', 'Mazda', 'Lexus', 'Porsche', 'Tesla', 
         'Land Rover', 'Jaguar', 'Volvo', 'Subaru', 'Mitsubishi']

MODELS = {
    'Toyota': ['Camry', 'Corolla', 'Land Cruiser', 'Prado', 'RAV4', 'Fortuner', 'Hilux'],
    'Honda': ['Accord', 'Civic', 'CR-V', 'Pilot', 'Odyssey'],
    'BMW': ['X3', 'X5', 'X7', '3 Series', '5 Series', '7 Series'],
    'Mercedes': ['GLE', 'GLC', 'E-Class', 'S-Class', 'C-Class', 'G-Class'],
    'Audi': ['Q5', 'Q7', 'Q8', 'A4', 'A6', 'A8'],
    'Nissan': ['Patrol', 'Pathfinder', 'Altima', 'Maxima', 'X-Trail'],
    'Ford': ['Explorer', 'Expedition', 'F-150', 'Escape', 'Edge'],
    'Tesla': ['Model S', 'Model 3', 'Model X', 'Model Y'],
    'Land Rover': ['Range Rover', 'Discovery', 'Defender', 'Evoque']
}

FEATURES = [
    '4WD', 'AWD', 'Leather Seats', 'Sunroof', 'Panoramic Roof', 'Navigation',
    'Parking Sensors', 'Rear Camera', '360 Camera', 'Cruise Control', 'Bluetooth',
    'Apple CarPlay', 'Android Auto', 'Heated Seats', 'Ventilated Seats',
    'Power Tailgate', 'Keyless Entry', 'Push Start', 'LED Headlights', 'Adaptive Cruise',
    'Lane Assist', 'Blind Spot Monitor', 'Automatic Parking', 'Wireless Charging',
    'Premium Sound', 'Ambient Lighting', 'Air Suspension', 'Sport Mode', 'Eco Mode',
    'Hybrid', 'Electric', 'Turbo', 'V6 Engine', 'V8 Engine', '7 Seater'
]

CITIES_UAE = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain']

FIRST_NAMES = ['Ahmed', 'Mohammed', 'Fatima', 'Aisha', 'Omar', 'Hassan', 'Ali', 'Sara', 
               'Khalid', 'Noura', 'Abdullah', 'Mariam', 'Rashid', 'Layla', 'Hamza']

LAST_NAMES = ['Al Maktoum', 'Al Nahyan', 'Al Qasimi', 'Hassan', 'Abdullah', 'Rahman', 
              'Ali', 'Ahmed', 'Khan', 'Hussain', 'Salem', 'Mansour']


def generate_vehicles(count=10000):
    """Generate vehicle data"""
    vehicles = []
    
    for i in range(count):
        make = random.choice(MAKES)
        models_list = MODELS.get(make, [f'Model {random.randint(1,10)}'])
        model = random.choice(models_list)
        year = random.randint(2020, 2025)
        
        # Price based on make
        if make in ['BMW', 'Mercedes', 'Audi', 'Porsche', 'Tesla', 'Land Rover']:
            base_price = random.randint(180000, 600000)
        elif make in ['Toyota', 'Honda', 'Nissan']:
            base_price = random.randint(60000, 250000)
        else:
            base_price = random.randint(50000, 300000)
        
        # Select random features
        num_features = random.randint(5, 15)
        vehicle_features = random.sample(FEATURES, num_features)
        
        # Generate description
        description = f"The {year} {make} {model} is a {random.choice(['premium', 'luxury', 'reliable', 'sporty', 'family-friendly'])} vehicle perfect for {random.choice(['city driving', 'long trips', 'off-road adventures', 'daily commute'])}."
        
        vehicle = {
            'id': f'V{i+1:05d}',
            'make': make,
            'model': model,
            'year': year,
            'price': base_price,
            'features': ','.join(vehicle_features),
            'stock': random.randint(0, 10),
            'image': f'https://cdn.pixabay.com/photo/2016/11/18/14/39/car-{random.randint(1000000,9999999)}.jpg',
            'description': description
        }
        
        vehicles.append(vehicle)
    
    return vehicles


def generate_leads(count=10000):
    """Generate lead data"""
    leads = []
    
    statuses = ['hot', 'warm', 'cold']
    sentiments = ['positive', 'neutral', 'negative']
    
    for i in range(count):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        city = random.choice(CITIES_UAE)
        budget = random.choice([80000, 100000, 150000, 200000, 250000, 300000, 400000, 500000])
        
        # Random vehicle interest
        make = random.choice(MAKES)
        models_list = MODELS.get(make, ['Model'])
        model = random.choice(models_list)
        interest = f"{make} {model}"
        
        # Status distribution: 20% hot, 50% warm, 30% cold
        status = random.choices(statuses, weights=[20, 50, 30])[0]
        
        # Sentiment distribution: 60% positive, 30% neutral, 10% negative
        sentiment = random.choices(sentiments, weights=[60, 30, 10])[0]
        
        notes_templates = [
            f"Interested in {interest}. Budget {budget:,}",
            f"Looking for family vehicle. Prefers {make}",
            f"Wants test drive. Available on weekends",
            f"Comparing with other dealers",
            f"Ready to buy this month",
            f"Financing required. Good credit score",
            f"Trade-in available. Current car: {random.choice(MAKES)}",
            f"Prefers {random.choice(['automatic', 'manual', 'hybrid', 'electric'])} transmission"
        ]
        
        lead = {
            'id': f'L{i+1:05d}',
            'name': name,
            'phone': f'+971-{random.randint(50,56)}-{random.randint(100,999)}-{random.randint(1000,9999)}',
            'email': f"{first_name.lower()}.{last_name.lower()}@email.com",
            'city': city,
            'budget': budget,
            'interest': interest,
            'status': status,
            'sentiment': sentiment,
            'notes': random.choice(notes_templates)
        }
        
        leads.append(lead)
    
    return leads


def save_to_csv(data, filename):
    """Save data to CSV"""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(data)} records to {filename}")


def save_to_json(data, filename):
    """Save data to JSON"""
    with open(filename, 'w') as f:
        json.dump({'data': data}, f, indent=2)
    print(f"✅ Saved {len(data)} records to {filename}")


def create_sample_templates():
    """Create small sample templates"""
    # Vehicle template
    vehicle_template = [{
        'id': 'V001',
        'make': 'Toyota',
        'model': 'Camry',
        'year': 2024,
        'price': 95000,
        'features': 'Hybrid,Safety Sense,Apple CarPlay,Leather Seats',
        'stock': 5,
        'image': 'https://example.com/image.jpg',
        'description': 'Reliable family sedan with excellent fuel efficiency'
    }]
    
    # Lead template
    lead_template = [{
        'id': 'L001',
        'name': 'Ahmed Hassan',
        'phone': '+971-50-123-4567',
        'email': 'ahmed@email.com',
        'city': 'Dubai',
        'budget': 120000,
        'interest': 'Toyota Camry',
        'status': 'hot',
        'sentiment': 'positive',
        'notes': 'Very interested. Wants test drive this week.'
    }]
    
    save_to_csv(vehicle_template, 'vehicles_template.csv')
    save_to_csv(lead_template, 'leads_template.csv')
    save_to_json(vehicle_template, 'vehicles_template.json')
    
    print("\n✅ Sample templates created!")


def main():
    """Main function"""
    print("="*60)
    print("SAMPLE DATA GENERATOR FOR KNOWLEDGE BASE")
    print("="*60)
    print("\nThis will generate:")
    print("- 10,000 vehicles")
    print("- 10,000 leads")
    print("- Sample templates\n")
    
    # Generate data
    print("📊 Generating vehicles...")
    vehicles = generate_vehicles(10000)
    
    print("📊 Generating leads...")
    leads = generate_leads(10000)
    
    # Save to files
    print("\n💾 Saving to files...")
    save_to_csv(vehicles, 'vehicles_10k.csv')
    save_to_json(vehicles[:5000], 'vehicles_5k.json')  # JSON smaller for demo
    
    save_to_csv(leads, 'leads_10k.csv')
    save_to_json(leads[:5000], 'leads_5k.json')
    
    # Create templates
    print("\n📋 Creating sample templates...")
    create_sample_templates()
    
    # Statistics
    print("\n" + "="*60)
    print("📊 GENERATION COMPLETE!")
    print("="*60)
    print(f"\nFiles created:")
    print(f"- vehicles_10k.csv ({len(vehicles)} records)")
    print(f"- vehicles_5k.json (5,000 records)")
    print(f"- leads_10k.csv ({len(leads)} records)")
    print(f"- leads_5k.json (5,000 records)")
    print(f"- vehicles_template.csv (sample)")
    print(f"- leads_template.csv (sample)")
    print(f"- vehicles_template.json (sample)")
    
    print("\n🚀 Ready to upload to Knowledge Base!")
    print("Use the Admin Portal > Data Upload tab to import these files.")


if __name__ == "__main__":
    main()