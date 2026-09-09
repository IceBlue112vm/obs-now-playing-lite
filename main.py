import asyncio

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


async def main():
    manager = await MediaManager.request_async()
    session = manager.get_current_session()

    if session is None:
        print("No active media session.")
        return

    media_properties = await session.try_get_media_properties_async()

    print(f"Title: {media_properties.title}")
    print(f"Artist: {media_properties.artist}")


if __name__ == "__main__":
    asyncio.run(main())
