from abc import ABC, abstractmethod

class BaseParser(ABC):
    """
    Abstract base class for all scraper parsing strategies.
    Defines the standard interface for generating requests and parsing responses.
    """

    @abstractmethod
    def generate_requests(self, spider, provider_config):
        """
        Generate scrapy.Request objects based on provider_config.
        
        :param spider: The scrapy.Spider instance.
        :param provider_config: Dictionary containing provider configuration.
        :yield: scrapy.Request or equivalent objects.
        """
        pass

    @abstractmethod
    def parse(self, response, spider):
        """
        Parse the HTTP response and yield VpsStockItems.
        
        :param response: The scrapy.http.Response object.
        :param spider: The scrapy.Spider instance.
        :yield: VpsStockItem objects.
        """
        pass

    def extract_value(self, selector, selectors_dict, field_name):
        """
        Utility method: Extracts value from a selector using either CSS or XPath patterns.
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

    def determine_stock(self, stock_status, selectors_dict):
        """
        Utility method: Determines whether the product is in stock based on parsed text
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
