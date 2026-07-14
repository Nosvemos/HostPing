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
    'hostping.pipelines.HostPingPipeline': 300,
}

# Use select reactor for Windows compatibility
TWISTED_REACTOR = 'twisted.internet.selectreactor.SelectReactor'

# Clean Logging configuration
LOG_LEVEL = 'WARNING'

import logging
import sys

# Configure our custom application logger (hostping)
app_logger = logging.getLogger('hostping')
app_logger.setLevel(logging.INFO)
app_logger.propagate = False # Prevent bubbling to Scrapy's root logger

# Remove any default handlers to avoid duplication
for h in list(app_logger.handlers):
    app_logger.removeHandler(h)

# Add clean stream handler for standard stdout
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log_handler.setFormatter(log_formatter)
app_logger.addHandler(log_handler)

# Silence scrapy's item dropper warnings specifically
logging.getLogger('scrapy.core.scraper').setLevel(logging.ERROR)

# Extensions configuration
EXTENSIONS = {
    'hostping.extensions.SilenceScrapyNoiseExtension': 0,
}

# Retry Settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
