from flask import Flask, jsonify, send_from_directory, request
import os
import requests

app = Flask(__name__, static_folder='static')

FLASHALPHA_KEY = 'G5DwBnT1ZbByenm7jLCWzpFe3ngHOOPsHmI4mjjw'

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/prices')
def prices():
    """Proxy Yahoo Finance quotes for SPY, QQQ, VIX"""
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
                'price': price,
                'prev':  prev,
                'change': price - prev,
                'pct':   ((price - prev) / prev) * 100
            }
        except Exception as e:
            results[ticker.replace('%5E', '^')] = {'error': str(e)}
    return jsonify(results)

@app.route('/api/gex/<ticker>')
def gex(ticker):
    """Proxy FlashAlpha GEX endpoint - tries summary first, falls back to gex endpoint"""
    try:
        # Try the stock summary endpoint which includes key levels
        url = f'https://lab.flashalpha.com/v1/stock/{ticker.lower()}/summary'
        r = requests.get(url, timeout=10, headers={'X-Api-Key': FLASHALPHA_KEY})
        if r.status_code == 200:
            data = r.json()
            # Extract key levels from summary
            exposure = data.get('exposure', {})
            key_levels = exposure.get('key_levels', {})
            result = {
                'gamma_flip': key_levels.get('gamma_flip') or exposure.get('gamma_flip'),
                'call_wall':  key_levels.get('call_wall')  or exposure.get('call_wall'),
                'put_wall':   key_levels.get('put_wall')   or exposure.get('put_wall'),
                'net_gex':    exposure.get('net_gex'),
                'regime':     exposure.get('regime'),
                '_raw':       data  # for debugging
            }
            return jsonify(result), 200

        # Fallback: direct GEX endpoint
        url2 = f'https://lab.flashalpha.com/v1/exposure/gex/{ticker.upper()}'
        r2 = requests.get(url2, timeout=10, headers={'X-Api-Key': FLASHALPHA_KEY})
        data2 = r2.json()
        # Derive call_wall and put_wall from strikes if not top-level
        if 'call_wall' not in data2 and 'strikes' in data2:
            strikes = data2['strikes']
            if strikes:
                call_wall = max(strikes, key=lambda s: s.get('call_gex', 0) or 0).get('strike')
                put_wall  = min(strikes, key=lambda s: s.get('put_gex', 0) or 0).get('strike')
                data2['call_wall'] = call_wall
                data2['put_wall']  = put_wall
        return jsonify(data2), r2.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
