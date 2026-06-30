import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import threading
import io

from remover import remove_background

class BackgroundRemoverApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Background Remover Pro")
        self.geometry("1350x760")
        self.minsize(1200,700)

        self.selected_image = None
        self.result_image = None

        self.build_ui()

    def build_ui(self):

        # ==========================
        # HEADER
        # ==========================

        header = ctk.CTkFrame(self,height=70,corner_radius=0)
        header.pack(fill="x")

        title = ctk.CTkLabel(
            header,
            text="Background Remover Pro",
            font=("Segoe UI",28,"bold")
        )
        title.pack(side="left",padx=25,pady=18)

        dev = ctk.CTkLabel(
            header,
            text="Developed by Alexandre Justin Repia",
            font=("Segoe UI",14)
        )

        dev.pack(side="right",padx=25)

        # ==========================
        # BODY
        # ==========================

        body = ctk.CTkFrame(self)
        body.pack(fill="both",expand=True,padx=20,pady=20)

        left = ctk.CTkFrame(body)
        left.pack(side="left",fill="both",expand=True,padx=(0,10))

        right = ctk.CTkFrame(body)
        right.pack(side="left",fill="both",expand=True)

        # LEFT TITLE

        ctk.CTkLabel(
            left,
            text="Original Image",
            font=("Segoe UI",22,"bold")
        ).pack(pady=15)

        self.left_canvas = ctk.CTkLabel(
            left,
            text="Drop Image Here\n\nor\n\nClick Browse",
            width=520,
            height=520,
            fg_color="#1d1d1d",
            corner_radius=15
        )

        self.left_canvas.pack(padx=20,pady=10,fill="both",expand=True)

        # RIGHT TITLE

        ctk.CTkLabel(
            right,
            text="Result",
            font=("Segoe UI",22,"bold")
        ).pack(pady=15)

        self.right_canvas = ctk.CTkLabel(
            right,
            text="Background Removed Preview",
            width=520,
            height=520,
            fg_color="#1d1d1d",
            corner_radius=15
        )

        self.right_canvas.pack(padx=20,pady=10,fill="both",expand=True)

        # ==========================
        # FOOTER
        # ==========================

        footer = ctk.CTkFrame(self,height=90)
        footer.pack(fill="x")

        self.browse_btn = ctk.CTkButton(
            footer,
            text="Browse Image",
            width=170,
            height=45,
            command=self.browse_image
        )

        self.browse_btn.pack(side="left",padx=20,pady=20)

        self.remove_btn = ctk.CTkButton(
            footer,
            text="Remove Background",
            width=170,
            height=45,
            command=self.remove_bg,
            state="disabled"
        )

        self.remove_btn.pack(side="left",padx=10)

        self.save_btn = ctk.CTkButton(
            footer,
            text="Save As",
            width=170,
            height=45,
            command=self.save_image,
            state="disabled"
        )

        self.save_btn.pack(side="left",padx=10)

        self.batch_btn = ctk.CTkButton(
            footer,
            text="Batch Process",
            width=170,
            height=45
        )

        self.batch_btn.pack(side="left",padx=10)

        self.progress = ctk.CTkProgressBar(footer,width=350)
        self.progress.pack(side="right",padx=25)

        self.progress.set(0)

    def browse_image(self):

        filename = filedialog.askopenfilename(
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp")
            ]
        )

        if not filename:
            return

        self.selected_image = filename

        img = Image.open(filename)

        preview = img.copy()
        preview.thumbnail((500, 500))

        ctk_img = ctk.CTkImage(
            light_image=preview,
            dark_image=preview,
            size=preview.size
        )

        self.left_canvas.configure(
            image=ctk_img,
            text=""
        )

        self.left_canvas.image = ctk_img

        self.remove_btn.configure(state="normal")

    def remove_bg(self):
        if not self.selected_image:
            return

        self.remove_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.progress.set(0)

        threading.Thread(
            target=self.process_image,
            daemon=True
        ).start()
    
    def process_image(self):

        try:

            self.after(0, lambda: self.progress.set(0.15))

            output = remove_background(self.selected_image)

            self.after(0, lambda: self.progress.set(0.7))

            image = Image.open(io.BytesIO(output))

            self.result_image = image.copy()

            preview = image.copy()
            preview.thumbnail((500, 500))

            self.after(
                0,
                lambda: self.update_result(preview)
            )

        except Exception as e:
            print("ERROR:", e)


    def update_result(self, image):

        ctk_img = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size
        )

        self.right_canvas.configure(
            image=ctk_img,
            text=""
        )

        self.right_canvas.image = ctk_img

        self.progress.set(1)

        self.save_btn.configure(state="normal")
        self.remove_btn.configure(state="normal")


    def save_image(self):

        if self.result_image is None:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image","*.png")
            ]
        )

        if filename:

            self.result_image.save(filename)