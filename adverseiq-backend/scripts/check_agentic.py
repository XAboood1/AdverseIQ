import asyncio
import logging
from app.core.k2_client import k2_build_client
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)

async def main():
    settings = get_settings()
    print("K2_BUILD_URL:", settings.k2_build_url)
    print("K2_BUILD_MODEL:", settings.k2_build_model)
    print("K2_API_KEY set:", bool(settings.k2_api_key))
    try:
        ok = await k2_build_client.check_reachable()
        print('agentic reachable:', ok)
    except Exception as e:
        print('agentic check raised:', repr(e))

if __name__ == '__main__':
    asyncio.run(main())
