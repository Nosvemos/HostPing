# HostPing - VPS/VDS Stock Tracker

HostPing is a highly modular, dynamic, and professional stock tracker built on Python and Scrapy. It monitors the availability of VPS/VDS resources from various hosting providers and updates a Discord dashboard using premium, auto-updating embeds with real-time timestamps translated to the viewer's local timezone.

---

## 🚀 Key Features

*   **Premium Discord Embeds**: Real-time status dashboards with color-coded sidebars (Green for in-stock, Red for out-of-stock) for each provider.
*   **Auto-Updating Dashboards**: Edits existing messages using Discord's `PATCH` API, keeping the notification channel clean and avoiding rate limits (only updates Discord when an actual stock status change is detected).
*   **Automatic Local Timezone Translation**: Uses Discord's native epoch timestamp formatting (`<t:TIMESTAMP:f> (<t:TIMESTAMP:R>)`), automatically translating "Last seen in stock" timestamps to the viewer's local device timezone and showing relative times (e.g., *5 minutes ago*) that count down in real-time in the Discord client.
*   **Modular Architecture**: Adding new VPS providers or changing CSS selectors only requires editing the `config/providers.json` file. No code modifications are necessary.
*   **Cloudflare Bypass Middleware**: Integrates `curl_cffi` within a Scrapy Downloader Middleware to spoof browser TLS/JA3/JA4 fingerprints, bypassing typical Cloudflare WAF protections without requiring headless browsers (like Selenium/Playwright) or proxies.
*   **Anti-Detection Delay Jitter**: Uses randomized delays (e.g., base of 5 minutes ±30–60 seconds) in the runner script to make request patterns look completely organic and prevent IP blocking.
*   **Docker Ready & State Persistent**: Ships with a ready-to-use Docker environment mapping a local `./data` directory to persist state and Discord message IDs, avoiding duplicate notifications or broken configurations across container restarts.

---

## 📂 Project Structure

```text
├── config/
│   └── providers.json       # Dynamic providers configurations (selectors, URLs, modes)
├── data/                    # Local persistent state (created at runtime, gitignored)
│   ├── hostping_state.json  # Internal stock state with last seen timestamps
│   └── discord_message_ids.json # Maps provider names to Discord message IDs
├── hostping/                # Scrapy project root
│   ├── spiders/
│   │   └── dynamic_spider.py # Configuration-driven scraping engine
│   ├── middlewares.py        # Cloudflare bypass and TLS spoofing middleware
│   ├── pipelines.py          # Price cleaning, item sorting, and Discord embed logic
│   └── settings.py           # Scrapy settings
├── Dockerfile               # Production multi-stage Docker build
├── docker-compose.yml       # Docker Compose setup with volumes and restart rules
├── entrypoint.sh            # Loop runner script with randomized anti-detection delay
├── requirements.txt         # Python dependencies
└── scrapy.cfg               # Scrapy config
```

---

## 🐳 Deployment (Docker & VPS)

For production deployment on an Ubuntu 22.04 LTS (or similar Linux) VPS:

### 1. Prerequisites
Ensure Docker and Git are installed on your system:
```bash
sudo apt update && sudo apt install -y git curl
# Install Docker (Official Docker Engine)
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

### 2. Clone the Repository
```bash
git clone https://github.com/Nosvemos/HostPing.git
cd HostPing
```

### 3. Configure Environments
Create a `.env` file in the root directory:
```bash
cp .env.example .env
nano .env
```
Populate the Discord webhook URL:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-id/your-webhook-token
```

### 4. Build and Run
Start the tracker in detached (background) mode:
```bash
sudo docker compose up -d --build
```

### 5. Monitor Logs
Verify that the tracker is successfully running and updating Discord:
```bash
sudo docker logs -f hostping_bot
```

---

## 🛠️ Local Development (Manual Run)

If you want to run the tracker locally on your development machine:

1.  **Create and activate a Virtual Environment**:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run a single crawl**:
    ```bash
    scrapy crawl dynamic_spider
    ```

---

## 📝 Customization

To add a new provider or update selectors, simply edit config/providers.json.

### Example Provider Configuration (CSS Scraper Mode):
```json
{
  "provider_name": "My Custom VPS",
  "url": "https://example.com/vps-plans",
  "bypass_cloudflare": true,
  "enabled": true,
  "scraping_mode": "list",
  "list_selectors": {
    "container_css": ".vps-card",
    "name_css": "h3::text",
    "price_css": ".price::text",
    "stock_status_css": ".order-btn::attr(class)",
    "out_of_stock_indicator": "disabled"
  }
}
```
Supported scraping modes (`scraping_mode`):
- `list`: Standard CSS selector parsing.
- `buyvm_js`: Specific parser for BuyVM JSON configurations.
- `ovh_engine_api`: Specific parser for OVH Datacenter API.
- `alphavps`: Specific configurator parse script.
