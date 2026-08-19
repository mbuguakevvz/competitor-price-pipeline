import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
import numpy as np
import yaml

def generate_large_dataset():
    """Generate large dataset with 20+ products and 6 retailers"""
    
    # Load product config
    with open('config/products_extended.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    products_data = config['products']
    retailers = ['Amazon', 'Best Buy', 'Walmart', 'Target', 'eBay', 'Newegg']
    
    # Generate 90 days of data (more history for ML)
    dates = [datetime.now() - timedelta(days=i) for i in range(90, -1, -1)]
    
    data = []
    print(f"📊 Generating data for {len(products_data)} products and {len(retailers)} retailers")
    
    for product in products_data:
        product_name = product['name']
        brand = product['brand']
        category = product['category']
        price_range = product.get('price_range', [100, 500])
        base_price = sum(price_range) / 2
        
        for retailer in retailers:
            # Source-specific pricing strategy
            source_markup = {
                'Amazon': random.uniform(-15, 10),
                'Best Buy': random.uniform(-5, 20),
                'Walmart': random.uniform(-20, 5),
                'Target': random.uniform(-10, 15),
                'eBay': random.uniform(-25, 0),
                'Newegg': random.uniform(-10, 5)
            }[retailer]
            
            # Generate price history
            for i, date in enumerate(dates):
                # Weekly pattern (prices drop on weekends)
                weekday = date.weekday()
                weekend_factor = 0.95 if weekday >= 5 else 1.0
                
                # Random fluctuations
                noise = np.random.normal(0, 5)
                
                # Trend (prices slowly decrease over time)
                trend = -0.03 * (90 - i) / 90 * 15
                
                # Calculate price
                price = base_price + source_markup + noise + trend
                price = price * weekend_factor
                
                # Ensure price stays within range
                price = max(price_range[0] * 0.85, min(price_range[1] * 1.15, price))
                price = round(price, 2)
                
                # Stock status
                stock_weights = [0.75, 0.15, 0.10]  # In Stock, Limited, Out of Stock
                stock_status = random.choices(['In Stock', 'Limited Stock', 'Out of Stock'], weights=stock_weights)[0]
                
                availability = {
                    'In Stock': 'In Stock - Ships within 2 days',
                    'Limited Stock': 'Only 3 left in stock',
                    'Out of Stock': 'Currently Unavailable'
                }[stock_status]
                
                data.append({
                    'product': product_name,
                    'brand': brand,
                    'category': category,
                    'source': retailer,
                    'price': price,
                    'stock_status': stock_status,
                    'availability': availability,
                    'rating': round(random.uniform(3.5, 4.9), 1),
                    'scraped_at': date.isoformat(),
                    'title': f'{product_name} - {category}',
                    'currency': 'USD'
                })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to database
    db_path = "data/warehouse/prices_large.db"
    conn = sqlite3.connect(db_path)
    df.to_sql('price_history', conn, if_exists='replace', index=False)
    conn.close()
    
    # Save to CSV
    csv_path = f"data/processed/prices_large_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Generated {len(df)} records")
    print(f"   - Products: {df['product'].nunique()}")
    print(f"   - Retailers: {df['source'].nunique()}")
    print(f"   - Categories: {df['category'].nunique()}")
    print(f"   - Price Range:  - ")
    print(f"   - Date Range: {df['scraped_at'].min()} to {df['scraped_at'].max()}")
    print(f"\n📁 Saved to: {db_path}")
    print(f"📁 Saved to: {csv_path}")
    
    # Show sample
    print("\n📊 Sample Data:")
    print(df[['product', 'brand', 'source', 'price', 'stock_status']].head(10))
    
    return df

if __name__ == "__main__":
    generate_large_dataset()
