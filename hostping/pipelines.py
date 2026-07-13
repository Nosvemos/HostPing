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
    Pipeline that sends notifications to configured channels (Telegram, Discord, Console)
    when an item successfully passes through the filters.
    """
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def process_item(self, item, spider):
        # We run the notification dispatch in a background thread to prevent blocking Scrapy's main loop
        return deferToThread(self._send_notifications, item)

    def _send_notifications(self, item):
        provider = item['provider']
        product = item['product_name']
        price = item['price']
        status_text = item['stock_status']
        in_stock = item['in_stock']
        url = item['url']

        emoji = "🟢" if in_stock else "🔴"
        title = f"🚨 VPS/VDS Stock Alert: {provider} 🚨"
        message = (
            f"**{title}**\n\n"
            f"**Product:** {product}\n"
            f"**Price:** {price}\n"
            f"**Status:** {emoji} {status_text}\n"
            f"**Link:** {url}"
        )

        logger.info(f"NOTIFICATION STATUS CHANGE: {provider} - {product} is now {'IN STOCK' if in_stock else 'OUT OF STOCK'}")

        # Send to Discord
        if self.discord_webhook:
            self._send_discord(message)

        # Send to Telegram
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message)

    def _send_discord(self, message):
        try:
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
            # Strip markdown double-asterisks as Telegram HTML/Markdown requires different formatting or parse_mode
            # We will use HTML formatting for simple bolding
            formatted_msg = message.replace("**", "<b>", 1).replace("**", "</b>", 1)  # replace title asterisks
            formatted_msg = formatted_msg.replace("**Product:**", "<b>Product:</b>")
            formatted_msg = formatted_msg.replace("**Price:**", "<b>Price:</b>")
            formatted_msg = formatted_msg.replace("**Status:**", "<b>Status:</b>")
            formatted_msg = formatted_msg.replace("**Link:**", "<b>Link:</b>")

            api_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": formatted_msg,
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
