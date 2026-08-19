import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
import numpy as np
import yaml

def generate_global_data():
    """Generate global price data with international retailers"""
    
    # Load configurations
    with open('config/products_extended.yaml', 'r') as f:
        product_config = yaml.safe_load(f)
    
    with open('config/retailers.yaml', 'r') as f:
        retailer_config = yaml.safe_load(f)
    
    products = product_config['products']
    retailers = retailer_config['retailers']
    
    # Currency exchange rates
    exchange_rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'GBP': 0.73,
        'INR': 83.0,
        'MXN': 17.0,
        'CNY': 7.2
    }
    
    # Generate 60 days of data
    dates = [datetime.now() - timedelta(days=i) for i in range(60, -1, -1)]
    
    data = []
    print(f"📊 Generating data for {len(products)} products and {len(retailers)} retailers")
    
    for product in products:
        product_name = product['name']
        price_range = product.get('price_range', [100, 500])
        base_price = sum(price_range) / 2
        
        for retailer in retailers:
            retailer_name = retailer['name']
            region = retailer['region']
            currency = retailer_config['regions'][0]['currency']  # Default
            
            # Find currency for region
            for region_config in retailer_config['regions']:
                if retailer_name in region_config.get('retailers', []):
                    currency = region_config['currency']
                    break
            
            # Regional pricing strategy
            region_multiplier = {
                'US': 1.0,
                'UK': 0.95,
                'Germany': 0.92,
                'China': 0.85,
                'India': 0.70,
                'Latin America': 0.80
            }.get(region, 1.0)
            
            for i, date in enumerate(dates):
                # Pricing factors
                noise = np.random.normal(0, 5)
                trend = -0.02 * (60 - i) / 60 * 10
                weekend_factor = 0.95 if date.weekday() >= 5 else 1.0
                
                # Calculate price in USD then convert
                price_usd = (base_price + noise + trend) * region_multiplier * weekend_factor
                price_usd = max(price_range[0] * 0.8, min(price_range[1] * 1.2, price_usd))
                
                # Convert to local currency
                rate = exchange_rates.get(currency, 1.0)
                price_local = price_usd * rate
                price_local = round(price_local, 2)
                
                # Stock status
                stock_weights = [0.80, 0.10, 0.10]
                stock_status = random.choices(['In Stock', 'Limited Stock', 'Out of Stock'], weights=stock_weights)[0]
                
                data.append({
                    'product': product_name,
                    'source': retailer_name,
                    'region': region,
                    'currency': currency,
                    'price': price_local,
                    'price_usd': round(price_usd, 2),
                    'stock_status': stock_status,
                    'availability': f'{stock_status} - {region}',
                    'rating': round(random.uniform(3.5, 4.9), 1),
                    'scraped_at': date.isoformat(),
                    'title': f'{product_name} - Global Edition'
                })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to database
    db_path = "data/warehouse/prices_global.db"
    conn = sqlite3.connect(db_path)
    df.to_sql('price_history', conn, if_exists='replace', index=False)
    conn.close()
    
    print(f"\n✅ Generated {len(df)} global records")
    print(f"   - Products: {df['product'].nunique()}")
    print(f"   - Retailers: {df['source'].nunique()}")
    print(f"   - Regions: {df['region'].nunique()}")
    print(f"   - Currencies: {df['currency'].nunique()}")
    print(f"   - Price Range: {df['currency'].iloc[0]} {df['price'].min():.2f} - {df['currency'].iloc[0]} {df['price'].max():.2f}")
    print(f"\n📁 Saved to: {db_path}")
    
    # Show summary by region
    print("\n🌍 Regional Summary:")
    region_summary = df.groupby('region').agg({
        'price': ['mean', 'min', 'max'],
        'source': 'nunique'
    }).round(2)
    print(region_summary)
    
    return df

if __name__ == "__main__":
    generate_global_data()
