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
        self.models = [Config.GROQ_MODEL, *Config.GROQ_MODEL_FALLBACKS]

    async def _complete(self, messages, temperature, max_tokens):
        """Run a chat completion, falling back across the configured model
        chain when a model is unavailable, decommissioned, or the key lacks
        access. Returns (content, completion) and updates self.model to the
        model that succeeded."""
        last_error = None
        for model in self.models:
            try:
                completion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                self.model = model
                return completion.choices[0].message.content, completion
            except Exception as e:  # noqa: BLE001
                if "json_validate_failed" in str(e):
                    # Strict JSON-schema validation failed (e.g. the model ran out
                    # of tokens mid-JSON or produced output not matching the schema).
                    # Try the next model in the chain before giving up.
                    logger.warning(f"Groq model '{model}' JSON validation failed: {e}")
                    last_error = e
                    continue
                last_error = e
                logger.warning(f"Groq model '{model}' failed (trying next): {e}")
        raise last_error

    async def generate(self, context: str) -> AIResponse:
        messages = [
            {
                "role": "system",
                "content": "You are a Discord support bot. Respond only in the required JSON format.",
            },
            {"role": "user", "content": context},
        ]
        try:
            content, completion = await self._complete(
                messages, temperature=0.3, max_tokens=800
            )
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
            content, _ = await self._complete(messages, temperature=0.0, max_tokens=100)
            data = json.loads(content)
            return bool(data.get("useful", False))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Knowledge classification failed: {e}")
            return False
