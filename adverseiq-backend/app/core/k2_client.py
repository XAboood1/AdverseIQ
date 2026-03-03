import asyncio
import json
import logging
import re
import time
from typing import AsyncIterator, Optional, Any

from json_repair import repair_json
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class K2Client:
    """
    Wraps the K2 Think V2 API with:
    - Rate limiting (18 RPM safe threshold)
    - Think-tag stripping (handles missing closing tag)
    - Multi-step JSON repair pipeline
    - Demo fallback escape hatch
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.k2_api_key,
            base_url=settings.k2_base_url,
        )
        self._request_timestamps: list[float] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Rate limiting
    # ------------------------------------------------------------------ #
    async def _check_rate_limit(self) -> None:
        """Sleep if we are approaching the 18 RPM safe threshold."""
        async with self._lock:
            now = time.monotonic()
            window_start = now - settings.k2_rate_window

            # Remove timestamps outside the rolling window
            self._request_timestamps = [
                t for t in self._request_timestamps if t > window_start
            ]

            if len(self._request_timestamps) >= settings.k2_rate_limit:
                oldest = self._request_timestamps[0]
                sleep_for = (oldest + settings.k2_rate_window) - now + 0.5
                if sleep_for > 0:
                    logger.warning(
                        f"Rate limit approaching — sleeping {sleep_for:.1f}s"
                    )
                    await asyncio.sleep(sleep_for)

            self._request_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------ #
    # Think-tag stripping
    # ------------------------------------------------------------------ #
    @staticmethod
    def strip_think_tags(text: str) -> str:
        """
        Remove <think>...</think> blocks from K2 output.
        Handles the edge case where the closing tag is missing.
        """
        # Remove complete think blocks
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Remove unclosed think block (opening tag with no closing tag)
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
        return text.strip()

    # ------------------------------------------------------------------ #
    # JSON repair pipeline
    # ------------------------------------------------------------------ #
    @staticmethod
    def _preprocess(text: str) -> str:
        """
        Fix K2-specific output issues before attempting JSON parse:
        - Python literals → JSON literals
        - Smart/curly quotes → straight quotes
        - Literal newlines inside strings → \\n
        - Unescaped control characters
        """
        # Python boolean/None literals → JSON
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)

        # Smart/curly quotes → straight quotes
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")

        # Replace literal tab characters (common in K2 reasoning output)
        text = text.replace('\t', ' ')

        return text

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Pull the LARGEST valid JSON object from text.

        K2 often emits reasoning prose before the JSON and also returns
        arrays nested inside the outer object.  Scanning from the last '{'
        picks up inner array elements (e.g. the last item in causal_steps).
        Instead, try every '{' as a potential start and return the longest
        complete block — the outermost wrapper always produces the longest
        match and wins over nested items.
        """
        # 1. Markdown code fence wins unconditionally
        fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if fence:
            candidate = fence.group(1).strip()
            if candidate.startswith('{'):
                return candidate

        # 2. Try every '{' as start; keep the longest complete JSON block found
        best = ""
        for start in range(len(text)):
            if text[start] != '{':
                continue
            depth = 0
            in_str = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\' and in_str:
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        if len(candidate) > len(best):
                            best = candidate
                        break

        return best or text

    @staticmethod
    def _repair_json(raw: str) -> Optional[dict[str, Any]]:
        """
        Multi-step JSON repair. Returns parsed dict or None if all steps fail.

        Step 1: Strip think tags + preprocess K2 literals
        Step 2: Extract the JSON block
        Step 3: Fast-path stdlib json.loads
        Step 4: json-repair library  (handles most real-world malformed JSON)
        Step 5: Manual trailing-comma + bracket-balance fix → json.loads
        """
        # Step 1
        text = K2Client.strip_think_tags(raw)
        text = K2Client._preprocess(text)

        # Step 2
        text = K2Client._extract_json_block(text)

        # Step 3: fast path
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        # Step 4: json-repair (most powerful, handles unquoted keys, truncation, etc.)
        try:
            repaired = repair_json(text, return_objects=True, ensure_ascii=False)
            if isinstance(repaired, dict) and repaired:
                return repaired
        except Exception as e:
            logger.debug(f'json-repair failed: {e}')

        # Step 5: manual trailing-comma + bracket balance → re-parse
        text = re.sub(r',\s*([}\]])', r'\1', text)
        open_b = text.count('[') - text.count(']')
        open_c = text.count('{') - text.count('}')
        if open_b > 0:
            text += ']' * open_b
        if open_c > 0:
            text += '}' * open_c
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError as e:
            logger.warning(f'JSON repair failed after all steps: {e}')
            return None

    # ------------------------------------------------------------------ #
    # Core call methods
    # ------------------------------------------------------------------ #
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        timeout: float = 90.0,
    ) -> str:
        """Standard (non-streaming) K2 call. Returns stripped text content."""
        await self._check_rate_limit()

        response = await self.client.chat.completions.create(
            model=settings.k2_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
            timeout=timeout,
        )

        raw = response.choices[0].message.content or ""
        return self.strip_think_tags(raw)

    async def call_and_parse_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        timeout: float = 90.0,
        demo_fallback: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Call K2 and parse the JSON response.
        If repair pipeline fails, attempts a second 'fix my JSON' call.
        If that also fails and demo_fallback is provided, returns fallback silently.
        """
        await self._check_rate_limit()

        raw = await self.client.chat.completions.create(
            model=settings.k2_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
            timeout=timeout,
        )

        raw_text = raw.choices[0].message.content or ""
        result = self._repair_json(raw_text)
        if result is not None:
            return result

        # Second attempt: ask K2 to fix its own output
        logger.warning("First JSON parse failed — attempting K2 self-repair call")

        stripped = self.strip_think_tags(raw_text)
        fix_prompt = (
            "The following is malformed JSON. Fix it and return ONLY valid JSON "
            "with no explanation or markdown:\n\n"
            f"{stripped[:4000]}"
        )

        try:
            await self._check_rate_limit()

            fix_response = await self.client.chat.completions.create(
                model=settings.k2_model,
                messages=[{"role": "user", "content": fix_prompt}],
                max_tokens=2048,
                extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
                timeout=30.0,
            )

            fix_text = fix_response.choices[0].message.content or ""
            result = self._repair_json(fix_text)
            if result is not None:
                return result

        except Exception as e:
            logger.error(f"K2 self-repair call failed: {e}")

        # Final fallback: return demo result silently if available
        if demo_fallback is not None:
            logger.warning("All JSON repair steps failed — returning demo fallback")
            return demo_fallback

        raise ValueError(
            "K2 returned output that could not be parsed after all repair steps"
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 16384,
        timeout: float = 120.0,
    ) -> AsyncIterator[str]:
        """
        Streaming call.
        Yields tokens (optionally including think content),
        then yields '---RESULT---' followed by the full raw output at the end.
        """
        await self._check_rate_limit()

        full_chunks: list[str] = []
        in_think = False

        stream_resp = await self.client.chat.completions.create(
            model=settings.k2_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            stream=True,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
            timeout=timeout,
        )

        async for chunk in stream_resp:
            token = chunk.choices[0].delta.content or ""
            if not token:
                continue

            full_chunks.append(token)

            # Update think state based on the running full text (safer than buffer-join)
            running = "".join(full_chunks[-20:])  # small tail window is enough
            if "<think>" in running:
                in_think = True
            if "</think>" in running:
                in_think = False

            # If you want to show "reasoning" tokens only when in_think:
            # yield token if in_think else nothing
            # Here I'll keep your intent: yield non-JSON fragments while streaming.
            if not in_think:
                s = token.strip()
                if s and not s.startswith(("{", "[")):
                    yield token

        full_text = "".join(full_chunks)
        yield "---RESULT---"
        yield full_text

    async def check_reachable(self) -> bool:
        """Quick connectivity check for the model endpoint."""
        try:
            await self._check_rate_limit()

            response = await self.client.chat.completions.create(
                model=settings.k2_model,
                messages=[{"role": "user", "content": "Reply with the word OK only."}],
                max_tokens=10,
                timeout=15.0,
            )
            return bool(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"K2 reachability check failed: {e!r}")
            return False


# Singleton instance
k2_client = K2Client()