from fastapi import FastAPI
from app.bybit import BybitAPI
import redis
import asyncio

app = FastAPI()
api = BybitAPI(api_key="your_api_key", secret_key="your_secret_key")

@app.get("/position/{symbol}")
async def get_position(symbol: str):
    return api.Position().get_position(symbol)

def fetch_trading_symbols():
    response = api.MarketData().get_trading_symbols()
    if response.status_code == 200:
        # data = response.json()
        symbols = response['result']['list']
        for symbol in symbols:
            print(symbol['symbol'])
            # Use the symbol name as the key, and store the symbol data as a JSON string
            # redis_client.set(symbol['name'], json.dumps(symbol))


async def background_task(interval: int):
    while True:
        fetch_trading_symbols()
        await asyncio.sleep(interval)  # Sleep for the specified interval (in seconds) before fetching again


@app.on_event("startup")
async def startup_event():
    # Start the background task when the application starts, fetching trading symbols every 24 hours
    asyncio.create_task(background_task(interval=86400))