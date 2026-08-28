import json

import groq
from pydantic import BaseModel, ValidationError

from config import Config
from utils.logging import logger


class AIResponse(BaseModel):
    action: str  # "answer" or "escalate"
    response: str


class GroqClient:
    def __init__(self):
        self.client = groq.AsyncGroq(api_key=Config.GROQ_API_KEY)
        self.model = Config.GROQ_MODEL

    async def generate(self, context: str) -> AIResponse:
        messages = [
            {
                "role": "system",
                "content": "You are a Discord support bot. Respond only in the required JSON format.",
            },
            {"role": "user", "content": context},
        ]
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            data = json.loads(content)
            parsed = AIResponse(**data)
            usage = completion.usage
            tokens = usage.total_tokens if usage else None
            return parsed, tokens
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            logger.error(f"Invalid AI output: {e}")
            raise ValueError("Invalid AI response")
