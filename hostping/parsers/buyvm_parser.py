import json
import scrapy
from datetime import datetime
from hostping.items import VpsStockItem
from hostping.parsers.base import BaseParser

class BuyvmParser(BaseParser):
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
        timestamp = datetime.utcnow().isoformat()
        
        text = response.text
        start_marker = "// ------------------------------------------ BEGINING: PLANS"
        end_marker = "// ------------------------------------------ END: PLANS"
        
        if start_marker in text and end_marker in text:
            try:
                json_str = text.split(start_marker)[1].split(end_marker)[0].strip()
                plans_data = json.loads(json_str)

                buyvm_config = provider.get('buyvm_config', {})
                target_location = buyvm_config.get('target_location', 'Luxembourg')
                target_groups = buyvm_config.get('target_groups', ['slice'])

                prices = {
                    "512": "$2.00/mo ($24/yr)",
                    "1024": "$3.50/mo",
                    "2048": "$7.00/mo",
                    "4096": "$15.00/mo",
                    "8192": "$30.00/mo",
                    "12288": "$45.00/mo",
                    "16384": "$60.00/mo",
                    "20480": "$75.00/mo",
                    "24576": "$90.00/mo",
                    "28672": "$105.00/mo",
                    "32768": "$120.00/mo"
                }

                for group_name in target_groups:
                    group_data = plans_data.get(group_name, {})
                    for plan_name, locations in group_data.items():
                        loc_info = None
                        for loc in locations:
                            if loc.get('location', '').lower() == target_location.lower():
                                loc_info = loc
                                break

                        if loc_info:
                            name = f"Slice {plan_name} ({target_location})"
                            disabled = loc_info.get('disabled') == 'true'
                            in_stock = not disabled

                            yield VpsStockItem(
                                provider=provider_name,
                                product_name=name,
                                price=prices.get(plan_name, "N/A"),
                                stock_status="Out of Stock" if disabled else "In Stock",
                                in_stock=in_stock,
                                url="https://buyvm.net/kvm-dedicated-server-slices/",
                                timestamp=timestamp
                            )
            except Exception as e:
                spider.logger.error(f"Error parsing BuyVM JS plans: {str(e)}")
        else:
            spider.logger.error(f"BuyVM JS markers not found in plans.js response for: {provider_name}")
