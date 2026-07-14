import scrapy
from datetime import datetime
from bs4 import BeautifulSoup
from hostping.items import VpsStockItem
from hostping.parsers.base import BaseParser

class AlphavpsParser(BaseParser):
    def generate_requests(self, spider, provider_config):
        plans = provider_config.get('plans', [])
        bypass_cf = provider_config.get('bypass_cloudflare', True)
        
        for plan in plans:
            url = plan.get('url')
            name = plan.get('name')
            price = plan.get('price', 'N/A')
            
            yield scrapy.Request(
                url=url,
                callback=spider.parse,
                meta={
                    'provider_config': provider_config,
                    'bypass_cloudflare': bypass_cf,
                    'plan_name': name,
                    'plan_price': price,
                    'target_location': provider_config.get('target_location', 'Germany')
                },
                dont_filter=True
            )

    def parse(self, response, spider):
        provider = response.meta['provider_config']
        provider_name = provider.get('provider_name', 'Unknown')
        plan_name = response.meta['plan_name']
        plan_price = response.meta['plan_price']
        target_location = response.meta['target_location']
        timestamp = datetime.utcnow().isoformat()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        in_stock = False
        stock_status = "Unavailable in region"
        
        # Look for a tag containing the target location (e.g., 'Germany')
        for tag in soup.find_all(string=lambda text: text and target_location in text):
            parent = tag.parent
            if parent and (parent.name == 'span' or parent.name == 'label'):
                text = parent.text.strip()
                if 'OOS' in text.upper() or 'OUT OF STOCK' in text.upper():
                    stock_status = "Out of Stock"
                    in_stock = False
                else:
                    stock_status = "In Stock"
                    in_stock = True
                break
                
        yield VpsStockItem(
            provider=provider_name,
            product_name=plan_name,
            price=plan_price,
            stock_status=stock_status,
            in_stock=in_stock,
            url=response.url,
            timestamp=timestamp
        )
