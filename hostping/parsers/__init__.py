from hostping.parsers.list_parser import ListParser
from hostping.parsers.single_parser import SingleParser
from hostping.parsers.buyvm_parser import BuyvmParser
from hostping.parsers.ovh_parser import OvhParser

class ParserFactory:
    """
    Factory class to return the appropriate parser strategy
    based on the scraping_mode defined in the configuration.
    """
    @staticmethod
    def get_parser(mode):
        mode_lower = mode.lower() if mode else "single"
        
        if mode_lower == "list":
            return ListParser()
        elif mode_lower == "buyvm_js":
            return BuyvmParser()
        elif mode_lower == "ovh_engine_api":
            return OvhParser()
        else:
            # Default to single parser
            return SingleParser()
