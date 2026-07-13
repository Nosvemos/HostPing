import os
import json
import scrapy
from datetime import datetime
from hostping.items import VpsStockItem

class DynamicSpider(scrapy.Spider):
    name = "dynamic_spider"

    def start_requests(self):
        # Resolve config path relative to project structure (root config folder)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(project_root, 'config', 'providers.json')

        if not os.path.exists(config_path):
            self.logger.error(f"Configuration file not found at: {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                providers = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load or parse providers config: {str(e)}")
            return

        for provider in providers:
            if not provider.get('enabled', True):
                self.logger.info(f"Skipping disabled provider: {provider.get('provider_name')}")
                continue

            url = provider.get('url')
            if not url:
                self.logger.warning(f"Skipping config entry due to missing URL: {provider}")
                continue

            bypass_cf = provider.get('bypass_cloudflare', False)

            # Pass provider configuration via Scrapy request meta
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'provider_config': provider,
                    'bypass_cloudflare': bypass_cf
                },
                dont_filter=True
            )

    def parse(self, response):
        provider = response.meta['provider_config']
        provider_name = provider.get('provider_name', 'Unknown')
        mode = provider.get('scraping_mode', 'single')

        self.logger.info(f"Parsing page for: {provider_name} | URL: {response.url}")
        timestamp = datetime.utcnow().isoformat()

        if mode == 'list':
            selectors = provider.get('list_selectors', {})
            container_css = selectors.get('container_css')
            container_xpath = selectors.get('container_xpath')

            if container_css:
                containers = response.css(container_css)
            elif container_xpath:
                containers = response.xpath(container_xpath)
            else:
                self.logger.error(f"List mode selected but no container selector defined for: {provider_name}")
                return

            self.logger.info(f"Found {len(containers)} product containers for: {provider_name}")

            for container in containers:
                name = self._extract(container, selectors, 'name')
                price = self._extract(container, selectors, 'price')
                stock_status = self._extract(container, selectors, 'stock_status')

                if not name:
                    # Skip rows or grids that don't match the actual item structure (e.g. headers)
                    continue

                in_stock = self._determine_stock(stock_status, selectors)

                yield VpsStockItem(
                    provider=provider_name,
                    product_name=name,
                    price=price or "N/A",
                    stock_status=stock_status or "Unknown",
                    in_stock=in_stock,
                    url=response.url,
                    timestamp=timestamp
                )

        else:  # 'single' product mode
            selectors = provider.get('single_selectors', {})
            name = self._extract(response, selectors, 'name') or provider_name
            price = self._extract(response, selectors, 'price')
            stock_status = self._extract(response, selectors, 'stock_status')

            in_stock = self._determine_stock(stock_status, selectors)

            yield VpsStockItem(
                provider=provider_name,
                product_name=name,
                price=price or "N/A",
                stock_status=stock_status or "Unknown",
                in_stock=in_stock,
                url=response.url,
                timestamp=timestamp
            )

    def _extract(self, selector, selectors_dict, field_name):
        """
        Extracts value from a selector using either CSS or XPath patterns.
        Falls back to extracting recursive text if no explicit Scrapy pseudoclasses are used.
        """
        css_key = f"{field_name}_css"
        xpath_key = f"{field_name}_xpath"

        css_selector = selectors_dict.get(css_key)
        xpath_selector = selectors_dict.get(xpath_key)

        val = None
        if css_selector:
            # If user explicitly asks for ::text or ::attr, use it. Otherwise, extract whole inner text.
            if "::text" in css_selector or "::attr" in css_selector:
                val = selector.css(css_selector).get()
            else:
                element = selector.css(css_selector)
                if element:
                    val = element.xpath("string(.)").get()
        elif xpath_selector:
            val = selector.xpath(xpath_selector).get()

        return val.strip() if val else ""

    def _determine_stock(self, stock_status, selectors_dict):
        """
        Determines whether the product is in stock based on parsed text
        and configuration indicators, falling back to a list of negative keywords.
        """
        if not stock_status:
            # If there is no stock indicator, assume in stock by default
            return True

        status_lower = stock_status.lower()

        # Check explicit positive indicator
        in_stock_indicator = selectors_dict.get('in_stock_indicator')
        if in_stock_indicator:
            return in_stock_indicator.lower() in status_lower

        # Check explicit negative indicator
        out_of_stock_indicator = selectors_dict.get('out_of_stock_indicator')
        if out_of_stock_indicator:
            return out_of_stock_indicator.lower() not in status_lower

        # Common negative keywords (English & Turkish)
        out_of_stock_keywords = [
            "out of stock", "sold out", "unavailable", "tükendi", 
            "stokta yok", "depleted", "no stock", "exhausted", 
            "0 left", "stock: 0", "yok"
        ]
        for keyword in out_of_stock_keywords:
            if keyword in status_lower:
                return False

        return True
