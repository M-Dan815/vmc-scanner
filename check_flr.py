# check_flr.py — run this once then delete it
import requests

response = requests.get("https://api.binance.com/api/v3/exchangeInfo")
data = response.json()

# Search for anything FLR related
matches = [
    s['symbol'] for s in data['symbols']
    if 'FLR' in s['symbol'] and s['quoteAsset'] == 'USDT'
]

print("FLR matches on Binance:")
for m in matches:
    print(f"  {m}")