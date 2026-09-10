import obsws_python as obs


OBS_HOST = "localhost"
OBS_PORT = 4455

TITLE_SOURCE = "NowPlayingTitle"
ARTIST_SOURCE = "NowPlayingArtist"
TEXT_SOURCES = (
    TITLE_SOURCE,
    ARTIST_SOURCE,
)

DEFAULT_TEXT_ALIGNMENT = "left"

RIGHT_MARGIN = 20
BOTTOM_MARGIN = 20
LINE_GAP = 5

MAX_TEXT_WIDTH_RATIO = 0.60
ELLIPSIS = "..."

SCENE_ITEM_ALIGNMENT_TOP_LEFT = 5

DEFAULT_OUTLINE_ENABLED = True
DEFAULT_OUTLINE_SIZE = 3
DEFAULT_OUTLINE_COLOR = 0x000000
DEFAULT_OUTLINE_OPACITY = 100


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

    def get_canvas_size(self):
        response = self.client.get_video_settings()

        return (
            response.base_width,
            response.base_height,
        )

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

        # Title / Artist Source 준비
        self.ensure_text_sources_in_scene(
            scene_name
        )

        # Overlay가 하나의 오브젝트처럼 동작하도록
        # Scene Item scale을 동일하게 유지
        self.normalize_overlay_scale(
            scene_name
        )

        # Text Source 내부 정렬은 좌측으로 통일
        self.set_text_alignment()

        # 기본 Outline 적용
        self.set_text_outline()

        # 두 Source 모두 표시
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

    def set_text_alignment(
        self,
        alignment=DEFAULT_TEXT_ALIGNMENT,
    ):
        for source_name in TEXT_SOURCES:
            self.client.set_input_settings(
                source_name,
                {"align": alignment},
                True,
            )

    def normalize_source_scale(
        self,
        scene_name,
        source_name,
    ):
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        if scene_item_id is None:
            return

        self.client.set_scene_item_transform(
            scene_name,
            scene_item_id,
            {
                "scaleX": 1.0,
                "scaleY": 1.0,
            },
        )

    def normalize_overlay_scale(
        self,
        scene_name,
    ):
        for source_name in TEXT_SOURCES:
            self.normalize_source_scale(
                scene_name,
                source_name,
            )

    def set_text_outline(self):
        settings = {
            "outline": DEFAULT_OUTLINE_ENABLED,
            "outline_size": DEFAULT_OUTLINE_SIZE,
            "outline_color": DEFAULT_OUTLINE_COLOR,
            "outline_opacity": DEFAULT_OUTLINE_OPACITY,
        }

        for source_name in TEXT_SOURCES:
            self.client.set_input_settings(
                source_name,
                settings,
                True,
            )

    # ------------------------------------------------------------------
    # Overlay layout
    # ------------------------------------------------------------------

    def get_source_text(self, source_name):
        response = self.client.get_input_settings(
            source_name
        )

        return response.input_settings.get(
            "text",
            "",
        )

    def get_source_size(
        self,
        scene_name,
        source_name,
    ):
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        if scene_item_id is None:
            return None

        response = self.client.get_scene_item_transform(
            scene_name,
            scene_item_id,
        )

        transform = response.scene_item_transform

        return (
            transform["sourceWidth"],
            transform["sourceHeight"],
        )

    def set_source_position(
        self,
        scene_name,
        source_name,
        x,
        y,
    ):
        scene_item_id = self.get_scene_item_id(
            scene_name,
            source_name,
        )

        if scene_item_id is None:
            return

        self.client.set_scene_item_transform(
            scene_name,
            scene_item_id,
            {
                "positionX": x,
                "positionY": y,
                "alignment": SCENE_ITEM_ALIGNMENT_TOP_LEFT,
            },
        )

    def layout_overlay(self):
        if self.target_scene is None:
            return

        scene_name = self.target_scene

        canvas_width, canvas_height = (
            self.get_canvas_size()
        )

        title_size = self.get_source_size(
            scene_name,
            TITLE_SOURCE,
        )

        artist_size = self.get_source_size(
            scene_name,
            ARTIST_SOURCE,
        )

        if (
            title_size is None
            or artist_size is None
        ):
            return

        title_width, title_height = title_size
        artist_width, artist_height = artist_size

        # 둘 중 더 긴 문자열을 전체 Overlay 폭으로 사용
        block_width = max(
            title_width,
            artist_width,
        )

        # 전체 Overlay의 왼쪽 시작점
        left = (
            canvas_width
            - RIGHT_MARGIN
            - block_width
        )

        # 아래에서부터 Artist 배치
        artist_y = (
            canvas_height
            - BOTTOM_MARGIN
            - artist_height
        )

        # Artist 위에 일정한 간격을 두고 Title 배치
        title_y = (
            artist_y
            - LINE_GAP
            - title_height
        )

        # 두 Source의 왼쪽 시작점을 동일하게 맞춤
        self.set_source_position(
            scene_name,
            TITLE_SOURCE,
            left,
            title_y,
        )

        self.set_source_position(
            scene_name,
            ARTIST_SOURCE,
            left,
            artist_y,
        )

    def get_max_text_width(self):
        canvas_width, _ = self.get_canvas_size()

        return (
                canvas_width * MAX_TEXT_WIDTH_RATIO
                - RIGHT_MARGIN
        )

    def fit_source_text(
            self,
            scene_name,
            source_name,
    ):
        source_size = self.get_source_size(
            scene_name,
            source_name,
        )

        if source_size is None:
            return False

        source_width, _ = source_size
        max_width = self.get_max_text_width()

        # 이미 허용 범위 안이면 그대로 사용
        if source_width <= max_width:
            return False

        text = self.get_source_text(
            source_name
        )

        if not text:
            return False

        # 이전 단계에서 붙인 ...은 글자 수 계산에서 제외
        if text.endswith(ELLIPSIS):
            content = text[:-len(ELLIPSIS)]
        else:
            content = text

        if len(content) <= 1:
            return False

        # 현재 실제 폭을 이용해서
        # 대략 몇 글자까지 들어갈지 계산
        ratio = max_width / source_width

        keep_length = max(
            1,
            int(len(content) * ratio) - 1,
        )

        shortened = (
                content[:keep_length].rstrip()
                + ELLIPSIS
        )

        # 반드시 이전 문자열보다 짧아지도록 보장
        if shortened == text:
            shortened = (
                    content[:-1].rstrip()
                    + ELLIPSIS
            )

        self.client.set_input_settings(
            source_name,
            {"text": shortened},
            True,
        )

        return True

    def fit_overlay_texts(self):
        if self.target_scene is None:
            return False

        text_changed = False

        for source_name in TEXT_SOURCES:
            if self.fit_source_text(
                self.target_scene,
                source_name,
            ):
                text_changed = True

        return text_changed
