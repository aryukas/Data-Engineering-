import random
from datetime import datetime, timezone
from typing import List, Dict, Union

INSTRUMENTS = ["AAPL", "BTC-USD", "ETH-USD", "TSLA"]

def generate_market_data() -> List[Dict[str, Union[str, float]]]:
    """Generates synthetic market data for a list of instruments."""
    data = []
    for instrument in INSTRUMENTS:
        # Explicitly calculating values to help linter type inference
        if "USD" in instrument:
            base_price = float(random.uniform(100, 50000))
        else:
            base_price = float(random.uniform(100, 300))
            
        data.append({
            "instrument_id": instrument,
            "price": float(round(base_price, 2)),
            "volume": float(round(float(random.uniform(0.1, 1000)), 2)),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return data

def generate_malformed_data() -> List[Dict[str, Union[str, float]]]:
    """Generates malformed market data for chaos testing."""
    data = generate_market_data()
    if data:
        # Pick a random record and make price a string
        idx = random.randint(0, len(data) - 1)
        data[idx]["price"] = "INVALID_PRICE"
    return data
