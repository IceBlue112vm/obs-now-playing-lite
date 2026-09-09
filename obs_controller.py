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

        self.target_scene = None

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

    def get_input_names(self):
        inputs = self.client.get_input_list().inputs
        return {item["inputName"] for item in inputs}

    def get_scene_item_id(self, scene_name, source_name):
        response = self.client.get_scene_item_list(scene_name)

        for item in response.scene_items:
            if item["sourceName"] == source_name:
                return item["sceneItemId"]

        return None

    def ensure_source_in_scene(
        self,
        scene_name,
        source_name,
        input_kind,
    ):
        # 이미 해당 Scene에 있으면 그대로 사용
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        if scene_item_id is not None:
            return scene_item_id

        # OBS 전체에도 Source 자체가 없으면 생성
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

        # Source는 있지만 현재 Scene에는 없으면 연결
        response = self.client.create_scene_item(
            scene_name,
            source_name,
            True,
        )

        return response.scene_item_id

    def activate_current_scene(self):
        scene_name = self.get_current_scene_name()

        # 다른 Scene이 이미 Target이면 먼저 비활성화
        if (
            self.target_scene is not None
            and self.target_scene != scene_name
        ):
            self.deactivate_target_scene()

        input_kind = self.get_text_input_kind()

        title_item_id = self.ensure_source_in_scene(
            scene_name,
            TITLE_SOURCE,
            input_kind,
        )

        artist_item_id = self.ensure_source_in_scene(
            scene_name,
            ARTIST_SOURCE,
            input_kind,
        )

        self.client.set_scene_item_enabled(
            scene_name,
            title_item_id,
            True,
        )

        self.client.set_scene_item_enabled(
            scene_name,
            artist_item_id,
            True,
        )

        self.target_scene = scene_name

        return scene_name

    def deactivate_target_scene(self):
        if self.target_scene is None:
            return

        for source_name in (TITLE_SOURCE, ARTIST_SOURCE):
            scene_item_id = self.get_scene_item_id(
                self.target_scene,
                source_name,
            )

            if scene_item_id is not None:
                self.client.set_scene_item_enabled(
                    self.target_scene,
                    scene_item_id,
                    False,
                )

        self.target_scene = None

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
