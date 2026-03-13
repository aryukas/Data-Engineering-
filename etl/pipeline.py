import time
import requests
import os
from typing import List, Dict, Tuple
from datetime import datetime
from models import MarketData, ProcessedMarketData
from db import insert_market_data
from logger import get_logger

logger = get_logger(__name__)

API_URL = os.getenv("API_URL", "http://api:8000/v1/market-data")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

def fetch_data(url: str, retries: int = 3, backoff: float = 1.0) -> List[Dict]:
    """Fetches data from the API with retries and exponential backoff."""
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.warning(f"Attempt {i+1} failed: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 2
    logger.error(f"Failed to fetch data after {retries} retries.")
    return []

def process_batch(raw_data: List[Dict]) -> Tuple[List[ProcessedMarketData], int]:
    """Validates, transforms, and detects outliers in a batch of records."""
    valid_records: List[MarketData] = []
    # Using a list to hold the counter to bypass Pyre's internal error with int addition
    stats = {"dropped": 0}
    
    # Validation
    for item in raw_data:
        try:
            valid_records.append(MarketData(**item))
        except Exception as e:
            logger.warning(f"Validation failed for record: {item}. Error: {e}")
            dropped_count = int(stats["dropped"])
            stats["dropped"] = dropped_count + 1
            
    if not valid_records:
        return [], int(stats["dropped"])

    # Transformation & Outlier Detection
    processed_records: List[ProcessedMarketData] = []
    
    # Group by instrument to compute batch stats
    by_instrument: Dict[str, List[MarketData]] = {}
    for r in valid_records:
        if r.instrument_id not in by_instrument:
            by_instrument[r.instrument_id] = []
        by_instrument[r.instrument_id].append(r)
        
    for instrument_id, records in by_instrument.items():
        total_value = sum(float(r.price * r.volume) for r in records)
        total_volume = sum(float(r.volume) for r in records)
        vwap = float(total_value / total_volume) if total_volume > 0 else 0.0
        
        avg_price = float(sum(float(r.price) for r in records) / len(records))
        
        for r in records:
            # Outlier detection: > 15% deviation from batch average price
            price_diff = float(abs(r.price - avg_price))
            is_outlier = bool(price_diff / avg_price > 0.15) if avg_price > 0 else False
            
            processed_records.append(ProcessedMarketData(
                **r.model_dump(),
                vwap=float(round(vwap, 4)),
                is_outlier=is_outlier
            ))
            
    return processed_records, int(stats["dropped"])

def run_pipeline():
    """Main pipeline loop."""
    logger.info("Starting ETL Pipeline...")
    while True:
        start_time = float(time.time())
        
        # 1. Extraction
        raw_data = fetch_data(API_URL)
        
        if raw_data:
            # 2. Validation, 3. Transformation, 4. Outlier Detection
            processed_data, dropped = process_batch(raw_data)
            
            # 5. Load
            if processed_data:
                insert_market_data(processed_data)
            
            execution_time = float(time.time() - start_time)
            logger.info("Batch processed", extra={
                "extra_data": {
                    "records_processed": len(processed_data),
                    "records_dropped": dropped,
                    "execution_time_seconds": float(round(execution_time, 4))
                }
            })
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    # Wait for other services to be ready (simplified)
    time.sleep(5)
    run_pipeline()
