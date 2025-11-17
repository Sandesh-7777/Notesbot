# config.py - Configuration file for your bot

# Bot Token from BotFather
BOT_TOKEN = "8148559791:AAFQfWdWXEwvyCyLc8t_vbqkIFxTun-wUVc"
# # GitHub Storage Configuration
# GITHUB_TOKEN = "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"
# GITHUB_REPO = "Sandesh-7777/Notesbot"  # Format: "username/repository-name"
# GitHub Storage Configuration 
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '8148559791:AAFQfWdWXEwvyCyLc8t_vbqkIFxTun-wUVc') 
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Sandesh-7777/Notesbot') # Format: "username/repository-name"

# Your Telegram User ID (to get this, send /start to @userinfobot on Telegram)
ADMIN_IDS = [6884754821]  # Replace with your actual Telegram ID

# Team Member User IDs (upload access only)
TEAM_MEMBER_IDS = [6496152250, 555666777]  # Add your team members' Telegram IDs

# File paths
DATA_FILE = "study_materials.json"
PDF_FOLDER = "pdfs/"

# Bot settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.txt']

# Search settings
MAX_SEARCH_RESULTS = 10

ADS = [
    {
        "text": "Check this offer!",   # What message you want to show to the user
        "url": "https://www.effectivegatecpm.com/yv9u1th9?key=4a2f106694f2523d86540aa156311604",  # Direct ad link
        "ad_id": "egcpm_ad1",          # Unique ID for tracking internally
        "tracking_url": "https://www.effectivegatecpm.com/yv9u1th9?key=4a2f106694f2523d86540aa156311604&user={user_id}"  # optional tracking pattern
    }
]

# Donation Settings
DONATION_OPTIONS = {
    "upi": "your-upi@id",
    "paypal": "https://paypal.me/yourname",
    "bitcoin": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "qr_code": "upi_qr_code.png"
}

# Smart Ad Settings
AD_VERIFICATION_ENABLED = True
FREE_DOWNLOADS_ALLOWED = 2  # 2 free downloads every 10 hours
WAIT_TIME_SECONDS = 20
TOKEN_DURATION_HOURS = 10  # 10 hours token validity
FREE_DOWNLOAD_RESET_HOURS = 10  # Free downloads reset every 10 hours
