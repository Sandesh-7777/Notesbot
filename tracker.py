# tracker.py - Simple web server for ad tracking
from flask import Flask, request, redirect
import json
import time

app = Flask(__name__)

# In-memory storage for tracking
click_data = {}

@app.route('/click')
def track_click():
    """Track ad clicks and redirect to actual ad"""
    ad_id = request.args.get('ad')
    user_id = request.args.get('user')
    token = request.args.get('token')
    
    # Record click time
    if token:
        click_data[token] = {
            'ad_id': ad_id,
            'user_id': user_id,
            'click_time': time.time(),
            'verified': False
        }
        print(f"Ad click recorded: {ad_id} by user {user_id}")
    
    # Redirect to actual ad URL
    ad_urls = {
        'ad1': 'https://example.com/python-course',
        'ad2': 'https://example.com/books',
        'ad3': 'https://example.com/web-dev'
    }
    
    redirect_url = ad_urls.get(ad_id, 'https://example.com')
    return redirect(redirect_url, code=302)

@app.route('/verify')
def verify_click():
    """Verify if ad was clicked (called by bot)"""
    token = request.args.get('token')
    
    if token in click_data:
        click_data[token]['verified'] = True
        return json.dumps({'status': 'success', 'clicked': True})
    
    return json.dumps({'status': 'success', 'clicked': False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)