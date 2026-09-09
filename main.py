import asyncio
import getpass

import obsws_python as obs
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


OBS_HOST = "localhost"
OBS_PORT = 4455

TITLE_SOURCE = "NowPlayingTitle"
ARTIST_SOURCE = "NowPlayingArtist"


async def get_current_media(manager):
    session = manager.get_current_session()

    if session is None:
        return None

    media_properties = await session.try_get_media_properties_async()

    return media_properties.title, media_properties.artist


def get_current_scene_name(client):
    response = client.get_current_program_scene()

    # 최신 OBS 응답
    if hasattr(response, "scene_name"):
        return response.scene_name

    # 이전 필드 호환
    return response.current_program_scene_name


def get_text_input_kind(client):
    input_kinds = client.get_input_kind_list(False).input_kinds

    for input_kind in input_kinds:
        if input_kind.startswith("text_gdiplus"):
            return input_kind

    raise RuntimeError("OBS에서 Text (GDI+) 소스를 찾을 수 없습니다.")


def create_text_source_if_missing(
    client,
    scene_name,
    source_name,
    input_kind,
):
    inputs = client.get_input_list().inputs
    input_names = {item["inputName"] for item in inputs}

    if source_name in input_names:
        return

    client.create_input(
        scene_name,
        source_name,
        input_kind,
        {"text": ""},
        True,
    )

    print(f"Created: {source_name}")


def update_obs_text(client, media):
    if media is None:
        title = ""
        artist = ""
    else:
        title, artist = media

    client.set_input_settings(
        TITLE_SOURCE,
        {"text": title},
        True,
    )

    client.set_input_settings(
        ARTIST_SOURCE,
        {"text": artist},
        True,
    )

async def main():
    print("Application started.")

    password = input("OBS WebSocket password: ")

    print("Connecting to OBS...")

    client = obs.ReqClient(
        host=OBS_HOST,
        port=OBS_PORT,
        password=password,
        timeout=3,
    )

    print("OBS connection established.")

    scene_name = get_current_scene_name(client)
    input_kind = get_text_input_kind(client)

    print("OBS connected.")
    print(f"Scene: {scene_name}")
    print(f"Text source: {input_kind}")

    create_text_source_if_missing(
        client,
        scene_name,
        TITLE_SOURCE,
        input_kind,
    )

    create_text_source_if_missing(
        client,
        scene_name,
        ARTIST_SOURCE,
        input_kind,
    )

    manager = await MediaManager.request_async()

    # 첫 실행 때 반드시 OBS 상태를 갱신하기 위한 sentinel
    previous_media = object()

    while True:
        current_media = await get_current_media(manager)

        if current_media != previous_media:
            update_obs_text(client, current_media)

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
