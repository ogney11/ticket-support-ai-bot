from sqlalchemy.ext.asyncio import AsyncSession
from database.models import AIUsageLog


class UsageLogRepository:
    @staticmethod
    async def create(
        session: AsyncSession,
        ticket_id: int,
        user_message_id: int,
        response: str | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
        success: bool = True,
        error: str | None = None,
    ):
        record = AIUsageLog(
            ticket_id=ticket_id,
            user_message_id=user_message_id,
            response=response,
            model=model,
            tokens_used=tokens_used,
            success=success,
            error=error,
        )
        session.add(record)
        await session.commit()
        return record
