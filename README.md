# VPS/VDS Stock Tracker (HostPing)

A highly modular and dynamic stock tracker built on Python and Scrapy. It monitors availability of VPS/VDS resources from various hosting providers and sends notifications when changes occur.

## Key Features

- **Dynamic Configuration**: Adding new providers or updating target URLs/selectors only requires editing `config/providers.json`. No code changes are necessary.
- **Proxy-free Cloudflare Bypass**: Integrates `curl_cffi` within a Scrapy Downloader Middleware to spoof browser TLS/JA3/JA4 fingerprints, bypassing typical Cloudflare bot protection screens without needing a heavy headless browser or proxies.
- **Duplicate Prevention**: Tracks stock state change history to prevent spamming notifications.
- **Multi-channel Notifications**: Supports console logs, Discord webhooks, and Telegram bots.

## Directory Structure

```text
├── config/
│   └── providers.json       # Dynamic providers configurations (selectors, urls, bypass specs)
├── docs/                     # AI Context & project internals (gitignored)
├── hostping/                 # Scrapy project root
│   ├── spiders/
│   │   └── dynamic_spider.py # Main spider executing configuration-based scraping
│   ├── items.py              # Scrapy item model for stock updates
│   ├── middlewares.py        # Cloudflare bypass and custom handlers
│   ├── pipelines.py          # State filters and notifications (Telegram/Discord)
│   └── settings.py           # Scrapy config settings
├── .gitignore
├── README.md
├── requirements.txt
└── scrapy.cfg
```

## Setup & Installation

1. **Clone the Repository & Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   # Notifications Config
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_CHAT_ID=-100123456789
   ```

3. **Modify Targets**:
   Update `config/providers.json` to add or modify tracking targets. Refer to `docs/ai_context.md` for JSON structure specifications.

## Running the Tracker

To run the tracker manually:
```bash
scrapy crawl dynamic_spider
```

To schedule execution every 15 or 30 minutes, set up a Cron Job (Linux) or Windows Task Scheduler to run the command above.
