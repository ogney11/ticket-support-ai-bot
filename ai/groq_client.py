import json

import groq
from pydantic import BaseModel, ValidationError

from config import Config
from utils.logging import logger


class AIResponse(BaseModel):
    action: str  # "answer", "ask_more" or "escalate"
    response: str
    reason: str | None = None


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

    async def is_useful_knowledge(self, text: str) -> bool:
        """Return True if the model considers this message reusable, factual
        knowledge (how-to, FAQ, policies, facts) rather than chat/interpersonal
        noise. Used to decide whether to index a message as knowledge."""
        prompt = (
            "Decide whether the following message is useful, reusable, factual "
            "knowledge for a support knowledge base (e.g. a how-to, FAQ answer, "
            "guide, policy, or factual information) as opposed to casual chat, "
            "personal conversation, opinions, or off-topic noise.\n"
            'Reply with a single JSON object: {"useful": true} or {"useful": false}.\n'
            "Message:\n" + text
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You classify Discord messages for a support knowledge base. "
                    "Reply only with the JSON object requested."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=10,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            data = json.loads(content)
            return bool(data.get("useful", False))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Knowledge classification failed: {e}")
            return False
