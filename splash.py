import tkinter as tk
from PIL import Image, ImageTk

def show_splash_screen(main_app_callback):
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.config(bg='pink')  # Escolha uma cor RARA que NÃO está na sua logo

    # Centralize a janela
    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    width = 600
    height = 600
    x = (screen_w // 2) - (width // 2)
    y = (screen_h // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    # Torna 'pink' transparente no Windows (tem que ser após geometry/config)
    splash.wm_attributes('-transparentcolor', 'pink')
    # Remove barra de tarefas
    splash.wm_attributes('-topmost', True)

    # Carrega e exibe a logo (PNG transparente)
    logo_img = Image.open("logo_fcp.png")
    logo_img = logo_img.resize((450, 450), Image.LANCZOS)
    logo_tk = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(splash, image=logo_tk, bg='pink', borderwidth=0, highlightthickness=0)
    logo_label.pack(pady=(40, 0))

    # Texto "Loading..."
    lbl = tk.Label(
        splash,
        text="Loading...",
        font=("Calibri", 22, "bold"),
        bg='pink',
        fg="#444",
        borderwidth=0,
        highlightthickness=0
    )
    lbl.pack(pady=(20, 0))

    # Fecha a splash e chama o app principal após 4 segundos
    splash.after(4000, lambda: [splash.destroy(), main_app_callback()])

    # Mantém referências
    splash.logo_tk = logo_tk

    splash.mainloop()
