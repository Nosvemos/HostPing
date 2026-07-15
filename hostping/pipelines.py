import os
import re
import json
import time
import logging
import urllib.request
from datetime import datetime
from twisted.internet.threads import deferToThread

logger = logging.getLogger(__name__)

def clean_price(price_str):
    if not price_str:
        return "unknown"
    # Remove anything in parentheses (like ($24/yr))
    price = re.sub(r'\(.*?\)', '', price_str).strip()
    # Remove USD text
    price = price.replace("USD", "").strip()
    # Move Euro symbol to front if at the end
    if price.endswith("€"):
        price = "€" + price[:-1].strip()
    # Ensure it ends with /mo
    if not price.endswith("/mo"):
        price = f"{price}/mo"
    # Clean up double slashes or extra spaces
    price = price.replace(" /mo", "/mo").replace("//mo", "/mo")
    return price

def extract_numeric_price(price_str):
    if not price_str:
        return 0.0
    # Extract only digits and decimal dot (e.g. €23.99/mo -> 23.99)
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

class HostPingPipeline:
    """
    Consolidated pipeline that collects all scraped items, compares them to the local
    state to detect changes, maintains the last seen in-stock timestamp for each item,
    and updates Discord accordingly with clean, provider-specific messages.
    """
    def __init__(self):
        self.state_file = 'data/hostping_state.json'
        self.msg_ids_file = 'data/discord_message_ids.json'
        
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        
        self.state = {}
        self.message_ids = {}
        self.scraped_items = []

    def open_spider(self, spider=None):
        os.makedirs('data', exist_ok=True)
        now_ts = int(time.time())
        
        # Load state
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    raw_state = json.load(f)
                # Migrate old flat bool state and string timestamps to Unix epoch int
                for k, v in raw_state.items():
                    if isinstance(v, bool):
                        self.state[k] = {
                            "in_stock": v,
                            "last_in_stock": now_ts if v else None
                        }
                    else:
                        last_in_stock = v.get('last_in_stock')
                        if isinstance(last_in_stock, str):
                            try:
                                dt = datetime.strptime(last_in_stock, "%Y-%m-%d %H:%M:%S")
                                last_in_stock = int(dt.timestamp())
                            except Exception:
                                last_in_stock = None
                        self.state[k] = {
                            "in_stock": v.get('in_stock', False),
                            "last_in_stock": last_in_stock
                        }
            except Exception as e:
                logger.error(f"Error loading/migrating state file: {str(e)}")
                self.state = {}
                
        # Load Discord message IDs
        if os.path.exists(self.msg_ids_file):
            try:
                with open(self.msg_ids_file, 'r', encoding='utf-8') as f:
                    self.message_ids = json.load(f)
            except Exception as e:
                logger.error(f"Error loading message IDs file: {str(e)}")
                self.message_ids = {}

    def process_item(self, item, spider=None):
        item['price'] = clean_price(item.get('price', ''))
        self.scraped_items.append(item)
        return item

    async def close_spider(self, spider=None):
        if not self.scraped_items:
            return

        now_ts = int(time.time())
        
        # Group scraped items by provider
        grouped = {}
        for item in self.scraped_items:
            provider = item['provider']
            if provider not in grouped:
                grouped[provider] = []
            grouped[provider].append(item)

        state_changed = False
        
        # Sort providers by predefined order to ensure logical Discord layout
        provider_order = [
            "Datalix Ryzen Gen4",
            "HostBrr 9950X VDS DE 1Gbps",
            "HostBrr 9950X VDS DE 10Gbps",
            "AlphaVPS Ryzen Germany",
            "BuyVM Slices Luxembourg"
        ]
        sorted_providers = sorted(grouped.keys(), key=lambda p: provider_order.index(p) if p in provider_order else 999)

        # Process each provider
        for provider in sorted_providers:
            items = grouped[provider]
            provider_changed = False
            
            # Check if any product in this provider has changed
            for item in items:
                key = f"{provider}_{item['product_name']}".strip().replace(" ", "_").lower()
                current_status = item['in_stock']
                
                prev_state = self.state.get(key, {})
                prev_status = prev_state.get('in_stock', None)
                prev_last_in_stock = prev_state.get('last_in_stock', None)
                
                # Determine new last_in_stock value
                if current_status:
                    new_last_in_stock = now_ts
                else:
                    new_last_in_stock = prev_last_in_stock
                
                # Check for change
                if prev_status != current_status:
                    provider_changed = True
                    state_changed = True
                    
                    if current_status:
                        logger.info(f"STATUS CHANGE: {provider} - {item['product_name']} is now IN STOCK")
                    else:
                        logger.info(f"STATUS CHANGE: {provider} - {item['product_name']} is now OUT OF STOCK")

                # Always update in-memory state
                self.state[key] = {
                    "in_stock": current_status,
                    "last_in_stock": new_last_in_stock
                }

            # If this provider has changes (or we don't have a message ID for it), update/send Discord
            if provider_changed or provider not in self.message_ids:
                if self.discord_webhook:
                    discord_msg = self._build_discord_message(provider, items)
                    await deferToThread(self._dispatch_discord, provider, discord_msg)

        # Always save state to persist updated last_in_stock timestamps
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write state file: {str(e)}")

    def _build_discord_message(self, provider, items):
        description_lines = []
        any_in_stock = False
        sorted_items = sorted(items, key=lambda x: extract_numeric_price(x.get('price', '')))
        for item in sorted_items:
            key = f"{provider}_{item['product_name']}".strip().replace(" ", "_").lower()
            item_state = self.state.get(key, {})
            in_stock = item_state.get('in_stock', False)
            last_in_stock = item_state.get('last_in_stock')
            
            if in_stock:
                any_in_stock = True
                line = f"🟢 **{item['product_name']}** - {item['price']} - [Buy Now](<{item['url']}>)"
            else:
                if last_in_stock:
                    last_in_stock_str = f"<t:{last_in_stock}:f> (<t:{last_in_stock}:R>)"
                else:
                    last_in_stock_str = "unknown"
                line = f"🔴 {item['product_name']} - {item['price']} - Last in stock: {last_in_stock_str}"
            description_lines.append(line)
            
        color = 3066993 if any_in_stock else 15158332 # 0x2ECC71 (Green) or 0xE74C3C (Red)
        
        embed = {
            "title": provider,
            "description": "\n".join(description_lines),
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return {"embeds": [embed]}

    def _dispatch_discord(self, provider, payload):
        try:
            data = json.dumps(payload).encode('utf-8')
            message_id = self.message_ids.get(provider)
            
            if message_id:
                # Try to PATCH
                patch_url = f"{self.discord_webhook}/messages/{message_id}"
                req = urllib.request.Request(
                    patch_url,
                    data=data,
                    headers={'Content-Type': 'application/json', 'User-Agent': 'HostPing-Tracker'},
                    method='PATCH'
                )
                try:
                    with urllib.request.urlopen(req) as response:
                        if response.status in (200, 204):
                            logger.info(f"Discord message for '{provider}' updated successfully.")
                            return
                except Exception as e:
                    logger.warning(f"Failed to patch Discord message for '{provider}', fallback to new post: {str(e)}")

            # Fallback to POST
            post_url = f"{self.discord_webhook}?wait=true"
            req = urllib.request.Request(
                post_url,
                data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'HostPing-Tracker'},
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                if response.status in (200, 204):
                    logger.info(f"Discord message for '{provider}' sent successfully.")
                    try:
                        resp_data = json.loads(response.read().decode('utf-8'))
                        new_msg_id = resp_data.get('id')
                        if new_msg_id:
                            self.message_ids[provider] = new_msg_id
                            with open(self.msg_ids_file, 'w', encoding='utf-8') as f:
                                json.dump(self.message_ids, f, indent=4)
                    except Exception as e:
                        logger.warning(f"Failed to save Discord message ID for '{provider}': {str(e)}")
                else:
                    logger.warning(f"Discord returned status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification for '{provider}': {str(e)}")
