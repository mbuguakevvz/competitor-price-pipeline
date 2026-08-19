import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Competitive Intelligence Dashboard", layout="wide")

st.title("📊 Competitive Intelligence Dashboard")
st.markdown("### Real-time competitor price monitoring")

# Load data
@st.cache_data
def load_data():
    db_path = "data/warehouse/prices.db"
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        try:
            df = pd.read_sql_query("SELECT * FROM price_history ORDER BY scraped_at DESC", conn)
            conn.close()
            return df
        except:
            conn.close()
            return pd.DataFrame()
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data found in the database.")
    st.info("📌 Run this command first to generate mock data:")
    st.code("python scripts/generate_mock_data.py", language="bash")
    st.stop()

# Convert scraped_at to datetime
df['scraped_at'] = pd.to_datetime(df['scraped_at'])

# Sidebar filters
st.sidebar.header("🔍 Filters")
products = st.sidebar.multiselect(
    "Select Products", 
    df['product'].unique(), 
    default=df['product'].unique()
)
sources = st.sidebar.multiselect(
    "Select Sources", 
    df['source'].unique(), 
    default=df['source'].unique()
)

filtered_df = df[df['product'].isin(products) & df['source'].isin(sources)]

if filtered_df.empty:
    st.warning("No data matches your filters")
    st.stop()

# Metrics
col1, col2, col3, col4 = st.columns(4)

# Get latest prices for each product
latest_data = filtered_df.groupby(['product', 'source']).last().reset_index()
latest_prices = latest_data[latest_data['price'].notna()]['price']

with col1:
    st.metric("📦 Total Products", filtered_df['product'].nunique())
with col2:
    st.metric("🏪 Total Sources", filtered_df['source'].nunique())
with col3:
    if not latest_prices.empty:
        st.metric("💰 Lowest Price", f"")
    else:
        st.metric("💰 Lowest Price", "N/A")
with col4:
    if not latest_prices.empty:
        st.metric("💎 Highest Price", f"")
    else:
        st.metric("💎 Highest Price", "N/A")

# Price chart
st.subheader("📈 Price History by Product")
fig = px.line(
    filtered_df[filtered_df['price'].notna()],
    x='scraped_at',
    y='price',
    color='product',
    facet_col='source',
    title='Price Trends Across Competitors',
    labels={'price': 'Price (USD)', 'scraped_at': 'Date'},
    markers=True
)
st.plotly_chart(fig, use_container_width=True)

# Current prices table
st.subheader("💰 Current Prices")
current = filtered_df.groupby(['product', 'source']).last().reset_index()
current = current[current['price'].notna()]
st.dataframe(
    current[['product', 'source', 'price', 'stock_status', 'scraped_at']],
    column_config={
        'price': st.column_config.NumberColumn(
            "Price",
            format="$%.2f"
        ),
        'scraped_at': st.column_config.DatetimeColumn(
            "Last Scraped",
            format="YYYY-MM-DD HH:mm"
        ),
        'stock_status': st.column_config.Column(
            "Stock Status",
            width="small"
        )
    },
    use_container_width=True,
    hide_index=True
)

# Two-column layout for stock and comparison
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📦 Stock Status Distribution")
    stock_counts = filtered_df[filtered_df['stock_status'].notna()]['stock_status'].value_counts()
    if not stock_counts.empty:
        st.bar_chart(stock_counts)
    else:
        st.info("No stock data available")

with col_right:
    st.subheader("🏷️ Price Comparison (Latest)")
    pivot = filtered_df.pivot_table(
        index='product',
        columns='source',
        values='price',
        aggfunc='last'
    )
    if not pivot.empty:
        # Format and highlight
        styled = pivot.style.format("")
        # Add conditional formatting if there are multiple products
        if len(pivot) > 1:
            styled = styled.highlight_min(color='lightgreen', axis=None)
            styled = styled.highlight_max(color='lightcoral', axis=None)
        st.dataframe(styled, use_container_width=True)
    else:
        st.info("No price data available")

# Bottom section: Raw data
with st.expander("📋 View Raw Data", expanded=False):
    st.dataframe(filtered_df, use_container_width=True)
    
    # Download buttons
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"price_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.info(
    f"""
    **Pipeline Info:**
    - Total Records: {len(filtered_df)}
    - Last Update: {filtered_df['scraped_at'].max().strftime('%Y-%m-%d %H:%M')}
    - Sources: {', '.join(filtered_df['source'].unique())}
    """
)

# Additional features
st.sidebar.markdown("---")
st.sidebar.success("🎯 **Pro Tip:** This dashboard automatically updates with new data from the scraper pipeline!")
