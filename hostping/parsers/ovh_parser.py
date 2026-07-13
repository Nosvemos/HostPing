import json
import scrapy
from urllib.parse import urlencode
from datetime import datetime
from hostping.items import VpsStockItem
from hostping.parsers.base import BaseParser

class OvhParser(BaseParser):
    def generate_requests(self, spider, provider_config):
        url = provider_config.get('url')
        bypass_cf = provider_config.get('bypass_cloudflare', False)
        
        ovh_config = provider_config.get('ovh_config', {})
        subsidiary = ovh_config.get('subsidiary', 'WE')
        os_param = ovh_config.get('os', 'Ubuntu 24.04')
        target_location = ovh_config.get('target_location', 'DE')
        plans = ovh_config.get('plans', [])

        for plan in plans:
            plan_code = plan.get('plan_code')
            plan_name = plan.get('name', plan_code)
            plan_price = plan.get('price', 'N/A')

            params = {
                "ovhSubsidiary": subsidiary,
                "os": os_param,
                "planCode": plan_code
            }
            query_url = f"{url}?{urlencode(params)}"

            yield scrapy.Request(
                url=query_url,
                method='GET',
                callback=spider.parse,
                meta={
                    'provider_config': provider_config,
                    'plan_code': plan_code,
                    'plan_name': plan_name,
                    'plan_price': plan_price,
                    'target_location': target_location,
                    'timestamp': datetime.utcnow().isoformat(),
                    'bypass_cloudflare': bypass_cf
                },
                dont_filter=True
            )

    def parse(self, response, spider):
        provider = response.meta['provider_config']
        plan_code = response.meta['plan_code']
        plan_name = response.meta['plan_name']
        plan_price = response.meta['plan_price']
        target_location = response.meta['target_location']
        timestamp = response.meta['timestamp']

        try:
            data = json.loads(response.text)
            datacenters = data.get("datacenters", [])

            dc = next((d for d in datacenters if d.get("datacenter") == target_location), None)

            if dc:
                status = dc.get("status", "unavailable")
                in_stock = status == "available"
                stock_status = "In Stock" if in_stock else "Out of Stock"
            else:
                in_stock = False
                stock_status = "Unavailable in region"

            yield VpsStockItem(
                provider=provider.get('provider_name', 'OVH'),
                product_name=plan_name,
                price=plan_price,
                stock_status=stock_status,
                in_stock=in_stock,
                url=f"https://www.ovhcloud.com/en/vps/configurator/?planCode={plan_code}",
                timestamp=timestamp
            )
        except Exception as e:
            spider.logger.error(f"Error parsing OVH engine API response for {plan_code}: {str(e)}")
