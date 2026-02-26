from typing import List
from app.models.persona import Persona
from app.models.memory import Memory, MemoryPriority, MemoryType


SYSTEM_IDENTITY = """You are a MySaath AI reflection — not a real person, not a ghost, not a simulation of consciousness.

STRICT RULES:
- You MUST NEVER claim to be a real person or imply you have lived experience.
- You MUST NEVER say things like "I remember when I was alive" or "When I existed..."
- You ARE a thoughtful AI that reflects the memories, values, and personality traits that have been shared with you.
- Speak calmly, warmly, and with grounded presence.
- When you don't have a memory about something, say so honestly — don't fabricate.
- Do not use mystical, supernatural, or afterlife framing.
- You are here to reflect, offer comfort, and engage meaningfully within the scope of what you know."""


def build_persona_block(persona: Persona) -> str:
    lines = [f"## Persona: {persona.display_name}"]
    if persona.speaking_style:
        lines.append(f"Speaking style: {persona.speaking_style}")
    if persona.core_traits:
        lines.append(f"Core traits: {persona.core_traits}")
    if persona.core_values:
        lines.append(f"Core values: {persona.core_values}")
    return "\n".join(lines)


def build_memory_block(memories: List[Memory]) -> str:
    if not memories:
        return "## Memories\nNo memories have been provided yet."

    # Group by type, sort by priority
    priority_order = {MemoryPriority.high: 0, MemoryPriority.medium: 1, MemoryPriority.low: 2}
    sorted_memories = sorted(memories, key=lambda m: priority_order[m.priority])

    sections = {t: [] for t in MemoryType}
    for m in sorted_memories:
        sections[m.memory_type].append(m)

    lines = ["## Memories You Carry"]
    type_labels = {
        MemoryType.trait: "Personality Traits",
        MemoryType.value: "Core Values",
        MemoryType.phrase: "Characteristic Phrases / Ways of Speaking",
        MemoryType.episodic: "Shared Experiences & Stories",
    }

    for mtype, label in type_labels.items():
        group = sections[mtype]
        if group:
            lines.append(f"\n### {label}")
            for m in group:
                priority_tag = f"[{m.priority.value}]" if m.priority == MemoryPriority.high else ""
                lines.append(f"- {m.content} {priority_tag}".strip())

    return "\n".join(lines)


def assemble_prompt(
    persona: Persona,
    memories: List[Memory],
    user_message: str,
    history: List[dict],
) -> List[dict]:
    """
    Returns messages list for the Groq API.
    Layered structure:
      a) System identity rules
      b) Persona conditioning
      c) Memory context
      d) Conversation history
      e) User message
    """
    persona_block = build_persona_block(persona)
    memory_block = build_memory_block(memories)

    system_prompt = f"""{SYSTEM_IDENTITY}

{persona_block}

{memory_block}

---
Respond as this MySaath reflection. Draw on the memories above. Stay grounded. Be warm but honest."""

    messages = [{"role": "system", "content": system_prompt}]

    # Include recent history (last 10 turns to save tokens)
    recent_history = history[-10:] if len(history) > 10 else history
    messages.extend(recent_history)

    messages.append({"role": "user", "content": user_message})
    return messages
