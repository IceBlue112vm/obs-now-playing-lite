from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


async def create_media_manager():
    return await MediaManager.request_async()


async def get_current_media(manager):
    session = manager.get_current_session()

    if session is None:
        return None

    media_properties = await session.try_get_media_properties_async()

    return media_properties.title, media_properties.artist
