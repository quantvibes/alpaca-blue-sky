import alpaca_trade_api as tradeapi
from atproto import Client
import time
from datetime import datetime, timedelta, timezone
import os

# Alpaca API Keys
ALPACA_API_KEY = "use-your-api-key"
ALPACA_SECRET_KEY = "use-your-api-secret"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # Use live URL for real trading

# Bluesky Credentials
BLUESKY_USERNAME = "your handle"
BLUESKY_PASSWORD = "your account password"

# File to store posted trade IDs
POSTED_TRADES_FILE = "posted_trades.txt"

# Initialize Alpaca API
alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version="v2")

# Initialize Bluesky Client
bluesky = Client()
bluesky.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

def load_posted_trades():
    """Load posted trade IDs from a file into a set."""
    if os.path.exists(POSTED_TRADES_FILE):
        with open(POSTED_TRADES_FILE, "r") as file:
            return set(line.strip() for line in file.readlines())  # Read and store trade IDs
    return set()

def save_trade_id(trade_id):
    """Save a new trade ID to the file to prevent duplicate postings."""
    with open(POSTED_TRADES_FILE, "a") as file:
        file.write(f"{trade_id}\n")

def post_trade_update(action, symbol, price, trade_id):
    """Post trade updates to Bluesky and track posted trades."""
    message = f"{action} {symbol} at ${price:.2f}"  # Removed qty
    bluesky.post(text=message)
    save_trade_id(trade_id)  # Save trade ID to file
    print(f"Posted to Bluesky: {message}")

def check_trades():
    """Monitor executed trades and post updates only for new trades within 5 minutes."""
    posted_trades = load_posted_trades()  # Load posted trades from file

    while True:
        try:
            orders = alpaca.list_orders(status='closed', limit=5)  # Fetch recent orders
            now = datetime.now(timezone.utc)  # Get the current time in UTC

            for order in orders:
                if order.id in posted_trades:
                    continue  # Skip already posted trades

                if order.filled_at:
                    # Convert filled_at to a datetime object with timezone awareness
                    if isinstance(order.filled_at, datetime):
                        filled_time = order.filled_at.replace(tzinfo=timezone.utc)
                    else:
                        filled_time = datetime.strptime(str(order.filled_at), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

                    # Check if the trade is older than 5 minutes
                    if (now - filled_time).total_seconds() > 300:  # 300 seconds = 5 minutes
                        print(f"Skipping trade (older than 5 minutes): {order.symbol} at {filled_time}")
                        continue

                    # Post the trade update
                    post_trade_update(
                        "Bought" if order.side == "buy" else "Sold",
                        order.symbol,
                        float(order.filled_avg_price),
                        order.id
                    )
                    posted_trades.add(order.id)  # Add to in-memory set too

                else:
                    print(f"Skipping trade with no filled timestamp: {order.symbol}")

        except Exception as e:
            print(f"Error checking trades: {e}")

        time.sleep(30)  # Poll every 30 seconds

if __name__ == "__main__":
    check_trades()