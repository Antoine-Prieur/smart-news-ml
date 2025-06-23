import asyncio

from src.setup import MLPlatformSetup


async def main() -> None:
    ml_platform = MLPlatformSetup()
    await ml_platform.setup()


if __name__ == "__main__":
    asyncio.run(main())
