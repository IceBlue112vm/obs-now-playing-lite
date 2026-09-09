import asyncio

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


async def get_current_media(manager):
    session = manager.get_current_session()

    if session is None:
        return None

    media_properties = await session.try_get_media_properties_async()

    return media_properties.title, media_properties.artist


async def main():
    manager = await MediaManager.request_async()
    previous_media = None

    while True:
        current_media = await get_current_media(manager)

        if current_media != previous_media:
            if current_media is None:
                print("No active media session.")
            else:
                title, artist = current_media
                print(f"Title: {title}")
                print(f"Artist: {artist}")
                print()

            previous_media = current_media

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
