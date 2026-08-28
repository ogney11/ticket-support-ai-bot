from discord import TextChannel, CategoryChannel
from config import Config
import re


class TicketDetector:
    @staticmethod
    def is_ticket(channel: TextChannel) -> bool:
        if channel.id in Config.TICKET_CHANNEL_IDS:
            return True
        if channel.category and channel.category.id in Config.TICKET_CATEGORY_IDS:
            return True
        if Config.TICKET_NAME_PATTERN:
            if re.match(Config.TICKET_NAME_PATTERN, channel.name):
                return True
        return False
