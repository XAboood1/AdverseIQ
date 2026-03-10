"""
app/core/k2_client.py

Two K2 clients for two endpoints:

K2StandardClient  → api.k2think.ai / MBZUAI-IFM/K2-Think-v2
    Used by: Rapid Check, Mechanism Trace
    - No tool calling on this endpoint
    - No JSON mode — JSON repair pipeline required
    - reasoning_content field carries thinking stream (no think-tag parsing needed)
    - Rate limit: 15 RPM conservative threshold

K2AgenticClient   → build-api.k2think.ai / MBZUAI-IFM/K2-V2-Instruct
    Used by: Mystery Solver only
    - Tool calling with parallel tool calls
    - JSON mode via response_format: json_object — guaranteed valid JSON
    - reasoning_content field for clean thinking stream
    - logprobs on content tokens for confidence calibration
    - Agent loop: K2 calls tools, you execute them, K2 reasons on results
    - Double-JSON argument parsing (REQUIRED — build-api double-encodes arguments)
    - Same API key works for both endpoints

CRITICAL NOTES FROM CAPABILITY TESTING:
  - tool_choice: "none" is BROKEN — omit tools array entirely to suppress tool calls
  - Tool arguments are DOUBLE-JSON-encoded — always use _parse_tool_arguments()
  - Streaming closes early on finish_reason: tool_calls — switch to non-streaming
    for tool-call turns; use streaming only for the final answer turn
  - max_tokens < 50 causes timeouts — always use >= 50
  - logprobs only apply to content tokens, NOT reasoning_content tokens
  - reasoning_content is never null — always present in every response
"""

import json
import math
import time
import asyncio
import logging
from typing import AsyncIterator, Optional, Callable, Any

from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ======================================================================
# Shared utilities
# ======================================================================

def _parse_tool_arguments(raw_arguments: str) -> dict:
    """
    Build-api tool call arguments are DOUBLE-JSON-encoded.
    Always use this function — never json.loads() directly on arguments.

    From capability doc:
        json.loads(json.loads(tc["function"]["arguments"]))
        or safer: parse once, check if result is still a string, parse again.
    """
    try:
        first = json.loads(raw_arguments)
        if isinstance(first, str):
            return json.loads(first)
        return first
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Tool argument double-parse failed: {e} | raw: {raw_arguments[:300]}")
        return {}


def _extract_logprob_certainty(logprobs_content: list, target_token: str) -> Optional[float]:
    """
    Find the logprob for a specific token and return a 0–1 certainty probability.

    Used to validate K2's self-reported confidence number. If K2 says confidence=87
    but the logprob on that token is very low, the model was hedging — discount the score.

    logprobs are only available on build-api content tokens (not reasoning_content).
    Returns None if token not found or logprobs unavailable.
    """
    if not logprobs_content:
        return None
    for token_data in logprobs_content:
        if token_data.get("token", "").strip() == target_token:
            lp = token_data.get("logprob", -20.0)
            return math.exp(max(lp, -20.0))  # clamp to avoid underflow
    return None


def _calibrate_confidence_with_logprobs(
    k2_confidence: int,
    logprobs_content: Optional[list],
) -> tuple[int, str]:
    """
    Adjust K2's self-reported confidence score using logprob certainty.

    Calibration tiers:
      certainty >= 0.7  → model was decisive  → keep score unchanged
      certainty 0.3–0.7 → mild uncertainty    → discount 10%
      certainty < 0.3   → model was hedging   → discount 20%
      no logprobs       → return score as-is

    Returns (adjusted_score, annotation_string) for transparency in the UI.
    """
    if not logprobs_content:
        return k2_confidence, "logprob calibration unavailable"

    certainty = _extract_logprob_certainty(logprobs_content, str(k2_confidence))
    if certainty is None:
        return k2_confidence, "confidence token not found in logprobs"

    if certainty >= 0.7:
        return k2_confidence, f"model certainty high ({certainty:.2f}) — score kept"
    elif certainty >= 0.3:
        adjusted = max(0, round(k2_confidence * 0.90))
        return adjusted, f"model certainty medium ({certainty:.2f}) — score discounted 10%"
    else:
        adjusted = max(0, round(k2_confidence * 0.80))
        return adjusted, f"model certainty low ({certainty:.2f}) — score discounted 20%"


