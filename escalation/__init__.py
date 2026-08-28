from datetime import datetime, timedelta

from config import Config
from database.repositories.escalations import EscalationRepository
from utils.logging import logger


class EscalationManager:
    COOLDOWN = timedelta(minutes=15)

    async def trigger(self, session, ticket_id, channel, guild, reason=None):
        last = await EscalationRepository.get_last_for_ticket(session, ticket_id)
        if last and last.last_notified:
            if datetime.utcnow() - last.last_notified < self.COOLDOWN:
                logger.info(
                    f"Escalation cooldown active for ticket {ticket_id}, skipping"
                )
                return False

        await EscalationRepository.create(
            session, ticket_id, reason=reason or "Insufficient knowledge"
        )

        role = guild.get_role(Config.SUPPORT_ROLE_ID) if guild else None
        if role:
            await channel.send(
                f"{role.mention} I couldn't find enough information to answer this "
                f"accurately. I've notified the support team."
            )
        else:
            await channel.send(
                "I couldn't find enough information to answer this accurately. "
                "Please contact support."
            )

        await EscalationRepository.update_last_notified(session, ticket_id)
        return True


class EscalationManagerInstance(EscalationManager):
    pass
