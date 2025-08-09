import pandas as pd
import time
import requests
from dotenv import load_dotenv
import os
import glob
from pathlib import Path
from datetime import date
from IPython.core.magic import (Magics, magics_class, cell_magic)
from IPython import get_ipython
import psutil

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
    
def load_fundamentals(current_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Return a DataFrame containing the latest fundamentals data,
    falling back from today's file ➜ most-recent dated file ➜ legacy file.
    """
    today       = date.today().isoformat()
    data_root   = Path("data")
    today_dir   = data_root / today

    # 1️⃣  today’s file
    today_file  = today_dir / f"fundamentals_{today}.csv"

    # 2️⃣  most-recent dated file in any sub-directory
    pattern     = str(data_root / "*" / "fundamentals_*.csv")
    dated_files = glob.glob(pattern)
    most_recent = max(dated_files, default=None, key=Path) if dated_files else None

    # 3️⃣  legacy top-level file
    legacy_file = data_root / "fundamentals.csv"

    for candidate in (today_file, most_recent, legacy_file):
        if candidate and Path(candidate).exists():
            latest = pd.read_csv(candidate, na_values=['-']) # void values found in some rows
            latest.drop(columns=latest.filter(regex=r"^Unnamed").columns, inplace=True, errors="ignore")
            break
    else:                              # --> no file found
        raise FileNotFoundError("No fundamentals file available.")

    # 4️⃣ to link the currently loaded data with the already existing one
    if current_df is not None and not current_df.empty:
        latest = pd.concat([current_df, latest])
        latest.drop(columns=latest.filter(regex=r"^Unnamed").columns, inplace=True, errors="ignore")
        latest.drop(columns='index', inplace=True, errors="ignore")
        latest.reset_index(drop = True, inplace=True)

    return latest

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

@magics_class
class TrafficMagic(Magics):

    @cell_magic
    def nettraffic(self, line, cell):
        net_io_start = psutil.net_io_counters()

        exec(cell, globals())  # esegue il contenuto della cella

        net_io_end = psutil.net_io_counters()
        sent_diff = (net_io_end.bytes_sent - net_io_start.bytes_sent) / (1024 ** 2)
        recv_diff = (net_io_end.bytes_recv - net_io_start.bytes_recv) / (1024 ** 2)

        print(f"{sent_diff:.2f} MB inviati; {recv_diff:.2f} MB ricevuti.")

def register_traffic_magic():
    ip = get_ipython()
    ip.register_magics(TrafficMagic)