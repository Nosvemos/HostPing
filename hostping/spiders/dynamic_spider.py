import os
import json
import logging
import scrapy
from hostping.parsers import ParserFactory

logger = logging.getLogger(__name__)

class DynamicSpider(scrapy.Spider):
    name = "dynamic_spider"

    async def start(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(project_root, 'config', 'providers.json')

        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at: {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                providers = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load or parse providers config: {str(e)}")
            return

        for provider in providers:
            provider_name = provider.get('provider_name', 'unknown')
            
            # Check for an environment variable override: ENABLE_PROVIDER_NAME
            env_key = f"ENABLE_{provider_name.replace(' ', '_').replace('-', '_').upper()}"
            env_val = os.getenv(env_key)
            
            is_enabled = provider.get('enabled', True)
            if env_val is not None:
                is_enabled = env_val.lower() in ('true', '1', 'yes')
                
            if not is_enabled:
                logger.info(f"Skipping disabled provider: {provider_name}")
                continue

            mode = provider.get('scraping_mode', 'single')
            parser = ParserFactory.get_parser(mode)
            
            try:
                for request in parser.generate_requests(self, provider):
                    yield request
            except Exception as e:
                logger.error(f"Failed to generate requests for {provider.get('provider_name')} using {mode} parser: {str(e)}")

    def parse(self, response):
        provider = response.meta.get('provider_config', {})
        provider_name = provider.get('provider_name', 'Unknown')
        mode = provider.get('scraping_mode', 'single')

        logger.info(f"Parsing page for: {provider_name} | URL: {response.url}")

        parser = ParserFactory.get_parser(mode)
        
        try:
            for item in parser.parse(response, self):
                yield item
        except Exception as e:
            logger.error(f"Failed to parse response for {provider_name} using {mode} parser: {str(e)}")
