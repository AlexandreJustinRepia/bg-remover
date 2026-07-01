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


IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
CROP_PRESETS = {
    "Original size": None,
    "Square 512": (512, 512),
    "Square 1024": (1024, 1024),
    "Portrait 4:5": (1080, 1350),
    "Story 9:16": (1080, 1920),
    "Landscape 16:9": (1920, 1080),
    "Product 1:1": (1600, 1600),
}


class BackgroundRemoverApp(ctk.CTk, DnDWrapper):

    def __init__(self):
        super().__init__()

        if TkinterDnD is not None:
            self.TkdndVersion = TkinterDnD._require(self)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Background Remover Pro")
        self.geometry("1220x820")
        self.minsize(900, 680)
        self.configure(fg_color="#0f141b")

        self.selected_image = None
        self.image_queue = []
        self.result_image = None
        self.result_images = {}
        self.raw_result_images = {}
        self.current_result_path = None
        self.gallery_items = {}
        self.processing = False
        self.progress_value = 0
        self.preview_layout = "wide"
        self.crop_preset = ctk.StringVar(value="Original size")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_ui()
        self.enable_drag_drop()
        self.refresh_gallery()
        self.bind("<Configure>", self.handle_resize)

    def build_ui(self):
        header = ctk.CTkFrame(self, height=82, corner_radius=0, fg_color="#111923")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(header, text="Background Remover Pro", font=("Segoe UI", 26, "bold"), text_color="#f7fafc")
        title.grid(row=0, column=0, sticky="w", padx=(24, 10), pady=(16, 0))

        subtitle = ctk.CTkLabel(header, text="Drop one image or a whole batch, remove backgrounds, export fixed transparent sizes.", font=("Segoe UI", 13), text_color="#8ea0b5")
        subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 12))

        dev = ctk.CTkLabel(header, text="Developed by Alexandre Justin Repia", font=("Segoe UI", 13), text_color="#8ea0b5")
        dev.grid(row=0, column=1, rowspan=2, sticky="e", padx=24)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        self.body.grid_columnconfigure((0, 1), weight=1, uniform="preview")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_rowconfigure(1, weight=0)

        self.left_panel, self.left_canvas = self.create_preview_panel(self.body, "Original Image", "Drop images here\nor click Browse Image", 0)
        self.right_panel, self.right_canvas = self.create_preview_panel(self.body, "Transparent Result", "Your finished preview appears here", 1)
        self.create_batch_gallery()

        footer = ctk.CTkFrame(self, corner_radius=0, fg_color="#111923")
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=0)

        actions = ctk.CTkFrame(footer, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="ew", padx=18, pady=14)
        for column in range(6):
            actions.grid_columnconfigure(column, weight=1, uniform="actions")

        self.browse_btn = self.create_action_button(actions, "Browse Image", self.browse_image, 0, fg_color="#2f80ed", hover_color="#1f6fd6")
        self.batch_btn = self.create_action_button(actions, "Add Batch", self.browse_batch, 1)
        self.remove_btn = self.create_action_button(actions, "Remove BG", self.remove_bg, 2, fg_color="#18a058", hover_color="#128048", state="disabled")
        self.crop_menu = ctk.CTkOptionMenu(actions, values=list(CROP_PRESETS.keys()), variable=self.crop_preset, height=42, corner_radius=8, font=("Segoe UI", 13, "bold"), fg_color="#293545", button_color="#35465a", button_hover_color="#425873", command=self.apply_crop_to_current)
        self.crop_menu.grid(row=0, column=3, sticky="ew", padx=5)
        self.save_btn = self.create_action_button(actions, "Save PNG", self.save_image, 4, state="disabled")
        self.save_all_btn = self.create_action_button(actions, "Save All", self.save_all_images, 5, state="disabled")

        progress_area = ctk.CTkFrame(footer, fg_color="transparent")
        progress_area.grid(row=0, column=1, sticky="e", padx=(0, 22), pady=14)

        self.status_label = ctk.CTkLabel(progress_area, text="Ready", font=("Segoe UI", 13), text_color="#8ea0b5")
        self.status_label.grid(row=0, column=0, sticky="e", pady=(0, 8))

        self.progress = ctk.CTkProgressBar(progress_area, width=260, height=12, corner_radius=8, progress_color="#2f80ed", fg_color="#223040")
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

    def create_batch_gallery(self):
        self.gallery_panel = ctk.CTkFrame(self.body, height=130, corner_radius=10, fg_color="#151d28", border_width=1, border_color="#253244")
        self.gallery_panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.gallery_panel.grid_propagate(False)
        self.gallery_panel.grid_columnconfigure(0, weight=1)
        self.gallery_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.gallery_panel, text="Loaded Images", font=("Segoe UI", 15, "bold"), text_color="#eef4fb").grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self.gallery_list = ctk.CTkScrollableFrame(self.gallery_panel, fg_color="transparent", height=78)
        self.gallery_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.gallery_list.grid_columnconfigure(0, weight=1)

    def refresh_gallery(self):
        for item in self.gallery_items.values():
            item.destroy()
        self.gallery_items = {}

        if not self.image_queue:
            empty = ctk.CTkLabel(self.gallery_list, text="No images loaded", font=("Segoe UI", 13), text_color="#6f8196")
            empty.grid(row=0, column=0, sticky="w", padx=8, pady=6)
            self.gallery_items["__empty__"] = empty
            return

        for row, image_path in enumerate(self.image_queue):
            self.add_gallery_item(image_path, row)

    def add_gallery_item(self, image_path, row):
        status = "Ready" if image_path in self.result_images else "Queued"
        button = ctk.CTkButton(
            self.gallery_list,
            text=f"{row + 1}. {Path(image_path).name}    {status}",
            height=34,
            anchor="w",
            corner_radius=7,
            font=("Segoe UI", 13),
            fg_color=self.gallery_color(image_path),
            hover_color="#35465a",
            command=lambda path=image_path: self.select_image(path)
        )
        button.grid(row=row, column=0, sticky="ew", padx=4, pady=3)
        self.gallery_items[image_path] = button

    def gallery_color(self, image_path):
        if image_path == self.selected_image or image_path == self.current_result_path:
            return "#2f80ed"
        if image_path in self.result_images:
            return "#18a058"
        return "#293545"

    def update_gallery_item(self, image_path, status):
        item = self.gallery_items.get(image_path)
        if item is None or image_path not in self.image_queue:
            return
        item.configure(text=f"{self.image_queue.index(image_path) + 1}. {Path(image_path).name}    {status}", fg_color=self.gallery_color(image_path))

    def update_gallery_selection(self):
        for image_path, item in self.gallery_items.items():
            if image_path == "__empty__":
                continue
            status = "Ready" if image_path in self.result_images else "Queued"
            item.configure(text=f"{self.image_queue.index(image_path) + 1}. {Path(image_path).name}    {status}", fg_color=self.gallery_color(image_path))

    def select_image(self, image_path):
        if image_path not in self.image_queue:
            return

        self.selected_image = image_path
        self.show_original_preview(Path(image_path))

        if image_path in self.result_images:
            self.current_result_path = image_path
            self.result_image = self.result_images[image_path]
            self.show_result_preview(self.result_image)
            self.save_btn.configure(state="normal")
            self.set_status(f"Viewing {Path(image_path).name}")
        else:
            self.result_image = None
            self.right_canvas.configure(image=None, text="Output not ready yet")
            self.right_canvas.image = None
            self.save_btn.configure(state="disabled")
            self.set_status(f"Queued {Path(image_path).name}")

        self.update_gallery_selection()

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
            self.left_canvas.configure(text="Release to load images")

    def handle_drag_leave(self, _event):
        self.left_panel.configure(border_color="#253244", border_width=1)
        if not self.selected_image:
            self.left_canvas.configure(text="Drop images here\nor click Browse Image")

    def handle_drop(self, event):
        self.left_panel.configure(border_color="#253244", border_width=1)
        self.load_images(self.tk.splitlist(event.data))

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
        self.gallery_panel.grid_forget()

        if layout == "stacked":
            self.body.grid_columnconfigure(0, weight=1, uniform="")
            self.body.grid_columnconfigure(1, weight=0, uniform="")
            self.body.grid_rowconfigure((0, 1), weight=1, uniform="preview")
            self.body.grid_rowconfigure(2, weight=0, uniform="")
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 9))
            self.right_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(9, 0))
            self.gallery_panel.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        else:
            self.body.grid_columnconfigure((0, 1), weight=1, uniform="preview")
            self.body.grid_rowconfigure(0, weight=1, uniform="")
            self.body.grid_rowconfigure(1, weight=0, uniform="")
            self.body.grid_rowconfigure(2, weight=0, uniform="")
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9), pady=0)
            self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(9, 0), pady=0)
            self.gallery_panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))

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
        filenames = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        self.load_images(filenames)

    def browse_batch(self):
        filenames = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        self.load_images(filenames)

    def load_images(self, filenames):
        paths = []
        for filename in filenames:
            path = Path(filename)
            if path.suffix.lower() in IMAGE_TYPES and path.exists():
                paths.append(path)

        if not paths:
            self.set_status("Please choose PNG, JPG, JPEG, or WEBP images")
            return

        self.image_queue = [str(path) for path in paths]
        self.selected_image = self.image_queue[0]
        self.result_images = {}
        self.raw_result_images = {}
        self.result_image = None
        self.current_result_path = None
        self.show_original_preview(Path(self.selected_image))
        self.right_canvas.configure(image=None, text="Your finished preview appears here")
        self.right_canvas.image = None
        self.refresh_gallery()
        self.remove_btn.configure(state="normal")
        self.save_btn.configure(state="disabled")
        self.save_all_btn.configure(state="disabled")
        label = "image" if len(paths) == 1 else "images"
        self.set_status(f"Loaded {len(paths)} {label}")
        self.progress.set(0)

    def show_original_preview(self, path):
        try:
            img = Image.open(path)
        except Exception as e:
            self.set_status("Could not open image")
            print("ERROR:", e)
            return

        preview = img.copy()
        preview.thumbnail((520, 520))
        ctk_img = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.left_canvas.configure(image=ctk_img, text="")
        self.left_canvas.image = ctk_img

    def remove_bg(self):
        if not self.image_queue:
            return
        self.set_processing_state(True)
        self.processing = True
        self.progress_value = 0.08
        self.progress.set(0)
        self.set_status("Removing backgrounds...")
        self.animate_progress()
        threading.Thread(target=self.process_images, daemon=True).start()

    def set_processing_state(self, is_processing):
        state = "disabled" if is_processing else "normal"
        self.browse_btn.configure(state=state)
        self.batch_btn.configure(state=state)
        self.remove_btn.configure(state="disabled" if is_processing else "normal")
        self.crop_menu.configure(state="disabled" if is_processing else "normal")
        self.save_btn.configure(state="disabled" if is_processing or self.result_image is None else "normal")
        self.save_all_btn.configure(state="disabled" if is_processing or not self.result_images else "normal")

    def process_images(self):
        results = {}
        total = len(self.image_queue)
        try:
            for index, image_path in enumerate(self.image_queue, start=1):
                self.after(0, lambda p=image_path, i=index, t=total: self.mark_processing(p, i, t))
                output = remove_background(image_path)
                image = Image.open(io.BytesIO(output)).convert("RGBA")
                results[image_path] = image
                self.after(0, lambda p=image_path, i=index, t=total: self.mark_processed(p, i, t))
            self.after(0, lambda: self.update_results(results))
        except Exception as e:
            self.after(0, lambda: self.processing_failed(str(e)))

    def mark_processing(self, image_path, index, total):
        self.set_status(f"Processing {index}/{total}: {Path(image_path).name}")
        self.update_gallery_item(image_path, "Processing")

    def mark_processed(self, image_path, index, total):
        self.progress.set(index / total)
        self.update_gallery_item(image_path, "Ready")

    def update_results(self, results):
        self.processing = False
        self.raw_result_images = results
        self.result_images = self.build_preset_results(results)
        self.current_result_path = next(iter(self.result_images), None)
        self.result_image = self.result_images.get(self.current_result_path)
        self.selected_image = self.current_result_path
        self.show_original_preview(Path(self.current_result_path))
        self.show_result_preview(self.result_image)
        self.refresh_gallery()
        self.progress.set(1)
        label = "image" if len(results) == 1 else "images"
        self.set_status(f"Background removed for {len(results)} {label}")
        self.set_processing_state(False)

    def show_result_preview(self, image):
        if image is None:
            return
        preview = image.copy()
        preview.thumbnail((520, 520))
        ctk_img = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.right_canvas.configure(image=ctk_img, text="")
        self.right_canvas.image = ctk_img

    def build_preset_results(self, source_results):
        return {
            image_path: self.make_preset_image(image)
            for image_path, image in source_results.items()
        }

    def make_preset_image(self, image):
        preset = CROP_PRESETS.get(self.crop_preset.get())
        if preset is None:
            return image.copy()

        target_w, target_h = preset
        source = image.convert("RGBA")
        alpha_bbox = source.getchannel("A").getbbox()
        if alpha_bbox:
            source = source.crop(alpha_bbox)

        source.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        x = (target_w - source.width) // 2
        y = (target_h - source.height) // 2
        canvas.alpha_composite(source, (x, y))
        return canvas

    def apply_crop_to_current(self, _choice=None):
        if not self.result_images:
            return
        self.result_images = self.build_preset_results(self.raw_result_images)
        self.result_image = self.result_images.get(self.current_result_path)
        self.show_result_preview(self.result_image)
        self.refresh_gallery()
        self.set_status(f"Applied {self.crop_preset.get()} preset")

    def processing_failed(self, message):
        self.processing = False
        self.progress.set(0)
        self.set_status("Could not process image")
        self.set_processing_state(False)
        self.save_btn.configure(state="disabled")
        print("ERROR:", message)

    def save_image(self):
        if self.result_image is None:
            return
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if filename:
            self.result_image.save(filename)
            self.set_status("Saved PNG")

    def save_all_images(self):
        if not self.result_images:
            return
        folder = filedialog.askdirectory()
        if not folder:
            return
        output_dir = Path(folder)
        preset_name = self.crop_preset.get().lower().replace(" ", "_").replace(":", "x")
        for source_path, image in self.result_images.items():
            source = Path(source_path)
            filename = f"{source.stem}_no_bg_{preset_name}.png"
            image.save(output_dir / filename)
        self.set_status(f"Saved {len(self.result_images)} PNG files")
