import os
import time
import pandas as pd
from datetime import datetime, timedelta
from fyers_apiv3 import fyersModel

# --- CONFIGURATION ---
# Replace these with your actual Fyers API credentials
CLIENT_ID = os.getenv("FYERS_APP_ID", "YOUR_CLIENT_ID_HERE")
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")

SYMBOL = "NSE:RELIANCE-EQ"
RESOLUTION = "5" # 5 minute candles
CHUNK_DAYS = 100 # Max calendar days per request for intraday data
MAX_YEARS = 6 # Will stop looping after these many years even if data exists
CSV_FILENAME = "RELIANCE_5m_data.csv"

def get_fyers_client():
    return fyersModel.FyersModel(
        client_id=CLIENT_ID,
        is_async=False,
        token=ACCESS_TOKEN,
        log_path=""
    )

def fetch_chunk_with_retry(fyers, data_params, max_retries=5):
    retries = 0
    backoff = 2 # seconds
    
    while retries <= max_retries:
        try:
            response = fyers.history(data=data_params)
            
            if response.get("s") == "ok":
                return response.get("candles", [])
            elif response.get("s") == "error":
                err_msg = response.get("message", "")
                print(f"  API Error Response: {err_msg}")
                # We will retry on error regardless, to handle rate limits
                
        except Exception as e:
            print(f"  Exception during API call: {e}")
            
        print(f"  Retrying in {backoff} seconds... (Attempt {retries + 1}/{max_retries})")
        time.sleep(backoff)
        backoff *= 2
        retries += 1
        
    print("  Max retries reached. Returning empty for this chunk.")
    return []

def main():
    if CLIENT_ID == "YOUR_CLIENT_ID_HERE" or ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE":
        print("ERROR: Please update CLIENT_ID and ACCESS_TOKEN in the script before running.")
        return

    fyers = get_fyers_client()
    
    end_date = datetime.now()
    all_candles = []
    
    print(f"Starting data extraction for {SYMBOL} (Resolution: {RESOLUTION}m)")
    print("Looping backward in 100-day chunks to fetch maximum available history...")
    print("-" * 50)
    
    # Calculate maximum loops to avoid infinite loops
    max_loops = int((365 * MAX_YEARS) / CHUNK_DAYS)
    
    for _ in range(max_loops):
        start_date = end_date - timedelta(days=CHUNK_DAYS - 1)
        
        # Format dates as YYYY-MM-DD
        range_from = start_date.strftime("%Y-%m-%d")
        range_to = end_date.strftime("%Y-%m-%d")
        
        data_params = {
            "symbol": SYMBOL,
            "resolution": RESOLUTION,
            "date_format": "1", # 1 means YYYY-MM-DD format
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1" # 1 for continuous data / adjusted for corporate actions
        }
        
        print(f"Fetching from {range_from} to {range_to}...")
        
        chunk_candles = fetch_chunk_with_retry(fyers, data_params)
        
        if not chunk_candles:
            print("No more data returned by the API (or hit a wall). Stopping extraction.")
            break
            
        all_candles.extend(chunk_candles)
        print(f"  -> Successfully fetched {len(chunk_candles)} candles.")
        
        # Move end_date backwards for the next chunk
        # Minus 1 day so ranges don't overlap
        end_date = start_date - timedelta(days=1)
        
        # Normal rate limiting delay to avoid hitting limits immediately (Fyers allows ~5-10 req/sec)
        time.sleep(0.5)

    if all_candles:
        print("-" * 50)
        print("Processing and saving data...")
        # Fyers returns: [Timestamp (Epoch), Open, High, Low, Close, Volume]
        df = pd.DataFrame(all_candles, columns=['epoch', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert epoch to IST datetime (Fyers epoch is in seconds)
        df['datetime'] = pd.to_datetime(df['epoch'], unit='s')
        df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        
        # Drop epoch and set datetime as first column
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        
        # Sort by datetime ascending (since we appended backward in chunks, older dates might be later in list)
        df.sort_values('datetime', inplace=True)
        # Drop duplicates just in case there's any overlap at the edges
        df.drop_duplicates(subset=['datetime'], inplace=True)
        
        # Save to CSV
        df.to_csv(CSV_FILENAME, index=False)
        print(f"\nSuccess! Total {len(df)} candles extracted.")
        print(f"Data saved to: {os.path.abspath(CSV_FILENAME)}")
        print(f"Data range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    else:
        print("No data was extracted.")

if __name__ == "__main__":
    main()
