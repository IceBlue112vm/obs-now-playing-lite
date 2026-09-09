import obsws_python as obs


OBS_HOST = "localhost"
OBS_PORT = 4455

TITLE_SOURCE = "NowPlayingTitle"
ARTIST_SOURCE = "NowPlayingArtist"


class OBSController:
    def __init__(self, password):
        self.client = obs.ReqClient(
            host=OBS_HOST,
            port=OBS_PORT,
            password=password,
            timeout=3,
        )

    def get_current_scene_name(self):
        response = self.client.get_current_program_scene()

        if hasattr(response, "scene_name"):
            return response.scene_name

        return response.current_program_scene_name

    def get_text_input_kind(self):
        input_kinds = self.client.get_input_kind_list(False).input_kinds

        for input_kind in input_kinds:
            if input_kind.startswith("text_gdiplus"):
                return input_kind

        raise RuntimeError(
            "OBS에서 Text (GDI+) 소스를 찾을 수 없습니다."
        )

    def create_text_source_if_missing(
        self,
        scene_name,
        source_name,
        input_kind,
    ):
        inputs = self.client.get_input_list().inputs
        input_names = {item["inputName"] for item in inputs}

        if source_name in input_names:
            return

        self.client.create_input(
            scene_name,
            source_name,
            input_kind,
            {"text": ""},
            True,
        )

        print(f"Created: {source_name}")

    def setup_text_sources(self, scene_name):
        input_kind = self.get_text_input_kind()

        self.create_text_source_if_missing(
            scene_name,
            TITLE_SOURCE,
            input_kind,
        )

        self.create_text_source_if_missing(
            scene_name,
            ARTIST_SOURCE,
            input_kind,
        )

        return input_kind

    def update_media(self, media):
        if media is None:
            title = ""
            artist = ""
        else:
            title, artist = media

        self.client.set_input_settings(
            TITLE_SOURCE,
            {"text": title},
            True,
        )

        self.client.set_input_settings(
            ARTIST_SOURCE,
            {"text": artist},
            True,
        )
