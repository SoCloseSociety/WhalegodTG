# Configuration file for whale tracking bot

import os

# API keys and other sensitive information should be stored in environment variables or a secure vault
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'localhost')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))

# Other configuration settings
DEFAULT_SCAN_LIMIT = 100
MAX_TX_HISTORY = 200

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')