import asyncio

from media import create_media_manager, get_current_media
from obs_controller import OBSController


async def main():
    print("Application started.")

    password = input("OBS WebSocket password: ")

    print("Connecting to OBS...")

    obs_controller = OBSController(password)

    print("OBS connection established.")

    scene_name = obs_controller.get_current_scene_name()
    input_kind = obs_controller.setup_text_sources(scene_name)

    print("OBS connected.")
    print(f"Scene: {scene_name}")
    print(f"Text source: {input_kind}")

    media_manager = await create_media_manager()

    previous_media = object()

    while True:
        current_media = await get_current_media(media_manager)

        if current_media != previous_media:
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
