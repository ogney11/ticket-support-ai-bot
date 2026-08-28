from ai.prompts import FORMAT_INSTRUCTIONS


def _format_history(history) -> str:
    lines = []
    for m in history:
        who = "User" if m.author_type == "user" else "Assistant"
        lines.append(f"[{who}] {m.content}")
    return "\n".join(lines) if lines else "(no prior conversation)"


def _format_knowledge(knowledge) -> str:
    lines = []
    for i, k in enumerate(knowledge, start=1):
        if hasattr(k, "question"):
            lines.append(f"{i}. Q: {k.question}\n   A: {k.answer}")
        else:
            lines.append(f"{i}. {k.content}")
    return "\n".join(lines) if lines else "(no knowledge available)"


def build_context(
    system: str,
    knowledge,
    history,
    user_message: str,
) -> str:
    knowledge_text = _format_knowledge(knowledge)
    history_text = _format_history(history)

    context = f"""{system}

{FORMAT_INSTRUCTIONS}

===== KNOWLEDGE BASE =====
{knowledge_text}

===== TICKET CONVERSATION HISTORY =====
{history_text}

===== NEW USER MESSAGE =====
{user_message}
"""
    return context.strip()