# ======================================================================
# Tool definitions — passed to K2AgenticClient calls
# K2 sees these and decides which ones to call during its reasoning.
# ======================================================================

ADVERSEIQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_drug_interaction",
            "description": (
                "Look up known drug interactions between two specific drugs in the "
                "AdverseIQ interaction database. Returns severity, mechanism, and "
                "description if a known interaction exists. Call this for every drug pair."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_a": {
                        "type": "string",
                        "description": "First drug name (generic preferred)",
                    },
                    "drug_b": {
                        "type": "string",
                        "description": "Second drug name (generic preferred)",
                    },
                },
                "required": ["drug_a", "drug_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_pubmed",
            "description": (
                "Search PubMed for drug interaction case reports and clinical studies. "
                "Use this to find recent literature that may not yet appear in static databases. "
                "Returns titles, abstract snippets, and PMIDs. "
                "Use targeted queries: e.g. 'tramadol sertraline serotonin syndrome case report'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "PubMed search query combining drug names and clinical context",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drug_class",
            "description": (
                "Get the pharmacological class(es) of a drug. "
                "Use this to assess systemic risks: serotonergic load, QT prolongation burden, "
                "anticoagulant risk, and herb-drug interaction potential."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "Drug name (generic preferred)",
                    },
                },
                "required": ["drug_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cyp_profile",
            "description": (
                "Get the CYP enzyme inhibition and induction profile of a drug. "
                "Use this to verify pharmacokinetic interactions — which enzymes does "
                "this drug inhibit, induce, or get metabolised by? "
                "Essential for confirming CYP-mediated drug interactions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "Drug name (generic preferred)",
                    },
                },
                "required": ["drug_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_safe_alternative",
            "description": (
                "Given a dangerous drug interaction, suggest a therapeutically equivalent "
                "safer alternative that avoids the interaction mechanism. "
                "Call this after identifying the primary interaction and the offending drug."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_to_replace": {
                        "type": "string",
                        "description": "The drug causing the interaction that should be replaced",
                    },
                    "indication": {
                        "type": "string",
                        "description": "What the drug is used for, e.g. 'antifungal', 'pain relief'",
                    },
                    "interacting_drug": {
                        "type": "string",
                        "description": "The co-prescribed drug that must be kept",
                    },
                },
                "required": ["drug_to_replace", "indication", "interacting_drug"],
            },
        },
    },
]


# ======================================================================
# K2StandardClient — api.k2think.ai
# Used for Rapid Check and Mechanism Trace
# ======================================================================

