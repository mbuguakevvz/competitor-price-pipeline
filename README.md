# Competitive Intelligence & Dynamic Pricing Pipeline

## 🎯 Project Overview
Real-time competitor price monitoring system tracking **Sony WH-1000XM5**, **Bose QC45**, and **Apple AirPods Max** across Amazon, Best Buy, and Walmart.

## 🚀 Features
- **Automated Web Scraping** with anti-detection (rotating user-agents, retry logic)
- **Data Pipeline** with CSV, JSON, and SQLite storage
- **Price Alerts** for significant changes (>15%)
- **Interactive Dashboard** built with Streamlit
- **Scheduled Daily Runs** via Windows Task Scheduler

## 📊 Business Value
- **For E-commerce:** Automated repricing decisions, margin optimization
- **For Procurement:** Forward pricing indicators, bulk buying timing
- **For Analysts:** Alternative data for market predictions

## 🛠️ Tech Stack
- **Scraping:** Requests, BeautifulSoup, Fake-UserAgent, Tenacity
- **Data Processing:** Pandas, NumPy
- **Storage:** SQLite, CSV, JSON
- **Dashboard:** Streamlit, Plotly
- **Scheduling:** Schedule + Windows Task Scheduler

## 📁 Project Structure
\\\
competitor-price-pipeline/
├── src/
│   └── main.py          # Main scraper
├── dashboard/
│   └── app.py           # Streamlit dashboard
├── scripts/
│   └── scheduler.py     # Scheduling script
├── config/
│   └── config.yaml      # Configuration
├── data/
│   ├── raw/            # Raw JSON data
│   ├── processed/      # Processed CSV
│   └── warehouse/      # SQLite database
├── logs/               # Log files
└── requirements.txt    # Dependencies
\\\

## 🚀 Quick Start

### 1. Setup
\\\powershell
# Clone and setup
cd competitor-price-pipeline
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
\\\

### 2. Run Scraper
\\\powershell
python src/main.py
\\\

### 3. Launch Dashboard
\\\powershell
streamlit run dashboard/app.py
\\\

### 4. Schedule Daily Runs
\\\powershell
# Using Windows Task Scheduler
schtasks /create /tn "PriceMonitor" /tr "python C:\path\to\scripts\scheduler.py" /sc daily /st 09:00
\\\

## 📈 Sample Output
![Dashboard](https://via.placeholder.com/800x400)

## 🔮 Future Enhancements
- [ ] ML-based price predictions (Prophet/XGBoost)
- [ ] Slack/Telegram alerts
- [ ] Docker containerization
- [ ] AWS S3 cloud storage

## 👨‍💻 Author
**Kevin Mbugua**
- GitHub: [github.com/mbuguakevvz](https://github.com/mbuguakevvz)

## 📄 License
MIT
