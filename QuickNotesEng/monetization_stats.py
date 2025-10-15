import json
from datetime import datetime, timedelta

def show_monetization_stats():
    """Show monetization statistics"""
    # Ad stats
    try:
        with open('ad_stats.json', 'r') as f:
            ad_stats = json.load(f)
    except:
        ad_stats = {}
    
    # Donation stats
    try:
        with open('donations.json', 'r') as f:
            donations = json.load(f)
    except:
        donations = []
    
    print("💰 Monetization Statistics")
    print("=" * 30)
    print(f"📢 Total Ad Impressions: {ad_stats.get('total_impressions', 0)}")
    print(f"👥 Unique Users Seen Ads: {len(ad_stats.get('user_ad_count', {}))}")
    print(f"💝 Total Donations: {len(donations)}")
    
    # Calculate revenue (example)
    total_revenue = sum(d.get('amount', 0) for d in donations)
    print(f"💵 Estimated Revenue: ₹{total_revenue}")

if __name__ == "__main__":
    show_monetization_stats()