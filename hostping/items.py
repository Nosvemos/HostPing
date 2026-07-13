import scrapy

class VpsStockItem(scrapy.Item):
    provider = scrapy.Field()
    product_name = scrapy.Field()
    price = scrapy.Field()
    stock_status = scrapy.Field()
    in_stock = scrapy.Field()
    url = scrapy.Field()
    timestamp = scrapy.Field()
