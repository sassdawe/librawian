"""Small local-only desktop camera scanner."""

import sys
import tkinter as tk
from tkinter import messagebox, ttk

from librawian.excel import ExcelTarget
from librawian.scanner import ScanSession


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.camera = None
        self.target = None
        self.session = ScanSession()
        self.pending = None
        self.cv2 = None
        self.decode = None
        root.title("Librawian — book ISBN scanner")
        root.protocol("WM_DELETE_WINDOW", self.close)
        panel = ttk.Frame(root, padding=12)
        panel.pack(fill="both", expand=True)
        self.mode = tk.StringVar(value="Excel" if sys.platform in ("win32", "darwin") else "Clipboard")
        self.mode_picker = ttk.Combobox(
            panel, textvariable=self.mode, values=("Excel", "Clipboard"), state="readonly"
        )
        self.mode_picker.pack(fill="x")
        self.connect_button = ttk.Button(panel, text="Use selected Excel cell", command=self.connect)
        self.connect_button.pack(fill="x", pady=4)
        self.destination = tk.StringVar(value="Excel: select the first empty ISBN cell, then connect.")
        ttk.Label(panel, textvariable=self.destination, wraplength=640).pack()
        controls = ttk.Frame(panel)
        controls.pack(fill="x", pady=8)
        ttk.Label(controls, text="Camera index:").pack(side="left")
        self.camera_index = ttk.Entry(controls, width=4)
        self.camera_index.insert(0, "0")
        self.camera_index.pack(side="left", padx=4)
        self.start_button = ttk.Button(controls, text="Start", command=self.start)
        self.start_button.pack(side="left", padx=4)
        ttk.Button(controls, text="Stop", command=self.stop).pack(side="left")
        ttk.Button(controls, text="Allow same ISBN again", command=self.allow_repeat).pack(side="right")
        self.preview = ttk.Label(panel, text="Camera preview", anchor="center")
        self.preview.pack(fill="both", expand=True)
        self.latest = tk.StringVar()
        ttk.Entry(panel, textvariable=self.latest, state="readonly").pack(fill="x", pady=8)
        self.status = tk.StringVar(value="Ready. Clipboard mode copies each scan for manual paste.")
        ttk.Label(panel, textvariable=self.status, wraplength=640).pack()

    def connect(self):
        self.target = None
        self.destination.set("Not connected. Select an empty ISBN cell in Excel and connect.")
        try:
            target = ExcelTarget.connect()
            description = target.description
        except Exception as exc:
            messagebox.showerror("Cannot connect to Excel", str(exc))
            return
        self.target = target
        self.destination.set(description)

    def allow_repeat(self):
        self.session.last_isbn = None
        self.status.set("Repeat enabled. The next visible ISBN will be sent again.")

    def start(self):
        if self.camera is not None:
            return
        if self.mode.get() == "Excel" and self.target is None:
            messagebox.showerror("Choose a destination", "Select an empty ISBN cell in Excel and connect first.")
            return
        camera = None
        try:
            import cv2
            from pyzbar.pyzbar import ZBarSymbol, decode

            index = int(self.camera_index.get())
            if index < 0:
                raise ValueError("Camera index must be zero or greater.")
            camera = cv2.VideoCapture(index)
            if not camera.isOpened():
                raise RuntimeError("Cannot open the webcam. Check camera permissions or try another index.")
            self.cv2 = cv2
            self.decode = lambda frame: decode(frame, symbols=[ZBarSymbol.EAN13])
        except Exception as exc:
            if camera is not None:
                camera.release()
            messagebox.showerror("Cannot start camera", str(exc))
            return
        self.camera = camera
        self.mode_picker.configure(state="disabled")
        self.connect_button.configure(state="disabled")
        self.camera_index.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.status.set("Scanning. Show one book barcode at a time; Stop before changing Excel rows.")
        self.tick()

    def send(self, number):
        if self.mode.get() == "Excel":
            self.target.write(number)
            self.destination.set(self.target.description)
        else:
            self.root.clipboard_clear()
            self.root.clipboard_append(number)

    def tick(self):
        self.pending = None
        try:
            ok, frame = self.camera.read()
            if not ok:
                raise RuntimeError("The webcam stopped providing frames. Reconnect it and press Start.")
            values = [item.data.decode("ascii", errors="replace") for item in self.decode(frame)]
            number = self.session.accept(values, self.send)
            if number:
                self.latest.set(number)
                action = "Written to Excel" if self.mode.get() == "Excel" else "Copied to clipboard"
                self.status.set(f"{action}: {number}. Show the next book (or enable repeat for another copy).")
                self.root.bell()
            height, width = frame.shape[:2]
            scale = min(640 / width, 480 / height)
            image = self.cv2.resize(frame, (int(width * scale), int(height * scale)))
            image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)
            height, width = image.shape[:2]
            data = f"P6\n{width} {height}\n255\n".encode("ascii") + image.tobytes()
            self.preview.image = tk.PhotoImage(data=data, format="PPM")
            self.preview.configure(image=self.preview.image)
        except Exception as exc:
            self.stop()
            self.status.set(f"Stopped: {exc}")
            messagebox.showerror("Scanning stopped", str(exc))
            return
        self.pending = self.root.after(100, self.tick)

    def stop(self):
        if self.pending is not None:
            self.root.after_cancel(self.pending)
            self.pending = None
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        self.mode_picker.configure(state="readonly")
        self.connect_button.configure(state="normal")
        self.camera_index.configure(state="normal")
        self.start_button.configure(state="normal")
        self.status.set("Stopped. Select and reconnect to a different cell if needed.")

    def close(self):
        self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    ScannerApp(root)
    root.mainloop()
