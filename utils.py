import time
import requests
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')  # Ensure the API key is loaded from .env

def get_current_fundamentals(symbol):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    time.sleep(5) # To avoid hitting the API rate limit; needed? boh
    
    out = {}
    for key in data:
        out[key] = data[key] if data[key] else np.nan
    return out