import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
import numpy as np
import os

# Create directories
os.makedirs('data/warehouse', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)
os.makedirs('data/raw', exist_ok=True)

# Realistic product data
products_data = {
    'Sony WH-1000XM5': {
        'base_price': 348,
        'price_range': (320, 380),
        'rating': 4.7
    },
    'Bose QuietComfort 45': {
        'base_price': 279,
        'price_range': (250, 310),
        'rating': 4.6
    },
    'Apple AirPods Max': {
        'base_price': 549,
        'price_range': (499, 599),
        'rating': 4.5
    },
    'Sennheiser Momentum 4': {
        'base_price': 299,
        'price_range': (270, 330),
        'rating': 4.4
    },
    'Jabra Elite 85h': {
        'base_price': 249,
        'price_range': (220, 280),
        'rating': 4.3
    }
}

sources = ['Amazon', 'Best Buy', 'Walmart', 'Target']

# Generate 60 days of data
dates = [datetime.now() - timedelta(days=i) for i in range(60, -1, -1)]

data = []
for product_name, product_info in products_data.items():
    base_price = product_info['base_price']
    price_range = product_info['price_range']
    rating = product_info['rating']
    
    for source in sources:
        # Source-specific pricing strategy
        source_markup = {
            'Amazon': random.uniform(-15, 10),
            'Best Buy': random.uniform(-5, 20),
            'Walmart': random.uniform(-20, 5),
            'Target': random.uniform(-10, 15)
        }[source]
        
        # Generate price history with realistic patterns
        for i, date in enumerate(dates):
            # Weekly pattern (prices drop on weekends)
            weekday = date.weekday()
            weekend_factor = 0.95 if weekday >= 5 else 1.0
            
            # Random fluctuations
            noise = np.random.normal(0, 3)
            
            # Trend (prices slowly decrease over time)
            trend = -0.02 * (60 - i) / 60 * 10
            
            # Calculate price
            price = base_price + source_markup + noise + trend
            price = price * weekend_factor
            
            # Ensure price stays within range
            price = max(price_range[0], min(price_range[1], price))
            price = round(price, 2)
            
            # Stock status (random with some patterns)
            stock_status = 'In Stock'
            if random.random() < 0.12:  # 12% chance of being out of stock
                stock_status = 'Out of Stock'
            elif random.random() < 0.05:  # 5% chance of limited stock
                stock_status = 'Limited Stock'
            
            # Availability text
            availability = {
                'In Stock': 'In Stock - Ships within 2 days',
                'Out of Stock': 'Currently Unavailable',
                'Limited Stock': 'Only 3 left in stock'
            }[stock_status]
            
            data.append({
                'product': product_name,
                'source': source,
                'price': price,
                'stock_status': stock_status,
                'availability': availability,
                'rating': round(rating + np.random.normal(0, 0.2), 1),
                'scraped_at': date.isoformat(),
                'title': f'{product_name} Wireless Headphones',
                'product_id': f'{product_name[:3]}_{source[:3]}_{date.strftime("%Y%m%d")}',
                'currency': 'USD'
            })

# Create DataFrame
df = pd.DataFrame(data)

# Save to SQLite
db_path = "data/warehouse/prices.db"
conn = sqlite3.connect(db_path)
df.to_sql('price_history', conn, if_exists='replace', index=False)
conn.close()

# Also save as CSV for easy viewing
csv_path = f"data/processed/prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
df.to_csv(csv_path, index=False)

print(f"✅ Created {len(df)} records in {db_path}")
print(f"✅ Saved CSV: {csv_path}")
print("\n📊 Sample Data:")
print(df[['product', 'source', 'price', 'stock_status']].head(10))
print("\n📈 Statistics:")
print(f"  - Products: {df['product'].nunique()}")
print(f"  - Sources: {df['source'].nunique()}")
print(f"  - Date Range: {df['scraped_at'].min()} to {df['scraped_at'].max()}")
print(f"  - Price Range:  - ")
print("\n🎯 Now run: streamlit run dashboard/app.py")
