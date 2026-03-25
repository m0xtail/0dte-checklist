from flask import Flask, jsonify, send_from_directory
import os
import requests
from datetime import date, timedelta
from collections import defaultdict

app = Flask(__name__, static_folder='static')

MASSIVE_KEY = 'Bo6ksFmnOppTG4wz1uBpzykLNzJZ3kja'

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/prices')
def prices():
    tickers = ['SPY', 'QQQ', '%5EVIX']
    results = {}
    for ticker in tickers:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d'
            r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data = r.json()
            q = data['chart']['result'][0]
            price = q['meta']['regularMarketPrice']
            prev  = q['meta']['chartPreviousClose']
            results[ticker.replace('%5E', '^')] = {
                'price':  price,
                'prev':   prev,
                'change': price - prev,
                'pct':    ((price - prev) / prev) * 100
            }
        except Exception as e:
            results[ticker.replace('%5E', '^')] = {'error': str(e)}
    return jsonify(results)

@app.route('/api/gex/<ticker>')
def gex(ticker):
    ticker = ticker.upper()
    today  = date.today().isoformat()

    # Get underlying price
    underlying = None
    try:
        pr = requests.get(
            f'https://api.massive.com/v2/last/trade/{ticker}',
            params={'apiKey': MASSIVE_KEY}, timeout=10)
        pd = pr.json()
        underlying = pd.get('results', {}).get('p') or pd.get('last', {}).get('price')
    except:
        pass

    # Fetch 0DTE options chain
    contracts = []
    for exp in [today, (date.today() + timedelta(days=1)).isoformat()]:
        try:
            cr = requests.get(
                f'https://api.massive.com/v3/snapshot/options/{ticker}',
                params={'expiration_date': exp, 'limit': 250, 'apiKey': MASSIVE_KEY},
                timeout=15)
            contracts = cr.json().get('results', [])
            if contracts:
                break
        except:
            pass

    if not contracts:
        return jsonify({'error': 'No contracts found'}), 404

    # Compute GEX per strike
    strike_gex = defaultdict(float)
    price_ref  = underlying or 500

    for c in contracts:
        details = c.get('details', {})
        greeks  = c.get('greeks', {})
        strike  = details.get('strike_price')
        gamma   = greeks.get('gamma')
        oi      = c.get('open_interest') or c.get('day', {}).get('open_interest')
        ctype   = details.get('contract_type', '').lower()
        if not all([strike, gamma is not None, oi]):
            continue
        gex_val = gamma * oi * 100 * (price_ref ** 2) * 0.01
        if ctype == 'call':
            strike_gex[strike] += gex_val
        elif ctype == 'put':
            strike_gex[strike] -= gex_val

    if not strike_gex:
        return jsonify({'error': 'No valid greeks in chain'}), 500

    sorted_strikes = sorted(strike_gex.keys())

    # Call wall and put wall
    call_wall = max(sorted_strikes, key=lambda s: strike_gex[s])
    put_wall  = min(sorted_strikes, key=lambda s: strike_gex[s])

    # Gamma flip: cumulative GEX zero crossing
    cumulative = 0
    gamma_flip = None
    best_dist  = float('inf')
    for s in sorted_strikes:
        cumulative += strike_gex[s]
        if abs(cumulative) < best_dist:
            best_dist  = abs(cumulative)
            gamma_flip = s

    net_gex = sum(strike_gex.values())

    return jsonify({
        'ticker':     ticker,
        'gamma_flip': gamma_flip,
        'call_wall':  call_wall,
        'put_wall':   put_wall,
        'net_gex':    net_gex,
        'regime':     'positive' if net_gex > 0 else 'negative',
        'underlying': underlying,
        'contracts':  len(contracts)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
