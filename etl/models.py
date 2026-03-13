from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

class MarketData(BaseModel):
    instrument_id: str
    price: float
    volume: float
    timestamp: datetime

    @field_validator('price', 'volume', mode='before')
    @classmethod
    def ensure_float(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"Could not convert {v} to float")
        return v

class ProcessedMarketData(MarketData):
    vwap: float
    is_outlier: bool
