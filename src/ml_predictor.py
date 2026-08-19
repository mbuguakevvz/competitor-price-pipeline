import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from prophet import Prophet
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

class PricePredictor:
    def __init__(self, db_path='data/warehouse/prices.db'):
        self.db_path = db_path
        self.models = {}
        self.predictions = {}
        
    def load_data(self, product_name=None):
        """Load price data from database"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM price_history"
        if product_name:
            query += f" WHERE product = '{product_name}'"
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['scraped_at'] = pd.to_datetime(df['scraped_at'])
        return df
    
    def prepare_prophet_data(self, df, product_name, source):
        """Prepare data for Prophet model"""
        product_df = df[(df['product'] == product_name) & (df['source'] == source)]
        product_df = product_df.sort_values('scraped_at')
        
        # Prophet requires columns: ds, y
        prophet_df = product_df[['scraped_at', 'price']].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df = prophet_df.dropna()
        
        return prophet_df
    
    def train_models(self, df):
        """Train Prophet models for each product-source combination"""
        combinations = df[['product', 'source']].drop_duplicates()
        
        for _, row in combinations.iterrows():
            product = row['product']
            source = row['source']
            key = f"{product}_{source}"
            
            try:
                prophet_df = self.prepare_prophet_data(df, product, source)
                
                if len(prophet_df) < 10:
                    print(f"⚠️ Not enough data for {key}")
                    continue
                
                # Initialize and train Prophet model
                model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=True,
                    changepoint_prior_scale=0.05,
                    seasonality_prior_scale=10.0
                )
                model.fit(prophet_df)
                
                self.models[key] = model
                print(f"✅ Trained model for {key}")
                
            except Exception as e:
                print(f"❌ Error training {key}: {str(e)}")
    
    def predict_future(self, df, days=30):
        """Generate future price predictions"""
        combinations = df[['product', 'source']].drop_duplicates()
        
        for _, row in combinations.iterrows():
            product = row['product']
            source = row['source']
            key = f"{product}_{source}"
            
            if key not in self.models:
                continue
            
            try:
                # Create future dataframe
                future = self.models[key].make_future_dataframe(periods=days)
                forecast = self.models[key].predict(future)
                
                # Extract predictions
                predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days)
                predictions.columns = ['date', 'predicted_price', 'lower_bound', 'upper_bound']
                predictions['product'] = product
                predictions['source'] = source
                
                self.predictions[key] = predictions
                print(f"✅ Generated predictions for {key}")
                
            except Exception as e:
                print(f"❌ Error predicting {key}: {str(e)}")
        
        return self.predictions
    
    def get_best_deal_prediction(self, days=7):
        """Find the best predicted price in the next X days"""
        all_predictions = pd.DataFrame()
        
        for key, df in self.predictions.items():
            all_predictions = pd.concat([all_predictions, df])
        
        if all_predictions.empty:
            return None
        
        # Find the lowest predicted price per product
        best_deals = all_predictions.loc[
            all_predictions.groupby('product')['predicted_price'].idxmin()
        ]
        
        return best_deals[['product', 'source', 'date', 'predicted_price']]
    
    def plot_predictions(self, product_name=None, source=None):
        """Visualize predictions"""
        if not self.predictions:
            print("No predictions available. Run predict_future() first.")
            return
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Sony WH-1000XM5', 'Bose QuietComfort 45', 
                           'Apple AirPods Max', 'Sennheiser Momentum 4')
        )
        
        row = 1
        col = 1
        products = list(self.predictions.keys())
        
        for key in products[:4]:  # Show first 4 products
            predictions = self.predictions[key]
            product = predictions['product'].iloc[0]
            
            fig.add_trace(
                go.Scatter(
                    x=predictions['date'],
                    y=predictions['predicted_price'],
                    mode='lines',
                    name=f"{product} (predicted)",
                    line=dict(color='blue', dash='dash')
                ),
                row=row, col=col
            )
            
            fig.add_trace(
                go.Scatter(
                    x=predictions['date'],
                    y=predictions['upper_bound'],
                    mode='lines',
                    name=f"{product} (upper)",
                    line=dict(color='lightblue', width=0),
                    showlegend=False
                ),
                row=row, col=col
            )
            
            fig.add_trace(
                go.Scatter(
                    x=predictions['date'],
                    y=predictions['lower_bound'],
                    mode='lines',
                    name=f"{product} (lower)",
                    line=dict(color='lightblue', width=0),
                    fill='tonexty',
                    fillcolor='rgba(173, 216, 230, 0.3)',
                    showlegend=False
                ),
                row=row, col=col
            )
            
            # Update layout for each subplot
            fig.update_yaxes(title_text="Price (USD)", row=row, col=col)
            
            # Update row/col counters
            if col < 2:
                col += 1
            else:
                col = 1
                row += 1
        
        fig.update_layout(
            height=600,
            title_text="📈 Price Predictions (Next 30 Days)",
            showlegend=True
        )
        
        return fig

# Usage example
if __name__ == "__main__":
    predictor = PricePredictor()
    
    # Load data
    print("📊 Loading data...")
    df = predictor.load_data()
    
    # Train models
    print("🤖 Training prediction models...")
    predictor.train_models(df)
    
    # Generate predictions
    print("🔮 Generating future predictions...")
    predictions = predictor.predict_future(df, days=30)
    
    # Get best deals
    print("💰 Finding best deals...")
    best_deals = predictor.get_best_deal_prediction()
    if best_deals is not None:
        print("\n🏆 Best Predicted Deals:")
        print(best_deals)
    
    # Plot predictions
    print("\n📈 Creating prediction charts...")
    fig = predictor.plot_predictions()
    if fig:
        fig.show()