class K2StandardClient:
    """
    Standard endpoint. No tool calling. No JSON mode.
    JSON repair pipeline required for all responses.
    reasoning_content carries the thinking stream — no think-tag parsing needed.
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.k2_api_key,
            base_url=settings.k2_base_url,
        )
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def _throttle(self):
        """Enforce 15 RPM rate limit with rolling window."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - settings.k2_rate_window
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            if len(self._timestamps) >= settings.k2_rate_limit:
                wait = self._timestamps[0] + settings.k2_rate_window - now + 0.5
                if wait > 0:
                    logger.warning(f"Standard client rate limit — waiting {wait:.1f}s")
                    await asyncio.sleep(wait)
            self._timestamps.append(time.monotonic())

    @staticmethod
    def repair_json(raw: str) -> Optional[dict]:
        """
        Multi-step JSON repair for standard endpoint responses.
        Steps: strip think tags → extract from fences → stack-match braces → fix commas → parse.
        """
        import re

        # Strip inline think tags (standard endpoint may still include them)
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()

        # Extract raw content from markdown fences (non-greedy inside fences only)
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence:
            text = fence.group(1).strip()

        # Find the first '{' then stack-match to its closing '}'
        # This avoids rfind grabbing a second object or trailing stray braces.
        start = text.find("{")
        if start != -1:
            depth = 0
            in_str = False
            escape = False
            end = -1
            for i, ch in enumerate(text[start:], start):
                if escape:
                    escape = False
                    continue
                if ch == "\\" and in_str:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_str = not in_str
                if in_str:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end != -1:
                text = text[start: end + 1]

        # Repair trailing commas before } or ]
        text = re.sub(r",\s*([}\]])", r"\1", text)

        # Close unclosed structures
        text += "]" * max(0, text.count("[") - text.count("]"))
        text += "}" * max(0, text.count("{") - text.count("}"))

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            logger.warning(f"JSON repair failed: {err}")
            return None

    async def call_and_parse_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        timeout: float = 90.0,
        demo_fallback: Optional[dict] = None,
    ) -> dict:
        """
        Non-streaming call with JSON repair pipeline.
        Falls back to self-repair call if first parse fails.
        Falls back to demo_fallback if both fail.
        """
        await self._throttle()
        try:
            response = await self.client.chat.completions.create(
                model=settings.k2_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                timeout=timeout,
            )
            content = response.choices[0].message.content or ""
            result = self.repair_json(content)
            if result is not None:
                return result

            # Self-repair: ask K2 to fix its own output
            logger.warning("Standard: first JSON parse failed — attempting self-repair")
            await self._throttle()
            fix = await self.client.chat.completions.create(
                model=settings.k2_model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Fix the following malformed JSON. Return ONLY valid JSON, "
                        f"no explanation, no markdown:\n\n{content[:4000]}"
                    ),
                }],
                max_tokens=2048,
                timeout=30.0,
            )
            fixed = self.repair_json(fix.choices[0].message.content or "")
            if fixed is not None:
                return fixed

        except Exception as exc:
            logger.error(f"Standard K2 call failed: {exc}", exc_info=True)

        if demo_fallback is not None:
            logger.warning("Standard: all repair attempts failed — using demo fallback")
            return demo_fallback

        raise ValueError("Standard K2 client: could not parse response after all repair steps")

    async def stream_reasoning(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        timeout: float = 90.0,
    ) -> AsyncIterator[dict]:
        """
        Streaming call.
        Yields {"type": "thinking", "token": str} from reasoning_content.
        Yields {"type": "done", "full_content": str} when complete.
        """
        await self._throttle()
        content_parts: list[str] = []

        stream = await self.client.chat.completions.create(
            model=settings.k2_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            stream=True,
            timeout=timeout,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # reasoning_content — clean thinking tokens for display
            thinking = getattr(delta, "reasoning_content", None) or ""
            if thinking and not thinking.strip().startswith(("{", "[", "}", "]")):
                yield {"type": "thinking", "token": thinking}

            # content — the actual answer
            content = delta.content or ""
            if content:
                content_parts.append(content)

        yield {"type": "done", "full_content": "".join(content_parts)}

    async def check_reachable(self) -> bool:
        try:
            await self._throttle()
            r = await self.client.chat.completions.create(
                model=settings.k2_model,
                messages=[{"role": "user", "content": "Reply OK only."}],
                max_tokens=50,
                timeout=15.0,
            )
            return bool(r.choices[0].message.content)
        except Exception as exc:
            logger.error(f"Standard reachability check failed: {exc}")
            return False


# ======================================================================
# K2AgenticClient — build-api.k2think.ai
# Used for Mystery Solver only
# ======================================================================

class K2AgenticClient:
    """
    Agentic endpoint. Tool calling. JSON mode. Logprobs. 512K context.

    Agent loop behaviour:
      Turn N (tool-call turns):
        - Pass tools array
        - K2 returns finish_reason: "tool_calls"
        - You execute tool calls and append results to messages
        - Loop continues

      Final turn:
        - Do NOT pass tools (tool_choice: "none" is broken — omit tools entirely)
        - Add response_format: json_object
        - Add logprobs: true for confidence calibration
        - K2 returns finish_reason: "stop" with valid JSON

    Streaming:
      - Stream closes after tool_calls finish_reason (this is expected)
      - Use non-streaming for all tool-call turns
      - Thinking tokens come from reasoning_content delta, not content delta
    """

    MAX_TURNS = 5  # 4–5 is typical; 5 is a good balance of depth vs speed

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.k2_api_key,
            base_url=settings.k2_build_url,
        )
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def _throttle(self):
        async with self._lock:
            now = time.monotonic()
            cutoff = now - settings.k2_rate_window
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            if len(self._timestamps) >= settings.k2_rate_limit:
                wait = self._timestamps[0] + settings.k2_rate_window - now + 0.5
                if wait > 0:
                    logger.warning(f"Agentic client rate limit — waiting {wait:.1f}s")
                    await asyncio.sleep(wait)
            self._timestamps.append(time.monotonic())

    async def run_agent_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_executor: Callable[[str, dict], Any],
        thinking_callback: Optional[Callable[[str], None]] = None,
        demo_fallback: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> tuple[dict, Optional[list], list[str]]:
        """
        Run the full agentic investigation loop.

        Args:
            system_prompt:      K2 system instructions including tool guidance
            user_prompt:        Patient case — medications, symptoms, context
            tool_executor:      async callable(tool_name: str, args: dict) -> any
                                You implement the tools; K2 decides when to call them
            thinking_callback:  sync callable(token: str) — called with each
                                reasoning_content token for SSE display
            demo_fallback:      returned silently if all turns fail
            timeout:            per-turn HTTP timeout in seconds

        Returns:
            (result_dict, logprobs_content, tool_calls_made)
            - result_dict:      parsed JSON from K2's final answer
            - logprobs_content: token logprob list from final turn (may be None)
            - tool_calls_made:  list of tool names K2 called, in order
        """
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        tool_calls_made: list[str] = []
        logprobs_content: Optional[list] = None

        for turn in range(self.MAX_TURNS):
            await self._throttle()
            is_final = (turn == self.MAX_TURNS - 1)

            # Build request kwargs
            kwargs: dict = {
                "model": settings.k2_build_model,
                "messages": messages,
                "max_tokens": 4096,
                "timeout": timeout,
            }

            if is_final:
                # Final turn: JSON mode + logprobs, NO tools
                # (tool_choice: "none" is broken — omit tools array entirely)
                kwargs["response_format"] = {"type": "json_object"}
                kwargs["logprobs"] = True
                kwargs["top_logprobs"] = 3
            else:
                kwargs["tools"] = ADVERSEIQ_TOOLS

            try:
                response = await self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                logger.error(f"Agentic turn {turn} API call failed: {exc}", exc_info=True)
                if demo_fallback:
                    return demo_fallback, None, tool_calls_made
                raise

            choice = response.choices[0]
            finish_reason = choice.finish_reason

            # Extract and stream reasoning tokens
            reasoning = getattr(choice.message, "reasoning_content", None) or ""
            if reasoning and thinking_callback:
                # Filter JSON fragments from thinking display
                clean = " ".join(
                    w for w in reasoning.split()
                    if not w.strip().startswith(("{", "[", "}", "]", '"'))
                )
                if clean.strip():
                    thinking_callback(clean + " ")

            # ---- Tool calls turn ----
            if finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls or []

                # Append assistant message with tool_calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": choice.message.content,  # may be None
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                # Execute each tool call — K2 may call multiple in parallel
                for tc in tool_calls:
                    name = tc.function.name
                    args = _parse_tool_arguments(tc.function.arguments)
                    tool_calls_made.append(name)

                    logger.info(f"K2 → tool: {name}({json.dumps(args)})")
                    if thinking_callback:
                        thinking_callback(f"\n[Tool: {name}({json.dumps(args)})]\n")

                    try:
                        tool_result = await tool_executor(name, args)
                        result_str = (
                            json.dumps(tool_result)
                            if isinstance(tool_result, (dict, list))
                            else str(tool_result)
                        )
                    except Exception as exc:
                        result_str = f"Tool error: {exc}"
                        logger.warning(f"Tool {name} execution failed: {exc}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                # Continue — K2 will reason on the tool results
                continue

            # ---- Stop turn — K2 reached a conclusion ----
            if finish_reason == "stop":
                content = choice.message.content or ""

                # Capture logprobs from final turn for confidence calibration
                if hasattr(choice, "logprobs") and choice.logprobs:
                    logprobs_content = choice.logprobs.content

                # Parse JSON — on the final turn response_format guarantees validity
                try:
                    return json.loads(content), logprobs_content, tool_calls_made
                except json.JSONDecodeError:
                    # Intermediate stop (not final turn) — try repair
                    repaired = K2StandardClient.repair_json(content)
                    if repaired:
                        return repaired, logprobs_content, tool_calls_made
                    logger.warning(f"Turn {turn} stop but JSON parse failed — continuing")
                    continue

            logger.warning(f"Unexpected finish_reason '{finish_reason}' on turn {turn}")

        # Max turns exhausted
        logger.error("Agentic loop: MAX_TURNS reached without a clean stop")
        if demo_fallback:
            return demo_fallback, None, tool_calls_made
        raise ValueError("Agentic loop: MAX_TURNS reached without conclusion")

    async def stream_agent_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_executor: Callable[[str, dict], Any],
        demo_fallback: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> AsyncIterator[dict]:
        """
        Run the agent loop and yield SSE-compatible event dicts in real-time.

        Event types:
            {"event": "thinking",     "data": str}   — K2 reasoning tokens (live)
            {"event": "tool_summary", "data": str}   — tools K2 called
            {"event": "result",       "data": dict}  — final parsed AnalysisResult
            {"event": "error",        "data": str}   — error message
        """
        thinking_q: asyncio.Queue = asyncio.Queue()

        def thinking_cb(token: str):
            try:
                thinking_q.put_nowait(token)
            except asyncio.QueueFull:
                pass  # drop rather than block

        # Launch the agent loop concurrently so we can stream tokens while it runs
        loop_task: asyncio.Task = asyncio.create_task(
            self.run_agent_loop(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tool_executor=tool_executor,
                thinking_callback=thinking_cb,
                demo_fallback=demo_fallback,
                timeout=timeout,
            )
        )

        try:
            # Drain thinking tokens in real-time while the loop is running
            while not loop_task.done():
                try:
                    token = await asyncio.wait_for(thinking_q.get(), timeout=0.05)
                    yield {"event": "thinking", "data": token}
                except asyncio.TimeoutError:
                    await asyncio.sleep(0)  # yield control back to event loop

            # Drain any tokens that arrived in the final batch
            while not thinking_q.empty():
                token = thinking_q.get_nowait()
                yield {"event": "thinking", "data": token}

            # Retrieve result — task is already done, this returns immediately
            result, _logprobs, tools_used = await loop_task

        except Exception as exc:
            logger.error(f"stream_agent_loop failed: {exc}", exc_info=True)
            yield {"event": "error", "data": str(exc)}
            return

        if tools_used:
            yield {
                "event": "tool_summary",
                "data": (
                    f"K2 autonomously called {len(tools_used)} tools: "
                    f"{', '.join(dict.fromkeys(tools_used))}"
                ),
            }

        yield {"event": "result", "data": result}

    async def check_reachable(self) -> bool:
        try:
            await self._throttle()
            r = await self.client.chat.completions.create(
                model=settings.k2_build_model,
                messages=[{"role": "user", "content": "Reply OK only."}],
                max_tokens=50,
                timeout=15.0,
            )
            return bool(r.choices[0].message.content)
        except Exception as exc:
            logger.error(f"Agentic reachability check failed: {exc}")
            return False


# ======================================================================
# Singleton instances — import these everywhere
# ======================================================================

k2_client = K2StandardClient()       # Rapid Check, Mechanism Trace
k2_build_client = K2AgenticClient()  # Mystery Solver