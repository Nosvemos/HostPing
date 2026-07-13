import os
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

BOT_NAME = 'hostping'

SPIDER_MODULES = ['hostping.spiders']
NEWSPIDER_MODULE = 'hostping.spiders'

# Respectful scraping settings
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 2
DOWNLOAD_DELAY = 1.5

# Default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

# Downloader Middlewares configuration
DOWNLOADER_MIDDLEWARES = {
    'hostping.middlewares.CloudflareBypassMiddleware': 543,
}

# Item Pipelines configuration
ITEM_PIPELINES = {
    'hostping.pipelines.StockFilterPipeline': 300,
    'hostping.pipelines.NotificationPipeline': 400,
}

# Use select reactor for Windows compatibility
TWISTED_REACTOR = 'twisted.internet.selectreactor.SelectReactor'

# Set logs to be clean
LOG_LEVEL = 'INFO'
