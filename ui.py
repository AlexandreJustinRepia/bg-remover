import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import threading
import io
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

DnDWrapper = TkinterDnD.DnDWrapper if TkinterDnD is not None else object

from remover import remove_background


class BackgroundRemoverApp(ctk.CTk, DnDWrapper):

    def __init__(self):
        super().__init__()

        if TkinterDnD is not None:
            self.TkdndVersion = TkinterDnD._require(self)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Background Remover Pro")
        self.geometry("1180x760")
        self.minsize(860, 620)
        self.configure(fg_color="#0f141b")

        self.selected_image = None
        self.result_image = None
        self.processing = False
        self.progress_value = 0
        self.preview_layout = "wide"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_ui()
        self.enable_drag_drop()
        self.bind("<Configure>", self.handle_resize)

    def build_ui(self):
        header = ctk.CTkFrame(self, height=82, corner_radius=0, fg_color="#111923")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(header, text="Background Remover Pro", font=("Segoe UI", 26, "bold"), text_color="#f7fafc")
        title.grid(row=0, column=0, sticky="w", padx=(24, 10), pady=(16, 0))

        subtitle = ctk.CTkLabel(header, text="Drop an image, remove the background, save a clean PNG.", font=("Segoe UI", 13), text_color="#8ea0b5")
        subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 12))

        dev = ctk.CTkLabel(header, text="Developed by Alexandre Justin Repia", font=("Segoe UI", 13), text_color="#8ea0b5")
        dev.grid(row=0, column=1, rowspan=2, sticky="e", padx=24)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        self.body.grid_columnconfigure((0, 1), weight=1, uniform="preview")
        self.body.grid_rowconfigure(0, weight=1)

        self.left_panel, self.left_canvas = self.create_preview_panel(self.body, "Original Image", "Drop image here\nor click Browse Image", 0)
        self.right_panel, self.right_canvas = self.create_preview_panel(self.body, "Transparent Result", "Your finished preview appears here", 1)

        footer = ctk.CTkFrame(self, corner_radius=0, fg_color="#111923")
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=0)

        actions = ctk.CTkFrame(footer, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="ew", padx=18, pady=14)
        for column in range(4):
            actions.grid_columnconfigure(column, weight=1, uniform="actions")

        self.browse_btn = self.create_action_button(actions, "Browse Image", self.browse_image, 0, fg_color="#2f80ed", hover_color="#1f6fd6")
        self.remove_btn = self.create_action_button(actions, "Remove Background", self.remove_bg, 1, fg_color="#18a058", hover_color="#128048", state="disabled")
        self.save_btn = self.create_action_button(actions, "Save PNG", self.save_image, 2, state="disabled")
        self.batch_btn = self.create_action_button(actions, "Batch Process", None, 3, state="disabled")

        progress_area = ctk.CTkFrame(footer, fg_color="transparent")
        progress_area.grid(row=0, column=1, sticky="e", padx=(0, 22), pady=14)

        self.status_label = ctk.CTkLabel(progress_area, text="Ready", font=("Segoe UI", 13), text_color="#8ea0b5")
        self.status_label.grid(row=0, column=0, sticky="e", pady=(0, 8))

        self.progress = ctk.CTkProgressBar(progress_area, width=280, height=12, corner_radius=8, progress_color="#2f80ed", fg_color="#223040")
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

    def create_action_button(self, parent, text, command, column, fg_color="#293545", hover_color="#35465a", state="normal"):
        button = ctk.CTkButton(parent, text=text, height=42, corner_radius=8, font=("Segoe UI", 13, "bold"), fg_color=fg_color, hover_color=hover_color, command=command, state=state)
        button.grid(row=0, column=column, sticky="ew", padx=5)
        return button

    def create_preview_panel(self, parent, title, empty_text, column):
        panel = ctk.CTkFrame(parent, corner_radius=10, fg_color="#151d28", border_width=1, border_color="#253244")
        panel.grid(row=0, column=column, sticky="nsew", padx=(0, 9) if column == 0 else (9, 0))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text=title, font=("Segoe UI", 19, "bold"), text_color="#eef4fb").grid(row=0, column=0, sticky="w", padx=18, pady=(15, 7))

        canvas = ctk.CTkLabel(panel, text=empty_text, width=360, height=360, fg_color="#0d1219", corner_radius=8, font=("Segoe UI", 15), text_color="#6f8196")
        canvas.grid(row=1, column=0, sticky="nsew", padx=14, pady=(7, 14))
        return panel, canvas

    def enable_drag_drop(self):
        if DND_FILES is None:
            self.set_status("Ready - install tkinterdnd2 for drag and drop")
            return

        for widget in (self, self.left_panel, self.left_canvas):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.handle_drop)
            widget.dnd_bind("<<DragEnter>>", self.handle_drag_enter)
            widget.dnd_bind("<<DragLeave>>", self.handle_drag_leave)

    def handle_drag_enter(self, _event):
        self.left_panel.configure(border_color="#2f80ed", border_width=2)
        if not self.selected_image:
            self.left_canvas.configure(text="Release to load image")

    def handle_drag_leave(self, _event):
        self.left_panel.configure(border_color="#253244", border_width=1)
        if not self.selected_image:
            self.left_canvas.configure(text="Drop image here\nor click Browse Image")

    def handle_drop(self, event):
        self.left_panel.configure(border_color="#253244", border_width=1)
        files = self.tk.splitlist(event.data)
        if files:
            self.load_image(files[0])

    def handle_resize(self, event):
        if event.widget is not self:
            return
        target_layout = "stacked" if event.width < 980 else "wide"
        if target_layout != self.preview_layout:
            self.preview_layout = target_layout
            self.apply_preview_layout(target_layout)

    def apply_preview_layout(self, layout):
        self.left_panel.grid_forget()
        self.right_panel.grid_forget()
        if layout == "stacked":
            self.body.grid_columnconfigure(0, weight=1, uniform="")
            self.body.grid_columnconfigure(1, weight=0, uniform="")
            self.body.grid_rowconfigure((0, 1), weight=1, uniform="preview")
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 9))
            self.right_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(9, 0))
        else:
            self.body.grid_columnconfigure((0, 1), weight=1, uniform="preview")
            self.body.grid_rowconfigure(0, weight=1, uniform="")
            self.body.grid_rowconfigure(1, weight=0, uniform="")
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9), pady=0)
            self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(9, 0), pady=0)

    def set_status(self, text):
        self.status_label.configure(text=text)

    def animate_progress(self):
        if not self.processing:
            return
        self.progress_value += 0.018
        if self.progress_value > 0.92:
            self.progress_value = 0.28
        self.progress.set(self.progress_value)
        self.after(28, self.animate_progress)

    def browse_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if filename:
            self.load_image(filename)

    def load_image(self, filename):
        path = Path(filename)
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            self.set_status("Please choose a PNG, JPG, JPEG, or WEBP image")
            return
        try:
            img = Image.open(path)
        except Exception as e:
            self.set_status("Could not open image")
            print("ERROR:", e)
            return

        self.selected_image = str(path)
        preview = img.copy()
        preview.thumbnail((520, 520))
        ctk_img = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.left_canvas.configure(image=ctk_img, text="")
        self.left_canvas.image = ctk_img
        self.right_canvas.configure(image=None, text="Your finished preview appears here")
        self.right_canvas.image = None
        self.result_image = None
        self.remove_btn.configure(state="normal")
        self.save_btn.configure(state="disabled")
        self.set_status(f"Loaded {path.name}")
        self.progress.set(0)

    def remove_bg(self):
        if not self.selected_image:
            return
        self.remove_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.processing = True
        self.progress_value = 0.08
        self.progress.set(0)
        self.set_status("Removing background...")
        self.animate_progress()
        threading.Thread(target=self.process_image, daemon=True).start()

    def process_image(self):
        try:
            output = remove_background(self.selected_image)
            image = Image.open(io.BytesIO(output))
            self.result_image = image.copy()
            preview = image.copy()
            preview.thumbnail((520, 520))
            self.after(0, lambda: self.update_result(preview))
        except Exception as e:
            self.after(0, lambda: self.processing_failed(str(e)))

    def update_result(self, image):
        self.processing = False
        ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self.right_canvas.configure(image=ctk_img, text="")
        self.right_canvas.image = ctk_img
        self.progress.set(1)
        self.set_status("Background removed")
        self.browse_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.remove_btn.configure(state="normal")

    def processing_failed(self, message):
        self.processing = False
        self.progress.set(0)
        self.set_status("Could not process image")
        self.browse_btn.configure(state="normal")
        self.remove_btn.configure(state="normal")
        self.save_btn.configure(state="disabled")
        print("ERROR:", message)

    def save_image(self):
        if self.result_image is None:
            return
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if filename:
            self.result_image.save(filename)
            self.set_status("Saved PNG")


