from datetime import datetime
from ...core import Conversions

class Siablocks:

    @staticmethod
    def at_time(timestamp, consensus):
        current_height = consensus.height
        return current_height - Conversions.duration_to_siablocks(datetime.now() - timestamp)