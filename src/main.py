import yaml
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from loguru import logger
import time
import sys
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import random
import re
import os

# Setup logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.add("logs/pipeline_{time:YYYY-MM-DD}.log", rotation="1 day")

class PriceMonitor:
    def __init__(self, config_path='config/config.yaml'):
        # Create directories if they don't exist
        for dir_path in ['data/raw', 'data/processed', 'data/warehouse', 'logs']:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.ua = UserAgent()
        self.results = []
        self.session = requests.Session()
        
    def get_headers(self):
        """Generate realistic browser headers"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def fetch_page(self, url):
        """Fetch page with retry logic and random delays"""
        # Random delay between 1-3 seconds to avoid detection
        delay = random.uniform(1, 3)
        time.sleep(delay)
        
        headers = self.get_headers()
        
        response = self.session.get(
            url, 
            headers=headers, 
            timeout=15,
            allow_redirects=True
        )
        
        # Check if we got blocked
        if response.status_code == 403 or response.status_code == 429:
            logger.warning(f"⚠️ Got blocked (status {response.status_code}), waiting...")
            time.sleep(20)
            headers['User-Agent'] = self.ua.random
            response = self.session.get(url, headers=headers, timeout=15)
            
        response.raise_for_status()
        
        # Check if we got a captcha page
        if 'captcha' in response.text.lower() or 'robot' in response.text.lower():
            logger.warning("⚠️ Captcha detected! Skipping...")
            raise Exception("Captcha detected")
            
        return response
    
    def extract_price(self, soup, selectors):
        """Extract price using multiple selectors - FIXED version"""
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.text.strip()
                    # Clean price text - handle $ and commas properly
                    # Remove everything except digits, dots, and commas
                    price_clean = re.sub(r'[^\d.,]', '', price_text)
                    
                    # Handle the case where price has no decimal point (e.g., "32093" -> "320.93")
                    if price_clean and len(price_clean) > 2:
                        # If there's no decimal point, assume last two digits are cents
                        if '.' not in price_clean and ',' not in price_clean:
                            if len(price_clean) >= 3:
                                # Insert decimal before last two digits
                                price_clean = price_clean[:-2] + '.' + price_clean[-2:]
                    
                    # Remove commas
                    price_clean = price_clean.replace(',', '')
                    
                    if price_clean:
                        price = float(price_clean)
                        # Check if price is reasonable (between  and  for headphones)
                        if 10 <= price <= 2000:
                            return price
                        else:
                            # If price seems too high, try to fix it
                            if price > 2000:
                                # Try dividing by 100 (handles cases where decimal was missing)
                                fixed_price = price / 100
                                if 10 <= fixed_price <= 2000:
                                    return fixed_price
            except Exception as e:
                continue
        return None
    
    def scrape_amazon(self, asin, product_name):
        """Scrape Amazon with fallback methods"""
        url = f"https://www.amazon.com/dp/{asin}"
        logger.info(f"🛒 Scraping Amazon: {product_name}")
        
        try:
            response = self.fetch_page(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple price selectors
            price_selectors = [
                '.a-price-whole',
                '.priceToPay span.a-price-whole',
                '.a-price .a-offscreen',
                '#corePrice_desktop .a-price-whole',
                '.a-price[data-a-size="xl"] .a-price-whole',
                '.a-price[data-a-size="l"] .a-price-whole'
            ]
            price = self.extract_price(soup, price_selectors)
            
            # Get title
            title_elem = soup.select_one('#productTitle')
            title = title_elem.text.strip() if title_elem else product_name
            
            # Get availability
            avail_selectors = [
                '#availability span.a-size-medium',
                '#availability .a-size-medium',
                '.availability .a-size-medium',
                '#availability'
            ]
            availability = 'Unknown'
            for selector in avail_selectors:
                elem = soup.select_one(selector)
                if elem:
                    availability = elem.text.strip()
                    break
            
            # Get rating
            rating_elem = soup.select_one('.a-icon-alt')
            rating = None
            if rating_elem:
                rating_match = re.search(r'(\d+\.?\d*)', rating_elem.text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Determine stock status
            stock_status = 'Unknown'
            if price:
                if 'out of stock' in availability.lower() or 'currently unavailable' in availability.lower():
                    stock_status = 'Out of Stock'
                else:
                    stock_status = 'In Stock'
            
            result = {
                'product': product_name,
                'source': 'Amazon',
                'product_id': asin,
                'title': title,
                'price': price,
                'currency': 'USD',
                'availability': availability,
                'stock_status': stock_status,
                'rating': rating,
                'scraped_at': datetime.now().isoformat()
            }
            
            logger.success(f"✅ Amazon {product_name}: ")
            return result
            
        except Exception as e:
            logger.error(f"❌ Amazon error: {str(e)}")
            return {
                'product': product_name,
                'source': 'Amazon',
                'product_id': asin,
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def scrape_bestbuy(self, sku, product_name):
        """Scrape Best Buy"""
        url = f"https://www.bestbuy.com/site/{sku}/p.p"
        logger.info(f"🛒 Scraping Best Buy: {product_name}")
        
        try:
            response = self.fetch_page(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_selectors = [
                '.priceView-customer-price span',
                '.priceView-hero-price span',
                '[data-testid="customer-price"] span',
                '.price-now',
                '.priceView-current-price span'
            ]
            price = self.extract_price(soup, price_selectors)
            
            title_elem = soup.select_one('h1')
            title = title_elem.text.strip() if title_elem else product_name
            
            avail_elem = soup.select_one('[data-testid="fulfillment-message"]')
            availability = avail_elem.text.strip() if avail_elem else 'Unknown'
            
            stock_status = 'In Stock' if price else 'Out of Stock'
            
            result = {
                'product': product_name,
                'source': 'Best Buy',
                'product_id': sku,
                'title': title,
                'price': price,
                'currency': 'USD',
                'availability': availability,
                'stock_status': stock_status,
                'scraped_at': datetime.now().isoformat()
            }
            
            logger.success(f"✅ Best Buy {product_name}: ")
            return result
            
        except Exception as e:
            logger.error(f"❌ Best Buy error: {str(e)}")
            return {
                'product': product_name,
                'source': 'Best Buy',
                'product_id': sku,
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def scrape_walmart(self, product_id, product_name):
        """Scrape Walmart"""
        url = f"https://www.walmart.com/ip/{product_id}"
        logger.info(f"🛒 Scraping Walmart: {product_name}")
        
        try:
            response = self.fetch_page(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_selectors = [
                '[data-testid="price"]',
                '.price-main',
                '.price-now',
                '.price-group .price-now',
                '.price-current'
            ]
            price = self.extract_price(soup, price_selectors)
            
            title_elem = soup.select_one('h1')
            title = title_elem.text.strip() if title_elem else product_name
            
            avail_elem = soup.select_one('[data-testid="fulfillment-message"]')
            availability = avail_elem.text.strip() if avail_elem else 'Unknown'
            
            stock_status = 'In Stock' if price else 'Out of Stock'
            
            result = {
                'product': product_name,
                'source': 'Walmart',
                'product_id': product_id,
                'title': title,
                'price': price,
                'currency': 'USD',
                'availability': availability,
                'stock_status': stock_status,
                'scraped_at': datetime.now().isoformat()
            }
            
            logger.success(f"✅ Walmart {product_name}: ")
            return result
            
        except Exception as e:
            logger.error(f"❌ Walmart error: {str(e)}")
            return {
                'product': product_name,
                'source': 'Walmart',
                'product_id': product_id,
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def save_results(self):
        """Save results to CSV, JSON, and SQLite"""
        if not self.results:
            logger.warning("No results to save!")
            return None
            
        df = pd.DataFrame(self.results)
        
        # Save to CSV
        csv_path = f"data/processed/prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"💾 Saved CSV: {csv_path}")
        
        # Save to JSON
        json_path = f"data/raw/prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        df.to_json(json_path, orient='records', indent=2)
        logger.info(f"💾 Saved JSON: {json_path}")
        
        # Save to SQLite
        db_path = "data/warehouse/prices.db"
        conn = sqlite3.connect(db_path)
        df.to_sql('price_history', conn, if_exists='append', index=False)
        conn.close()
        logger.info(f"💾 Saved to SQLite: {db_path}")
        
        return df
    
    def check_price_alerts(self, df):
        """Check for significant price changes"""
        if df is None or len(df) < 2:
            return
            
        # Check for prices below  (good deal alert)
        cheap_products = df[df['price'] < 200]
        if not cheap_products.empty:
            for _, row in cheap_products.iterrows():
                logger.warning(f"🔔 DEAL ALERT: {row['product']} at {row['source']} is ")
    
    def run(self):
        """Main pipeline runner"""
        logger.info("🚀 Starting Competitive Intelligence Pipeline")
        logger.info("=" * 50)
        
        for product in self.config['products']:
            name = product['name']
            identifiers = product['identifiers']
            
            # Scrape each source
            if 'amazon' in identifiers:
                result = self.scrape_amazon(identifiers['amazon'], name)
                self.results.append(result)
                time.sleep(2)  # Small delay between requests
            
            if 'bestbuy' in identifiers:
                result = self.scrape_bestbuy(identifiers['bestbuy'], name)
                self.results.append(result)
                time.sleep(2)
            
            if 'walmart' in identifiers:
                result = self.scrape_walmart(identifiers['walmart'], name)
                self.results.append(result)
                time.sleep(2)
            
            logger.info("-" * 30)
        
        # Save all results
        df = self.save_results()
        if df is not None:
            self.check_price_alerts(df)
        
        logger.info("=" * 50)
        logger.success("✅ Pipeline completed successfully!")
        
        # Print summary
        if df is not None and not df.empty:
            print("\n📊 PRICE SUMMARY:")
            print(df[['product', 'source', 'price', 'stock_status']].to_string(index=False))
        else:
            print("\n⚠️ No data was scraped. Check the logs for errors.")
        
        return df

if __name__ == "__main__":
    import sqlite3
    monitor = PriceMonitor()
    monitor.run()
