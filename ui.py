import sys
from pathlib import Path

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from media import create_media_manager, get_current_media
from obs_controller import OBSController
from settings import load_settings, save_settings


APP_VERSION = "0.2.0-dev"
APP_AUTHOR = "77ㅑ르륵"

WINDOW_SIZE = "440x650"

MEDIA_POLL_INTERVAL_SEC = 1
QUEUE_POLL_INTERVAL_MS = 100

MANUAL_UPDATE_DELAY_MS = 500
FONT_SIZE_UPDATE_DELAY_MS = 300
OVERLAY_LAYOUT_DELAY_MS = 30
AUTO_CONNECT_DELAY_MS = 200

DEFAULT_FONT_SIZE = 32
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 500

BG_COLOR = "#F4F2EE"
CARD_COLOR = "#FCFBF9"
TEXT_COLOR = "#2F2F2F"
SUBTEXT_COLOR = "#77736E"
BORDER_COLOR = "#DDD8D1"
ACCENT_COLOR = "#8A5F3D"
ACCENT_HOVER_COLOR = "#765034"
ACCENT_PRESSED_COLOR = "#68442F"
ACCENT_TEXT_COLOR = "#FFFDF9"

def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("OBS Now Playing Lite")
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        self.root.iconbitmap(
            str(resource_path("assets/OBSNowPlayingLite.ico"))
        )

        # Saved settings
        saved_settings = load_settings()

        saved_font_size = saved_settings.get(
            "font_size",
            DEFAULT_FONT_SIZE,
        )
        saved_font_size = max(
            MIN_FONT_SIZE,
            min(saved_font_size, MAX_FONT_SIZE),
        )

        self.saved_password = saved_settings.get(
            "password",
            "",
        )

        # Application state
        self.obs_controller = None
        self.current_media = None
        self.is_active = False

        # UI variables
        self.title_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.font_size_var = tk.StringVar(
            value=str(saved_font_size)
        )

        self.last_valid_font_size = saved_font_size

        # UI update state
        self.is_auto_updating = False
        self.manual_update_job = None
        self.font_size_update_job = None
        self.overlay_layout_job = None

        # Background media worker
        self.media_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.create_widgets()
        self.restore_password_field()
        self.bind_variable_changes()
        self.start_media_worker()

        self.root.after(
            QUEUE_POLL_INTERVAL_MS,
            self.process_media_queue,
        )

        if self.saved_password:
            self.root.after(
                AUTO_CONNECT_DELAY_MS,
                self.auto_connect_obs,
            )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

    # ------------------------------------------------------------------
    # UI creation
    # ------------------------------------------------------------------

    def create_widgets(self):
        self.configure_styles()

        main_frame = ttk.Frame(
            self.root,
            padding=(20, 18),
        )
        main_frame.pack(
            fill="both",
            expand=True,
        )

        self.create_header(main_frame)
        self.create_connection_section(main_frame)
        self.create_media_section(main_frame)
        self.create_control_section(main_frame)
        self.create_footer(main_frame)

    def configure_styles(self):
        style = ttk.Style()

        # Makes custom colors more consistently visible on Windows.
        style.theme_use("clam")

        self.root.configure(
            bg=BG_COLOR,
        )

        style.configure(
            "TFrame",
            background=BG_COLOR,
        )

        style.configure(
            "Card.TFrame",
            background=CARD_COLOR,
        )

        style.configure(
            "TLabel",
            background=BG_COLOR,
            foreground=TEXT_COLOR,
            font=("Malgun Gothic", 10),
        )

        style.configure(
            "Title.TLabel",
            background=BG_COLOR,
            foreground=TEXT_COLOR,
            font=("Malgun Gothic", 16, "bold"),
        )

        style.configure(
            "Subtitle.TLabel",
            background=BG_COLOR,
            foreground=SUBTEXT_COLOR,
            font=("Malgun Gothic", 10),
        )

        style.configure(
            "Section.TLabelframe",
            background=CARD_COLOR,
            bordercolor=BORDER_COLOR,
            relief="solid",
            padding=12,
        )

        style.configure(
            "Section.TLabelframe.Label",
            background=CARD_COLOR,
            foreground=TEXT_COLOR,
            font=("Malgun Gothic", 11, "bold"),
        )

        style.configure(
            "Card.TLabel",
            background=CARD_COLOR,
            foreground=TEXT_COLOR,
            font=("Malgun Gothic", 10),
        )

        style.configure(
            "Status.TLabel",
            background=CARD_COLOR,
            foreground=SUBTEXT_COLOR,
            font=("Malgun Gothic", 10),
        )

        style.configure(
            "TEntry",
            fieldbackground="#FFFFFF",
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            padding=5,
        )

        style.configure(
            "TSpinbox",
            fieldbackground="#FFFFFF",
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            padding=4,
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT_COLOR,
            foreground=ACCENT_TEXT_COLOR,
            bordercolor=ACCENT_COLOR,
            font=("Malgun Gothic", 10, "bold"),
            padding=(10, 7),
        )

        style.map(
            "Accent.TButton",
            background=[
                ("disabled", "#D8D1CB"),
                ("pressed", ACCENT_PRESSED_COLOR),
                ("active", ACCENT_HOVER_COLOR),
            ],
            foreground=[
                ("disabled", "#9B938D"),
            ],
        )

    def create_header(self, parent):
        header = ttk.Frame(parent)
        header.pack(
            fill="x",
            pady=(0, 18),
        )

        ttk.Label(
            header,
            text="OBS Now Playing Lite",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="현재 재생 중인 미디어 정보를 OBS에 자동으로 표시합니다.",
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(3, 0),
        )

    def create_connection_section(self, parent):
        section = ttk.LabelFrame(
            parent,
            text=" OBS 연결",
            style="Section.TLabelframe",
        )
        section.pack(
            fill="x",
            pady=(0, 12),
        )

        section.columnconfigure(0, weight=1)

        ttk.Label(
            section,
            text="WebSocket 비밀번호",
            style="Card.TLabel",
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.password_entry = ttk.Entry(
            section,
            show="*",
        )
        self.password_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 8),
        )

        self.connect_button = ttk.Button(
            section,
            text="연결",
            command=self.connect_obs,
            width=9,
        )
        self.connect_button.grid(
            row=1,
            column=1,
            padx=(8, 0),
            pady=(5, 8),
        )

        status_frame = ttk.Frame(
            section,
            style="Card.TFrame",
        )
        status_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.obs_status_dot = tk.Canvas(
            status_frame,
            width=10,
            height=10,
            bg=CARD_COLOR,
            highlightthickness=0,
            bd=0,
        )

        self.obs_status_dot.pack(
            side="left",
            padx=(0, 6),
        )

        self.obs_status_circle = self.obs_status_dot.create_oval(
            2,
            2,
            8,
            8,
            fill="#999999",
            outline="",
        )

        self.obs_status_label = ttk.Label(
            status_frame,
            text="연결되지 않음",
            style="Status.TLabel",
        )
        self.obs_status_label.pack(side="left")

    def create_media_section(self, parent):
        section = ttk.LabelFrame(
            parent,
            text=" 현재 재생 정보",
            style="Section.TLabelframe",
        )
        section.pack(
            fill="x",
            pady=(0, 12),
        )

        section.columnconfigure(0, weight=1)

        ttk.Label(
            section,
            text="제목",
            style="Card.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.title_entry = ttk.Entry(
            section,
            textvariable=self.title_var,
        )
        self.title_entry.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(5, 10),
        )

        ttk.Label(
            section,
            text="아티스트",
            style="Card.TLabel",
        ).grid(
            row=2,
            column=0,
            sticky="w",
        )

        self.artist_entry = ttk.Entry(
            section,
            textvariable=self.artist_var,
        )
        self.artist_entry.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(5, 25),
        )

        ttk.Label(
            section,
            text="폰트 크기",
            style="Card.TLabel",
        ).grid(
            row=4,
            column=0,
            sticky="w",
        )

        self.font_size_spinbox = ttk.Spinbox(
            section,
            from_=MIN_FONT_SIZE,
            to=MAX_FONT_SIZE,
            textvariable=self.font_size_var,
            width=6,
        )
        self.font_size_spinbox.grid(
            row=4,
            column=1,
            sticky="e",
        )

        self.font_size_spinbox.bind(
            "<FocusOut>",
            self.clamp_font_size,
        )

        self.font_size_spinbox.bind(
            "<Return>",
            self.clamp_font_size,
        )

    def create_control_section(self, parent):
        section = ttk.LabelFrame(
            parent,
            text=" 표시 제어",
            style="Section.TLabelframe",
        )
        section.pack(
            fill="x",
            pady=(0, 12),
        )

        self.target_label = ttk.Label(
            section,
            text="대상 장면: -",
            style="Card.TLabel",
        )
        self.target_label.pack(
            fill="x",
            anchor="w",
        )

        self.toggle_button = ttk.Button(
            section,
            text="표시 시작",
            command=self.toggle_active,
            state="disabled",
            style="Accent.TButton",
        )
        self.toggle_button.pack(
            fill="x",
            pady=(12, 0),
        )

    def create_footer(self, parent):
        style = ttk.Style()
        style.configure(
            "Footer.TLabel",
            foreground="#999999",
            font=("Segoe", 9),
        )

        ttk.Label(
            parent,
            text=f"v{APP_VERSION} · by {APP_AUTHOR}",
            style="Footer.TLabel",
        ).pack(
            side="bottom",
            anchor="e",
        )

    def bind_variable_changes(self):
        self.title_var.trace_add(
            "write",
            self.schedule_manual_update,
        )

        self.artist_var.trace_add(
            "write",
            self.schedule_manual_update,
        )

        self.font_size_var.trace_add(
            "write",
            self.schedule_font_size_update,
        )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def restore_password_field(self):
        if not self.saved_password:
            return

        self.password_entry.insert(
            0,
            self.saved_password,
        )

    def save_current_settings(
        self,
        font_size=None,
        show_error=True,
    ):
        if font_size is None:
            font_size = self.get_font_size()

        if font_size is None:
            font_size = self.last_valid_font_size

        try:
            save_settings(
                font_size,
                self.saved_password,
            )

        except Exception as error:
            if show_error:
                messagebox.showerror(
                    "설정 오류",
                    (
                        "설정을 저장하지 못했습니다.\n\n"
                        f"{error}"
                    ),
                )

    # ------------------------------------------------------------------
    # OBS connection
    # ------------------------------------------------------------------

    def auto_connect_obs(self):
        if not self.saved_password:
            return

        self.connect_obs()

    def connect_obs(self):
        password = self.password_entry.get()

        try:
            obs_controller = OBSController(
                password
            )

        except Exception as error:
            self.obs_controller = None
            self.set_obs_disconnected()
            self.show_obs_connection_error(
                error
            )
            return

        self.obs_controller = obs_controller

        # 연결이 실제로 성공한 비밀번호만 저장
        self.saved_password = password

        self.set_obs_connected()
        self.save_current_settings()

    def set_obs_connected(self):
        self.obs_status_dot.itemconfig(
            self.obs_status_circle,
            fill="#4CAF50",
        )

        self.obs_status_label.config(
            text="연결됨"
        )

        self.connect_button.config(
            text="연결됨",
            state="disabled",
        )

        self.password_entry.config(
            state="disabled",
        )

        self.toggle_button.config(
            state="normal",
        )

    def set_obs_disconnected(self):
        self.obs_status_dot.itemconfig(
            self.obs_status_circle,
            fill="#E57373",
        )

        self.obs_status_label.config(
            text="연결 실패"
        )

        self.connect_button.config(
            text="연결",
            state="normal",
        )

        self.password_entry.config(
            state="normal",
        )

        self.toggle_button.config(
            state="disabled",
        )

    def show_obs_connection_error(self, error):
        error_text = str(error).lower()
        winerror = getattr(
            error,
            "winerror",
            None,
        )

        if (
            winerror == 10061
            or "actively refused" in error_text
            or "connection refused" in error_text
            or "timed out" in error_text
            or "failed to establish" in error_text
        ):
            message = (
                "OBS에 연결할 수 없습니다.\n\n"
                "OBS가 실행 중인지 확인하고,\n"
                "도구 → WebSocket 서버 설정에서 "
                "WebSocket 서버가 활성화되어 있는지 확인해주세요."
            )

        elif (
            "authentication" in error_text
            or "identified" in error_text
            or "identify client" in error_text
            or "password" in error_text
        ):
            message = (
                "OBS WebSocket 비밀번호가 올바르지 않습니다.\n\n"
                "OBS의 WebSocket 서버 설정에서 "
                "비밀번호를 다시 확인해주세요."
            )

        else:
            message = (
                "OBS 연결 중 알 수 없는 오류가 발생했습니다.\n\n"
                f"{error}"
            )

        messagebox.showerror(
            "OBS 연결 실패",
            message,
        )

    # ------------------------------------------------------------------
    # ON / OFF
    # ------------------------------------------------------------------

    def toggle_active(self):
        if self.obs_controller is None:
            return

        try:
            if self.is_active:
                self.deactivate()
            else:
                self.activate()

        except Exception as error:
            messagebox.showerror(
                "OBS 오류",
                str(error),
            )

    def activate(self):
        scene_name = (
            self.obs_controller
            .activate_current_scene()
        )

        font_size = self.get_font_size()

        if font_size is not None:
            self.obs_controller.set_font_size(
                font_size
            )

        if self.current_media is not None:
            self.obs_controller.update_media(
                self.current_media
            )

        self.is_active = True

        self.target_label.config(
            text=f"대상 장면: {scene_name}"
        )

        self.toggle_button.config(
            text="표시 끄기"
        )

        self.schedule_overlay_layout()

    def deactivate(self):
        self.cancel_overlay_layout()

        self.obs_controller.deactivate_target_scene()

        self.is_active = False

        self.target_label.config(
            text="대상 장면: -"
        )

        self.toggle_button.config(
            text="표시 시작"
        )

    # ------------------------------------------------------------------
    # Media worker
    # ------------------------------------------------------------------

    def start_media_worker(self):
        thread = threading.Thread(
            target=self.run_media_worker,
            daemon=True,
        )

        thread.start()

    def run_media_worker(self):
        asyncio.run(
            self.media_worker()
        )

    async def media_worker(self):
        manager = await create_media_manager()
        previous_media = object()

        while not self.stop_event.is_set():
            current_media = await get_current_media(
                manager
            )

            if current_media != previous_media:
                self.media_queue.put(
                    current_media
                )

                previous_media = current_media

            await asyncio.sleep(
                MEDIA_POLL_INTERVAL_SEC
            )

    def process_media_queue(self):
        try:
            while True:
                media = self.media_queue.get_nowait()

                self.handle_detected_media(
                    media
                )

        except queue.Empty:
            pass

        self.root.after(
            QUEUE_POLL_INTERVAL_MS,
            self.process_media_queue,
        )

    def handle_detected_media(self, media):
        self.cancel_manual_update()

        self.current_media = media

        if media is None:
            title = "-"
            artist = "-"
        else:
            title, artist = media

        self.set_media_fields(
            title,
            artist,
        )

        self.update_obs_if_active(
            media
        )

    def set_media_fields(
        self,
        title,
        artist,
    ):
        self.is_auto_updating = True

        try:
            self.title_var.set(
                title
            )

            self.artist_var.set(
                artist
            )

        finally:
            self.is_auto_updating = False

    # ------------------------------------------------------------------
    # Manual media editing
    # ------------------------------------------------------------------

    def schedule_manual_update(self, *args):
        if self.is_auto_updating:
            return

        self.cancel_manual_update()

        self.manual_update_job = self.root.after(
            MANUAL_UPDATE_DELAY_MS,
            self.apply_manual_update,
        )

    def cancel_manual_update(self):
        if self.manual_update_job is None:
            return

        self.root.after_cancel(
            self.manual_update_job
        )

        self.manual_update_job = None

    def apply_manual_update(self):
        self.manual_update_job = None

        media = (
            self.title_var.get().strip(),
            self.artist_var.get().strip(),
        )

        self.current_media = media

        self.update_obs_if_active(
            media
        )

    # ------------------------------------------------------------------
    # Font size
    # ------------------------------------------------------------------

    def schedule_font_size_update(self, *args):
        self.cancel_font_size_update()

        self.font_size_update_job = self.root.after(
            FONT_SIZE_UPDATE_DELAY_MS,
            self.apply_font_size,
        )

    def cancel_font_size_update(self):
        if self.font_size_update_job is None:
            return

        self.root.after_cancel(
            self.font_size_update_job
        )

        self.font_size_update_job = None

    def clamp_font_size(self, event=None):
        try:
            font_size = int(
                self.font_size_var.get()
            )

        except ValueError:
            font_size = (
                self.last_valid_font_size
            )

        font_size = max(
            MIN_FONT_SIZE,
            min(
                font_size,
                MAX_FONT_SIZE,
            ),
        )

        self.last_valid_font_size = font_size

        if (
            self.font_size_var.get()
            != str(font_size)
        ):
            self.font_size_var.set(
                str(font_size)
            )

    def get_font_size(self):
        try:
            font_size = int(
                self.font_size_var.get()
            )

        except ValueError:
            return None

        if not (
            MIN_FONT_SIZE
            <= font_size
            <= MAX_FONT_SIZE
        ):
            return None

        self.last_valid_font_size = font_size

        return font_size

    def apply_font_size(self):
        self.font_size_update_job = None

        font_size = self.get_font_size()

        if font_size is None:
            return

        # OBS가 꺼져 있거나 Overlay가 OFF여도
        # 사용자가 선택한 Font Size는 저장
        self.save_current_settings(
            font_size
        )

        if not self.is_active:
            return

        if self.obs_controller is None:
            return

        try:
            self.obs_controller.set_font_size(
                font_size
            )

            # Font Size가 작아졌을 때 잘렸던 문자열을
            # 원본으로 복구한 뒤 다시 길이를 검사
            self.obs_controller.update_media(
                self.current_media
            )

            self.schedule_overlay_layout()

        except Exception as error:
            messagebox.showerror(
                "OBS 오류",
                str(error),
            )

    # ------------------------------------------------------------------
    # Overlay layout
    # ------------------------------------------------------------------

    def schedule_overlay_layout(self):
        self.cancel_overlay_layout()

        self.overlay_layout_job = self.root.after(
            OVERLAY_LAYOUT_DELAY_MS,
            self.apply_overlay_layout,
        )

    def cancel_overlay_layout(self):
        if self.overlay_layout_job is None:
            return

        self.root.after_cancel(
            self.overlay_layout_job
        )

        self.overlay_layout_job = None

    def apply_overlay_layout(self):
        self.overlay_layout_job = None

        if (
            not self.is_active
            or self.obs_controller is None
        ):
            return

        try:
            text_changed = (
                self.obs_controller
                .fit_overlay_texts()
            )

            # ...으로 문자열을 변경했다면
            # OBS가 새 폭을 계산할 시간을 다시 기다림
            if text_changed:
                self.schedule_overlay_layout()
                return

            # 모두 60% 안에 들어왔을 때 최종 배치
            self.obs_controller.layout_overlay()

        except Exception as error:
            messagebox.showerror(
                "OBS 오류",
                str(error),
            )

    # ------------------------------------------------------------------
    # Common OBS update
    # ------------------------------------------------------------------

    def update_obs_if_active(
        self,
        media,
    ):
        if (
            not self.is_active
            or self.obs_controller is None
        ):
            return

        try:
            self.obs_controller.update_media(
                media
            )

            self.schedule_overlay_layout()

        except Exception as error:
            messagebox.showerror(
                "OBS 오류",
                str(error),
            )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def on_close(self):
        self.stop_event.set()

        # debounce가 실행되기 전에 프로그램을 종료해도
        # 마지막으로 입력한 정상 Font Size는 저장
        font_size = self.get_font_size()

        if font_size is None:
            font_size = (
                self.last_valid_font_size
            )

        self.save_current_settings(
            font_size,
            show_error=False,
        )

        self.cancel_manual_update()
        self.cancel_font_size_update()
        self.cancel_overlay_layout()

        if (
            self.is_active
            and self.obs_controller is not None
        ):
            try:
                self.obs_controller.deactivate_target_scene()

            except Exception:
                pass

        self.root.destroy()


def run_app():
    root = tk.Tk()
    App(root)
    root.mainloop()
