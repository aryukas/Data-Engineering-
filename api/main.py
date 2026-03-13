import random
from fastapi import FastAPI, HTTPException
from data_generator import generate_market_data, generate_malformed_data

app = FastAPI(title="Mock Market Data API")

@app.get("/v1/market-data")
async def get_market_data():
    """
    Returns synthetic market data.
    Implements 5% fault injection:
    - 2.5% chance of 500 Internal Server Error
    - 2.5% chance of returning malformed data
    """
    chaos_roll = random.random()
    
    if chaos_roll < 0.025:
        # 2.5% chance of 500 error
        raise HTTPException(status_code=500, detail="Internal Server Error (Chaos Injection)")
    
    if chaos_roll < 0.05:
        # 2.5% chance of malformed data
        return generate_malformed_data()
    
    return generate_market_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
