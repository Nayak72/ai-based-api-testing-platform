"""Structured output helper with json-repair + Pydantic validation + retry loop."""

from __future__ import annotations

import json

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger()


def _simple_repair_json(s: str) -> str:
    """Lightweight fallback repair when json_repair package is not installed."""
    s = s.strip()
    # Strip markdown code fences if present
    if s.startswith("```"):
        lines = s.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    in_str = False
    escape = False
    open_curly = 0
    open_square = 0
    for ch in s:
        if ch == "\\" and not escape:
            escape = True
            continue
        if ch == '"' and not escape:
            in_str = not in_str
        elif not in_str:
            if ch == "{":
                open_curly += 1
            elif ch == "}":
                open_curly -= 1
            elif ch == "[":
                open_square += 1
            elif ch == "]":
                open_square -= 1
        escape = False

    if in_str:
        s += '"'
    while open_square > 0:
        s += "]"
        open_square -= 1
    while open_curly > 0:
        s += "}"
        open_curly -= 1
    return s


class StructuredOutputError(Exception):
    """Raised when structured output cannot be produced after max_repairs attempts."""


async def generate_structured(
    ai_orchestrator,
    prompt: str,
    system: str,
    model_cls: type[BaseModel],
    max_repairs: int = 2,
    model: str | None = None,
) -> BaseModel:
    """
    Generate and parse a Pydantic model from an LLM response.

    Strategy per attempt:
      1. Call LLM with JSON mode.
      2. Try json_repair.loads (handles partial/malformed JSON from small models).
      3. Validate with Pydantic.
      4. On failure, re-prompt with the validation error + previous output (max_repairs loops).
    """
    from app.ai.providers.base import GenerationRequest

    original_prompt = prompt
    last_error: str | None = None
    last_content: str | None = None
    repairs_used = 0

    for attempt in range(max_repairs + 1):
        if attempt > 0 and last_error and last_content:
            repairs_used += 1
            prompt = (
                f"{original_prompt}\n\n"
                f"--- PREVIOUS OUTPUT (attempt {attempt}) ---\n{last_content}\n"
                f"--- VALIDATION ERROR ---\n{last_error}\n"
                "Fix the JSON so it passes validation and output ONLY valid JSON."
            )

        request = GenerationRequest(
            prompt=prompt,
            system_prompt=system,
            temperature=0.1,
            max_tokens=4096,
            response_format="json_object",
            model=model,
        )

        response = await ai_orchestrator.generate(request)
        content = response.content
        last_content = content

        # Step 1: try json_repair
        data = None
        try:
            import json_repair  # type: ignore[import]

            data = json_repair.loads(content)
        except Exception:
            pass

        # Step 2: fallback simple repair
        if data is None:
            try:
                repaired = _simple_repair_json(content)
                data = json.loads(repaired)
            except Exception:
                pass

        # Step 3: fall back to stdlib json
        if data is None:
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                last_error = f"JSON parse failed: {e}"
                logger.warning("JSON parse failed", attempt=attempt, error=last_error)
                continue

        # Step 3: Pydantic validation
        try:
            result = model_cls.model_validate(data)
            if repairs_used:
                logger.info("Structured output succeeded after repairs", repairs_used=repairs_used)
            return result
        except ValidationError as e:
            last_error = str(e)
            logger.warning("Pydantic validation failed", attempt=attempt, error=last_error[:300])
            continue

    raise StructuredOutputError(
        f"Failed to produce valid {model_cls.__name__} after {repairs_used} repair(s). Last error: {last_error}"
    )
