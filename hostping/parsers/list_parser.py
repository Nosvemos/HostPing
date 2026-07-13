import scrapy
from datetime import datetime
from hostping.items import VpsStockItem
from hostping.parsers.base import BaseParser

class ListParser(BaseParser):
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
        
        selectors = provider.get('list_selectors', {})
        container_css = selectors.get('container_css')
        container_xpath = selectors.get('container_xpath')
        timestamp = datetime.utcnow().isoformat()

        if container_css:
            containers = response.css(container_css)
        elif container_xpath:
            containers = response.xpath(container_xpath)
        else:
            spider.logger.error(f"List mode selected but no container selector defined for: {provider_name}")
            return

        spider.logger.info(f"Found {len(containers)} product containers for: {provider_name}")

        for container in containers:
            name = self.extract_value(container, selectors, 'name')
            price = self.extract_value(container, selectors, 'price')
            stock_status = self.extract_value(container, selectors, 'stock_status')

            if not name:
                # Skip rows or grids that don't match the actual item structure (e.g. headers)
                continue

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
