import os
import csv
import zipfile
import io
import time
import logging
from datetime import datetime
import urllib.request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

class ExternalDataService:
    def __init__(self, db_manager):
        self.db = db_manager
        self.base_url_udiff = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{}_F_0000.csv.zip"
        self.base_url_delivery = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{}.csv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }
        self.cookie_jar = {}
        
    def _bootstrap_session(self):
        """Fetch nseindia.com homepage to acquire Akamai/Cloudflare cookies."""
        logger.info("Bootstrapping NSE session cookies...")
        req = urllib.request.Request("https://www.nseindia.com/", headers=self.headers)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            cookie_header = resp.headers.get('Set-Cookie')
            if cookie_header:
                self.headers['Cookie'] = cookie_header
            time.sleep(3) # Politeness delay
            logger.info("NSE session bootstrapped successfully.")
        except Exception as e:
            logger.warning(f"Failed to bootstrap session: {e}")

    def fetch_udiff_bhavcopy(self, date_str: str) -> bool:
        """Fetches UDiFF Bhavcopy for a given date YYYYMMDD"""
        self._bootstrap_session()
        
        url = self.base_url_udiff.format(date_str)
        req = urllib.request.Request(url, headers=self.headers)
        try:
            logger.info(f"Fetching UDiFF Bhavcopy: {url}")
            resp = urllib.request.urlopen(req, timeout=15)
            content = resp.read()
            
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                csv_filename = z.namelist()[0]
                with z.open(csv_filename) as f:
                    data = f.read().decode('utf-8')
            
            self._process_udiff_csv(data)
            logger.info("Successfully fetched and processed UDiFF Bhavcopy.")
            return True
        except HTTPError as e:
            if e.code == 403:
                logger.warning("NSE archives returned HTTP 403 Forbidden. Falling back to local imports.")
            else:
                logger.error(f"HTTPError {e.code}: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Failed to fetch UDiFF Bhavcopy: {e}")
            return False
            
    def fetch_delivery_data(self, date_str: str) -> bool:
        """Fetches delivery percentage data for DDMMYYYY"""
        time.sleep(3) # Hard throttle: <= 1 req / 3s
        self._bootstrap_session()
        
        url = self.base_url_delivery.format(date_str)
        req = urllib.request.Request(url, headers=self.headers)
        try:
            logger.info(f"Fetching Delivery Data: {url}")
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read().decode('utf-8')
            self._process_delivery_csv(data)
            logger.info("Successfully fetched and processed Delivery Data.")
            return True
        except Exception as e:
            logger.warning(f"Failed to fetch Delivery Data: {e}")
            return False
            
    def _process_udiff_csv(self, csv_data: str):
        # Implementation to process UDiFF Bhavcopy and ingest to DuckDB
        # Example schema: TckrSymb, FinInstrmNm, SctySrs, etc.
        reader = csv.DictReader(io.StringIO(csv_data))
        # Just processing logic here, can populate security metrics in future
        count = sum(1 for row in reader)
        logger.info(f"Parsed {count} rows from UDiFF Bhavcopy")
        
    def _process_delivery_csv(self, csv_data: str):
        reader = csv.DictReader(io.StringIO(csv_data))
        count = sum(1 for row in reader)
        logger.info(f"Parsed {count} rows from Delivery Data")
