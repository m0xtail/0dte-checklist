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
    """Proxy FlashAlpha GEX endpoint"""
    from datetime import date
    today = date.today().isoformat()
    try:
        url = f'https://lab.flashalpha.com/v1/exposure/gex/{ticker.upper()}?expiration={today}'
        r = requests.get(url, timeout=10, headers={'X-Api-Key': FLASHALPHA_KEY})
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
