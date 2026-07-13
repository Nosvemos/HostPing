import scrapy
from datetime import datetime
from hostping.items import VpsStockItem
from hostping.parsers.base import BaseParser

class SingleParser(BaseParser):
    def generate_requests(self, spider, provider_config):
        url = provider_config.get('url')
        bypass_cf = provider_config.get('bypass_cloudflare', False)
        
        yield scrapy.Request(
            url=url,
            callback=spider.parse,
            meta={
                'provider_config': provider_config,
                'bypass_cloudflare': bypass_cf
            },
            dont_filter=True
        )

    def parse(self, response, spider):
        provider = response.meta['provider_config']
        provider_name = provider.get('provider_name', 'Unknown')
        
        selectors = provider.get('single_selectors', {})
        timestamp = datetime.utcnow().isoformat()
        
        name = self.extract_value(response, selectors, 'name') or provider_name
        price = self.extract_value(response, selectors, 'price')
        stock_status = self.extract_value(response, selectors, 'stock_status')

        in_stock = self.determine_stock(stock_status, selectors)

        yield VpsStockItem(
            provider=provider_name,
            product_name=name,
            price=price or "N/A",
            stock_status=stock_status or "Unknown",
            in_stock=in_stock,
            url=response.url,
            timestamp=timestamp
        )
