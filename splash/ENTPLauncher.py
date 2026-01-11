import os
import subprocess
import threading
import tkinter as tk

from PIL import Image, ImageTk

BASE = os.path.dirname(os.path.abspath(__file__))


def launch_main():
    subprocess.Popen([os.path.join(BASE, "EasiNoteMain.exe")])


root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)

img = Image.open(os.path.join(BASE, "splash.png"))
photo = ImageTk.PhotoImage(img)

w, h = img.size
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

label = tk.Label(root, image=photo, border=0)
label.pack()

threading.Thread(target=launch_main, daemon=True).start()

root.after(6000, root.destroy)
root.mainloop()
