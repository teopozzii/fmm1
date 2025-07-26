import time
import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')  # Ensure the API key is loaded from .env

def get_fundamentals(ticker, function='o'):
    """
    Fetches the current fundamentals for a given ticker.
    Returns a dictionary with relevant financial metrics.
    """

    if function not in ['o', 'c', 'b', 'i']:
        raise ValueError("Function must be one of 'o' (overview), 'c' (cash flow), 'b' (balance sheet), or 'i' (income statement).")
    function_map = {
        'o': 'OVERVIEW',
        'c': 'CASH_FLOW',
        'b': 'BALANCE_SHEET',
        'i': 'INCOME_STATEMENT'
    }
    function = function_map[function]

    function = function.upper()
    url = f"https://www.alphavantage.co/query?function={function}&symbol={ticker}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    time.sleep(5) # To avoid hitting the API rate limit; needed?

    if function != 'OVERVIEW' and 'annualReports' in data:
        return data['annualReports']
    else:
        return data