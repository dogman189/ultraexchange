import json
import ssl
import urllib.parse
import urllib.request
import certifi
import os
import time
import statistics
from collections import deque
from dotenv import load_dotenv


load_dotenv()
API_KEY = os.getenv("CMC_API_KEY")

tick = int(input("Enter time between hits (Max 330/day): "))
SYMBOL_TO_TRADE = input("Enter the symbol you want to trade: ")
WINDOW_SIZE = int(input("Enter the amount of background data for the algorithm: "))           
TRADE_AMOUNT_USD = float(input("Enter the amount you want to use per trade: ")) 


price_history = deque(maxlen=WINDOW_SIZE)

portfolio = {
    "USD": float(input("Enter portfolio amount: ")),  y
    "holdings": {}
}

def fetch_cmc_price(symbol):
   
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = urllib.parse.urlencode({"symbol": symbol, "convert": "USD"})
    
    request = urllib.request.Request(
        f"{url}?{params}",
        headers={"Accept": "application/json", "X-CMC_PRO_API_KEY": API_KEY},
    )
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urllib.request.urlopen(request, context=context) as response:
            data = json.load(response)
            return data["data"][symbol]["quote"]["USD"]["price"]
    except Exception as e:
        print(f"API Error: {e}")
        return None

def run_math_engine(current_price):
    
    price_history.append(current_price)
    
    if len(price_history) < WINDOW_SIZE:
        print(f"⌛ Building history... ({len(price_history)}/{WINDOW_SIZE})")
        return "WAITING"

    
    sma = statistics.mean(price_history)
    
    
    stdev = statistics.stdev(price_history)
    
    
    upper_band = sma + (stdev * 2)
    lower_band = sma - (stdev * 2)
    
    print(f"Stats -> SMA: ${sma:,.2f} | Upper: ${upper_band:,.2f} | Lower: ${lower_band:,.2f}")

   
    if current_price <= lower_band:
        return "BUY"
    elif current_price >= upper_band:
        return "SELL"
    else:
        return "HOLD"

def execute_trade(action, symbol, price):
    
    global portfolio
    
    if action == "BUY":
        if portfolio["USD"] >= TRADE_AMOUNT_USD:
            coins_bought = TRADE_AMOUNT_USD / price
            portfolio["USD"] -= TRADE_AMOUNT_USD
            
            
            portfolio["holdings"][symbol] = portfolio["holdings"].get(symbol, 0) + coins_bought
            print(f"[TRADE] 🟢 BUY: Acquired {coins_bought:.6f} {symbol} at ${price:,.2f}")
        else:
            print(f"[TRADE] ❌ Ignored Buy Signal: Insufficient USD.")

    elif action == "SELL":
        
        if symbol in portfolio["holdings"] and portfolio["holdings"][symbol] > 0:
            coins_to_sell = portfolio["holdings"][symbol]
            usd_gained = coins_to_sell * price
            
            
            portfolio["USD"] += usd_gained
            portfolio["holdings"][symbol] = 0
            print(f"[TRADE] 🔴 SELL: Liquidated {coins_to_sell:.6f} {symbol} for ${usd_gained:,.2f}")
        else:
            print(f"[TRADE] ❌ Ignored Sell Signal: No {symbol} in portfolio to sell.")


if __name__ == "__main__":
    print("="*60)
    print(f"INITIATING QUANTITATIVE BOT FOR {SYMBOL_TO_TRADE}")
    print("Strategy: Bollinger Bands (2 Standard Deviations)")
    print("="*60)
    
    if not API_KEY:
        print("CRITICAL ERROR: No API Key found.")
        exit()

    while True:
        try:
            print(f"\n--- Tick: {time.strftime('%H:%M:%S')} ---")
            
           
            price = fetch_cmc_price(SYMBOL_TO_TRADE)
            
            if price:
                print(f"Current Price: ${price:,.2f}")
                
                
                signal = run_math_engine(price)
                print(f"Algorithm Signal: {signal}")
                
                
                if signal in ["BUY", "SELL"]:
                    execute_trade(signal, SYMBOL_TO_TRADE, price)
                
                
                print(f"Wallet: ${portfolio['USD']:,.2f} USD | {portfolio['holdings'].get(SYMBOL_TO_TRADE, 0):.6f} {SYMBOL_TO_TRADE}")
            
            
            time.sleep(tick) 
            
        except KeyboardInterrupt:
            print("\nBot stopped by user. Final Portfolio State:")
            print(f"Total USD: ${portfolio['USD']:,.2f}")
            print(f"Total Crypto: {portfolio['holdings']}")
            break
        except Exception as e:
            print(f"System Error: {e}")
            time.sleep(60) 