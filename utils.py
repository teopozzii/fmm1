import pandas as pd
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

    if function != 'OVERVIEW' and 'quarterlyReports' in data:
        return data['quarterlyReports']
    elif function != 'OVERVIEW' and 'annualReports' in data:
        return data['annualReports']
    else:
        return data
    

def compute_book_value_per_share(fundamentals):
    """
    Computes Book Value Per Share (BVPS) and inserts it into the BALANCE_SHEET sub-dataframe.

    Priority:
    1. (totalAssets - totalLiabilities) / commonStockSharesOutstanding
    2. totalShareholderEquity / commonStockSharesOutstanding

    Modifies the input DataFrame in-place by adding:
        ('BALANCE_SHEET', 'bookValuePerShare'): Book Value Per Share
    """

    index = fundamentals.index
    # Pull inputs safely
    get = lambda col: fundamentals[col] if col in fundamentals else pd.Series(index=index, dtype='float64')
    
    total_assets = get(('BALANCE_SHEET', 'totalAssets'))
    total_liabilities = get(('BALANCE_SHEET', 'totalLiabilities'))
    total_equity = get(('BALANCE_SHEET', 'totalShareholderEquity'))
    shares_outstanding = get(('BALANCE_SHEET', 'commonStockSharesOutstanding'))

    # Priority 1: (Assets - Liabilities) / Shares
    bvps_1 = (total_assets - total_liabilities) / shares_outstanding
    
    # Priority 2: Equity / Shares
    bvps_2 = total_equity / shares_outstanding
    # Priority 3: Rely on latest data provided by OVERVIEW
    bvps_3 = fundamentals[('OVERVIEW', 'BookValue')]

    book_value_per_share = bvps_1.combine_first(bvps_2).combine_first(bvps_3)

    # Add to DataFrame
    fundamentals[('BALANCE_SHEET', 'bookValuePerShare')] = book_value_per_share
    return fundamentals

def next_quarter(date: str):
    
    yr = int(date[:4]) # current year

    if date.endswith("12-31"):
        yr = str(yr + 1)

        datenew = f"{yr}-03-31"
    
    elif date.endswith("03-31"):
        datenew = f"{yr}-06-30"
    
    elif date.endswith("06-30"):
        datenew = f"{yr}-09-30"
    
    elif date.endswith("09-30"):
        datenew = f"{yr}-12-31"
    
    else:
        raise ValueError("Something wrong with the date!")
    return datenew