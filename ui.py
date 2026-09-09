import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from media import create_media_manager, get_current_media
from obs_controller import OBSController


MANUAL_UPDATE_DELAY_MS = 500


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("OBS Now Playing Lite")
        self.root.geometry("420x550")
        self.root.resizable(False, False)

        self.obs_controller = None
        self.current_media = None
        self.is_active = False

        self.title_var = tk.StringVar()
        self.artist_var = tk.StringVar()

        # 자동 감지값을 Entry에 넣을 때
        # 수동 수정으로 잘못 인식하지 않기 위한 플래그
        self.is_auto_updating = False

        # debounce용 예약 작업 ID
        self.manual_update_job = None

        self.media_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.create_widgets()

        # 사용자가 Entry 내용을 변경하면 호출
        self.title_var.trace_add(
            "write",
            self.schedule_manual_update,
        )
        self.artist_var.trace_add(
            "write",
            self.schedule_manual_update,
        )

        self.start_media_worker()

        self.root.after(100, self.process_media_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # OBS connection
        ttk.Label(
            main_frame,
            text="OBS WebSocket Password",
        ).pack(anchor="w")

        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=(5, 10))

        self.password_entry = ttk.Entry(
            password_frame,
            show="*",
        )
        self.password_entry.pack(
            side="left",
            fill="x",
            expand=True,
        )

        self.connect_button = ttk.Button(
            password_frame,
            text="Connect",
            command=self.connect_obs,
        )
        self.connect_button.pack(
            side="left",
            padx=(10, 0),
        )

        self.obs_status_label = ttk.Label(
            main_frame,
            text="OBS: Disconnected",
        )
        self.obs_status_label.pack(anchor="w")

        # Current media
        ttk.Separator(main_frame).pack(
            fill="x",
            pady=15,
        )

        ttk.Label(
            main_frame,
            text="Now Playing",
        ).pack(anchor="w")

        ttk.Label(
            main_frame,
            text="Title",
        ).pack(
            anchor="w",
            pady=(5, 0),
        )

        self.title_entry = ttk.Entry(
            main_frame,
            textvariable=self.title_var,
        )
        self.title_entry.pack(
            fill="x",
            pady=(2, 5),
        )

        ttk.Label(
            main_frame,
            text="Artist",
        ).pack(anchor="w")

        self.artist_entry = ttk.Entry(
            main_frame,
            textvariable=self.artist_var,
        )
        self.artist_entry.pack(
            fill="x",
            pady=(2, 5),
        )

        # Target scene
        self.target_label = ttk.Label(
            main_frame,
            text="Target Scene: -",
        )
        self.target_label.pack(
            anchor="w",
            pady=(10, 0),
        )

        # ON / OFF
        self.toggle_button = ttk.Button(
            main_frame,
            text="ON",
            command=self.toggle_active,
            state="disabled",
        )
        self.toggle_button.pack(
            fill="x",
            pady=(20, 0),
        )

    def connect_obs(self):
        password = self.password_entry.get()

        try:
            self.obs_controller = OBSController(password)

            self.obs_status_label.config(
                text="OBS: Connected"
            )
            self.connect_button.config(
                text="Connected",
                state="disabled",
            )
            self.password_entry.config(
                state="disabled",
            )
            self.toggle_button.config(
                state="normal",
            )

        except Exception as error:
            self.obs_controller = None

            self.obs_status_label.config(
                text="OBS: Connection failed"
            )

            messagebox.showerror(
                "OBS Connection Failed",
                str(error),
            )

    def toggle_active(self):
        if self.obs_controller is None:
            return

        try:
            if not self.is_active:
                scene_name = (
                    self.obs_controller.activate_current_scene()
                )

                if self.current_media is not None:
                    self.obs_controller.update_media(
                        self.current_media
                    )

                self.is_active = True

                self.target_label.config(
                    text=f"Target Scene: {scene_name}"
                )
                self.toggle_button.config(
                    text="OFF"
                )

            else:
                self.obs_controller.deactivate_target_scene()

                self.is_active = False

                self.target_label.config(
                    text="Target Scene: -"
                )
                self.toggle_button.config(
                    text="ON"
                )

        except Exception as error:
            messagebox.showerror(
                "OBS Error",
                str(error),
            )

    def start_media_worker(self):
        thread = threading.Thread(
            target=self.run_media_worker,
            daemon=True,
        )
        thread.start()

    def run_media_worker(self):
        asyncio.run(self.media_worker())

    async def media_worker(self):
        manager = await create_media_manager()
        previous_media = object()

        while not self.stop_event.is_set():
            current_media = await get_current_media(manager)

            if current_media != previous_media:
                self.media_queue.put(current_media)
                previous_media = current_media

            await asyncio.sleep(1)

    def process_media_queue(self):
        try:
            while True:
                media = self.media_queue.get_nowait()

                # 새 곡이 들어왔다면 대기 중인 수동 수정은 취소
                self.cancel_manual_update()

                self.current_media = media

                if media is None:
                    title = "-"
                    artist = "-"
                else:
                    title, artist = media

                # 자동 감지값을 Entry에 넣는 동안
                # trace callback을 무시
                self.is_auto_updating = True

                self.title_var.set(title)
                self.artist_var.set(artist)

                self.is_auto_updating = False

                if (
                    self.is_active
                    and self.obs_controller is not None
                ):
                    self.obs_controller.update_media(media)

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.process_media_queue,
        )

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

        title = self.title_var.get().strip()
        artist = self.artist_var.get().strip()

        self.current_media = (
            title,
            artist,
        )

        if (
            self.is_active
            and self.obs_controller is not None
        ):
            try:
                self.obs_controller.update_media(
                    self.current_media
                )

            except Exception as error:
                messagebox.showerror(
                    "OBS Error",
                    str(error),
                )

    def on_close(self):
        self.stop_event.set()

        self.cancel_manual_update()

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
