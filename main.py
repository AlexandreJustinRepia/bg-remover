import customtkinter as ctk
from ui import BackgroundRemoverApp

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    app = BackgroundRemoverApp()
    app.mainloop()