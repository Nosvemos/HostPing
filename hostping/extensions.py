import logging

class SilenceScrapyNoiseExtension:
    """
    Scrapy extension that silences standard Scrapy core/twisted log messages,
    while keeping custom logger messages (e.g. hostping.*) intact at INFO level.
    """
    def __init__(self):
        # Override log levels after Scrapy has finished setting up logging
        logging.getLogger('scrapy').setLevel(logging.ERROR)
        logging.getLogger('twisted').setLevel(logging.ERROR)
        logging.getLogger('py.warnings').setLevel(logging.ERROR)

    @classmethod
    def from_crawler(cls, crawler):
        return cls()
