import obsws_python as obs


OBS_HOST = "localhost"
OBS_PORT = 4455

TITLE_SOURCE = "NowPlayingTitle"
ARTIST_SOURCE = "NowPlayingArtist"
TEXT_SOURCES = (TITLE_SOURCE, ARTIST_SOURCE)


class OBSController:
    def __init__(self, password):
        self.client = obs.ReqClient(
            host=OBS_HOST,
            port=OBS_PORT,
            password=password,
            timeout=3,
        )

        self.target_scene = None

    # ------------------------------------------------------------------
    # OBS information
    # ------------------------------------------------------------------

    def get_current_scene_name(self):
        response = self.client.get_current_program_scene()

        if hasattr(response, "scene_name"):
            return response.scene_name

        return response.current_program_scene_name

    def get_text_input_kind(self):
        input_kinds = (
            self.client
            .get_input_kind_list(False)
            .input_kinds
        )

        for input_kind in input_kinds:
            if input_kind.startswith("text_gdiplus"):
                return input_kind

        raise RuntimeError(
            "OBS에서 Text (GDI+) 소스를 찾을 수 없습니다."
        )

    def get_input_names(self):
        inputs = self.client.get_input_list().inputs

        return {
            item["inputName"]
            for item in inputs
        }

    def get_scene_item_id(
        self,
        scene_name,
        source_name,
    ):
        scene_items = (
            self.client
            .get_scene_item_list(scene_name)
            .scene_items
        )

        for item in scene_items:
            if item["sourceName"] == source_name:
                return item["sceneItemId"]

        return None

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    def ensure_source_in_scene(
        self,
        scene_name,
        source_name,
        input_kind,
    ):
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        # 이미 현재 Scene에 존재
        if scene_item_id is not None:
            return scene_item_id

        # OBS 전체에도 Source가 없으면 새로 생성
        if source_name not in self.get_input_names():
            response = self.client.create_input(
                scene_name,
                source_name,
                input_kind,
                {"text": ""},
                True,
            )

            print(f"Created: {source_name}")

            return response.scene_item_id

        # Source는 존재하지만 현재 Scene에는 없는 경우
        response = self.client.create_scene_item(
            scene_name,
            source_name,
            True,
        )

        return response.scene_item_id

    def ensure_text_sources_in_scene(
        self,
        scene_name,
    ):
        input_kind = self.get_text_input_kind()

        return {
            source_name: self.ensure_source_in_scene(
                scene_name,
                source_name,
                input_kind,
            )
            for source_name in TEXT_SOURCES
        }

    def set_source_enabled(
        self,
        scene_name,
        source_name,
        enabled,
    ):
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        if scene_item_id is None:
            return

        self.client.set_scene_item_enabled(
            scene_name,
            scene_item_id,
            enabled,
        )

    def set_text_sources_enabled(
        self,
        scene_name,
        enabled,
    ):
        for source_name in TEXT_SOURCES:
            self.set_source_enabled(
                scene_name,
                source_name,
                enabled,
            )

    # ------------------------------------------------------------------
    # Target Scene
    # ------------------------------------------------------------------

    def activate_current_scene(self):
        scene_name = self.get_current_scene_name()

        # 다른 Scene이 Target이면 먼저 숨김
        if (
            self.target_scene is not None
            and self.target_scene != scene_name
        ):
            self.deactivate_target_scene()

        self.ensure_text_sources_in_scene(
            scene_name
        )

        self.set_text_sources_enabled(
            scene_name,
            True,
        )

        self.target_scene = scene_name

        return scene_name

    def deactivate_target_scene(self):
        if self.target_scene is None:
            return

        self.set_text_sources_enabled(
            self.target_scene,
            False,
        )

        self.target_scene = None

    # ------------------------------------------------------------------
    # Media display
    # ------------------------------------------------------------------

    def update_media(self, media):
        if media is None:
            title = ""
            artist = ""
        else:
            title, artist = media

        values = {
            TITLE_SOURCE: title,
            ARTIST_SOURCE: artist,
        }

        for source_name, text in values.items():
            self.client.set_input_settings(
                source_name,
                {"text": text},
                True,
            )

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------

    def set_font_size(self, font_size):
        font_size = int(font_size)

        for source_name in TEXT_SOURCES:
            response = self.client.get_input_settings(
                source_name
            )

            settings = response.input_settings
            font = settings.get("font", {}).copy()

            font["size"] = font_size

            self.client.set_input_settings(
                source_name,
                {"font": font},
                True,
            )
