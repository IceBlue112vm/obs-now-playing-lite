import asyncio

from media import create_media_manager, get_current_media
from obs_controller import OBSController


async def main():
    print("Application started.")

    password = input("OBS WebSocket password: ")

    print("Connecting to OBS...")

    obs_controller = OBSController(password)

    print("OBS connection established.")

    media_manager = await create_media_manager()

    previous_media = object()

    while True:
        current_media = await get_current_media(media_manager)

        if current_media != previous_media:
            if obs_controller.target_scene is not None:
                obs_controller.update_media(current_media)

            if current_media is None:
                print("No active media session.")
            else:
                title, artist = current_media
                print()
                print(f"Title: {title}")
                print(f"Artist: {artist}")

            previous_media = current_media

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
