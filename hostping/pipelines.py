import os
import json
import logging
import urllib.request
from scrapy.exceptions import DropItem
from twisted.internet.threads import deferToThread

logger = logging.getLogger(__name__)

class StockFilterPipeline:
    """
    Pipeline that filters out items whose stock status hasn't changed.
    Maintains state in a local file 'hostping_state.json'.
    """
    def __init__(self):
        self.state_file = 'hostping_state.json'
        self.state = {}

    def open_spider(self, spider):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except Exception as e:
                logger.error(f"Error loading state file: {str(e)}")
                self.state = {}

    def process_item(self, item, spider):
        # Generate a unique key for this provider + product combination
        key = f"{item['provider']}_{item['product_name']}".strip().replace(" ", "_").lower()
        current_status = item['in_stock']

        previous_status = self.state.get(key)

        if previous_status == current_status:
            # Stock status did not change, drop the item to avoid notification spam
            raise DropItem(f"No stock status change for {item['provider']} - {item['product_name']}.")

        # Status changed! Update local state and save
        self.state[key] = current_status
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write state file: {str(e)}")

        return item


class NotificationPipeline:
    """
    Pipeline that aggregates items successfully passed through the filters
    and sends a consolidated notification when the spider closes.
    """
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.changed_items = []

    def process_item(self, item, spider):
        self.changed_items.append(item)
        return item

    def close_spider(self, spider):
        if not self.changed_items:
            return
            
        in_stock_items = [item for item in self.changed_items if item['in_stock']]
        
        if not in_stock_items:
            # Changes happened, but they were all items going OUT OF STOCK
            discord_msg = "🚨 **Stock Status Changed** 🚨\n\nSome tracked products are now out of stock. Currently, there are no new items in stock. 🔴"
            telegram_msg = "🚨 <b>Stock Status Changed</b> 🚨\n\nSome tracked products are now out of stock. Currently, there are no new items in stock. 🔴"
            return deferToThread(self._dispatch_notifications, discord_msg, telegram_msg)
            
        # Group items by provider
        grouped = {}
        for item in in_stock_items:
            provider = item['provider']
            if provider not in grouped:
                grouped[provider] = []
            grouped[provider].append(item)
            
        # Build consolidated Discord message (Markdown)
        discord_lines = ["**🚨 NEW STOCK ALERT 🚨**\n"]
        for provider, items in grouped.items():
            discord_lines.append(f"**{provider}**")
            for item in items:
                discord_lines.append(f"🟢 {item['product_name']} - {item['price']} - [Buy Now](<{item['url']}>)")
                logger.info(f"STATUS CHANGE: {provider} - {item['product_name']} is now IN STOCK")
            discord_lines.append("") # Empty line between providers
            
        discord_msg = "\n".join(discord_lines)
        
        # Build consolidated Telegram message (HTML)
        telegram_lines = ["🚨 <b>NEW STOCK ALERT</b> 🚨\n"]
        for provider, items in grouped.items():
            telegram_lines.append(f"<b>{provider}</b>")
            for item in items:
                telegram_lines.append(f"🟢 {item['product_name']} - {item['price']} - <a href=\"{item['url']}\">Buy Now</a>")
            telegram_lines.append("")
            
        telegram_msg = "\n".join(telegram_lines)
        
        # Send notifications using deferToThread to not block reactor on shutdown (though shutdown blocking is less critical)
        return deferToThread(self._dispatch_notifications, discord_msg, telegram_msg)
        
    def _dispatch_notifications(self, discord_msg, telegram_msg):
        if self.discord_webhook:
            self._send_discord(discord_msg)
            
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(telegram_msg)

    def _send_discord(self, message):
        try:
            # Discord has a 2000 character limit per message.
            # If the grouped message is too large, we must chunk it, but for our scale, it should fit.
            if len(message) > 1900:
                message = message[:1900] + "\n... [Message Truncated]"
                
            data = json.dumps({"content": message}).encode('utf-8')
            req = urllib.request.Request(
                self.discord_webhook,
                data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'HostPing-Tracker'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 204 or response.status == 200:
                    logger.info("Discord notification sent successfully.")
                else:
                    logger.warning(f"Discord returned status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}")

    def _send_telegram(self, message):
        try:
            api_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }).encode('utf-8')

            req = urllib.request.Request(
                api_url,
                data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'HostPing-Tracker'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    logger.info("Telegram notification sent successfully.")
                else:
                    logger.warning(f"Telegram returned status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")

