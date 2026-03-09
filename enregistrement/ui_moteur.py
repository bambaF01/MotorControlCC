import argparse
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import serial
from serial.tools import list_ports

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BAUD = 9600
OUT_PREFIX = "moteur_"
OUT_DIR = Path(__file__).resolve().parent


PID_PATTERN = re.compile(r"rpm:\s*([+-]?\d+(?:\.\d+)?)\s+cons:\s*([+-]?\d+(?:\.\d+)?)")
BO_PATTERN = re.compile(r"rpm:\s*([+-]?\d+(?:\.\d+)?)\s+pwm:\s*([+-]?\d+(?:\.\d+)?)")
GAINS_PATTERN = re.compile(
    r"Kp=\s*([+-]?\d+(?:\.\d+)?)\s+Ki=\s*([+-]?\d+(?:\.\d+)?)\s+Kd=\s*([+-]?\d+(?:\.\d+)?)"
)


@dataclass
class Sample:
    t: float
    rpm: float
    aux: float


def find_arduino_port(prefer_due: bool = True):
    ports = list(list_ports.comports())
    if not ports:
        return None

    keywords = ["arduino", "usb", "acm", "usb-serial", "cp210", "ch340", "ftdi"]
    due_keywords = ["arduino due", "due", "sam", "atmel", "programming port", "native usb"]

    def score_port(p):
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        score = 0
        if any(k in desc for k in keywords) or any(k in hwid for k in keywords):
            score += 10
        if prefer_due and (any(k in desc for k in due_keywords) or any(k in hwid for k in due_keywords)):
            score += 20
        return score

    ports_sorted = sorted(ports, key=score_port, reverse=True)
    if score_port(ports_sorted[0]) > 0:
        return ports_sorted[0].device

    return ports[0].device


class SerialReader(threading.Thread):
    def __init__(self, ser: serial.Serial, out_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.ser = ser
        self.out_queue = out_queue
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException:
                break
            if line:
                self.out_queue.put(line)


class MotorUI:
    def __init__(self, root, port: Optional[str], baud: int):
        self.root = root
        self.root.title("Motor PID UI")

        self.port_var = tk.StringVar(value=port or "")
        self.baud_var = tk.IntVar(value=baud)
        self.status_var = tk.StringVar(value="Deconnecte")
        self.mode_var = tk.StringVar(value="auto")
        self.detected_mode_var = tk.StringVar(value="-")

        self.setpoint_var = tk.StringVar(value="0")
        self.pwm_var = tk.StringVar(value="0")
        self.kp_var = tk.StringVar(value="0.0")
        self.ki_var = tk.StringVar(value="0.0")
        self.kd_var = tk.StringVar(value="0.0")

        self.sample_window = 10.0
        self.max_points = 500
        self.data = deque(maxlen=self.max_points)

        self.logging = False
        self.log_handle = None
        self.log_start_time = None
        self.log_path = None
        self.log_header = None

        self.ser = None
        self.reader_thread = None
        self.reader_stop = threading.Event()
        self.line_queue = queue.Queue()
        self.send_lock = threading.Lock()
        self.start_time = None

        self._build_ui()
        self._schedule_update()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Port:").pack(side=tk.LEFT)
        ttk.Entry(top, width=18, textvariable=self.port_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Detecter", command=self._detect_port).pack(side=tk.LEFT)

        ttk.Label(top, text="Baud:").pack(side=tk.LEFT, padx=(12, 2))
        ttk.Entry(top, width=8, textvariable=self.baud_var).pack(side=tk.LEFT)

        ttk.Button(top, text="Connecter", command=self.connect).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Deconnecter", command=self.disconnect).pack(side=tk.LEFT)

        ttk.Label(top, textvariable=self.status_var).pack(side=tk.LEFT, padx=10)

        mode_frame = ttk.Frame(self.root, padding=10)
        mode_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Auto", value="auto", variable=self.mode_var).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="PID", value="pid", variable=self.mode_var).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="BO", value="bo", variable=self.mode_var).pack(side=tk.LEFT)
        ttk.Label(mode_frame, text="Detecte:").pack(side=tk.LEFT, padx=(12, 2))
        ttk.Label(mode_frame, textvariable=self.detected_mode_var).pack(side=tk.LEFT)

        controls = ttk.Frame(self.root, padding=10)
        controls.pack(side=tk.TOP, fill=tk.X)

        pid_box = ttk.LabelFrame(controls, text="PID")
        pid_box.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        self._row_entry(pid_box, "Consigne (rpm)", self.setpoint_var)
        self._row_buttons(pid_box, "Consigne", "v", self.setpoint_var, step=5)

        self._row_entry(pid_box, "Kp", self.kp_var)
        self._row_buttons(pid_box, "Kp", "kp", self.kp_var, step=0.1)

        self._row_entry(pid_box, "Ki", self.ki_var)
        self._row_buttons(pid_box, "Ki", "ki", self.ki_var, step=0.1)

        self._row_entry(pid_box, "Kd", self.kd_var)
        self._row_buttons(pid_box, "Kd", "kd", self.kd_var, step=0.1)

        ttk.Button(pid_box, text="Lire gains (g)", command=self._send_get_gains).pack(side=tk.TOP, pady=(6, 2))

        bo_box = ttk.LabelFrame(controls, text="Boucle Ouverte")
        bo_box.pack(side=tk.LEFT, fill=tk.Y)

        self._row_entry(bo_box, "PWM", self.pwm_var)
        self._row_buttons(bo_box, "PWM", "p", self.pwm_var, step=50)

        ttk.Button(bo_box, text="Stop (s)", command=self._send_stop).pack(side=tk.TOP, pady=(8, 2))

        log_box = ttk.LabelFrame(controls, text="Enregistrement")
        log_box.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        ttk.Button(log_box, text="Sauvegarder", command=self._start_logging).pack(side=tk.TOP, pady=(4, 2))
        ttk.Button(log_box, text="Arreter", command=self._stop_logging).pack(side=tk.TOP, pady=(2, 4))
        self.log_status_var = tk.StringVar(value="Inactif")
        ttk.Label(log_box, textvariable=self.log_status_var).pack(side=tk.TOP, pady=(4, 2))

        plot_frame = ttk.Frame(self.root, padding=10)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Temps (s)")
        self.ax.set_ylabel("RPM / Consigne")
        self.rpm_line, = self.ax.plot([], [], label="rpm")
        self.aux_line, = self.ax.plot([], [], label="consigne/pwm")
        self.ax.legend(loc="upper right")
        self.ax.grid(True, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _row_entry(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
        ttk.Entry(row, width=10, textvariable=var).pack(side=tk.LEFT)
        ttk.Button(row, text="Set", command=lambda: self._send_set(label, var)).pack(side=tk.LEFT, padx=4)

    def _row_buttons(self, parent, label, prefix, var, step):
        row = ttk.Frame(parent)
        row.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row, text=f"{label} +/ -", width=14).pack(side=tk.LEFT)
        ttk.Button(row, text="-", width=3, command=lambda: self._send_step(prefix, -step, var)).pack(side=tk.LEFT)
        ttk.Button(row, text="+", width=3, command=lambda: self._send_step(prefix, step, var)).pack(side=tk.LEFT, padx=2)

    def _detect_port(self):
        port = find_arduino_port()
        if port:
            self.port_var.set(port)

    def connect(self):
        if self.ser and self.ser.is_open:
            return
        port = self.port_var.get().strip()
        baud = int(self.baud_var.get())
        if not port:
            port = find_arduino_port()
            if port:
                self.port_var.set(port)
            else:
                self.status_var.set("Aucun port")
                return
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
        except serial.SerialException as exc:
            self.status_var.set(f"Erreur: {exc}")
            return

        time.sleep(2.0)
        self.reader_stop.clear()
        self.reader_thread = SerialReader(self.ser, self.line_queue, self.reader_stop)
        self.reader_thread.start()
        self.start_time = time.time()
        self.status_var.set(f"Connecte: {port}")

    def disconnect(self):
        if not self.ser:
            return
        self._stop_logging()
        self.reader_stop.set()
        if self.reader_thread:
            self.reader_thread.join(timeout=1.0)
        try:
            self.ser.close()
        except serial.SerialException:
            pass
        self.ser = None
        self.status_var.set("Deconnecte")

    def _send(self, cmd: str):
        if not self.ser or not self.ser.is_open:
            self.status_var.set("Non connecte")
            return
        with self.send_lock:
            try:
                self.ser.write((cmd + "\n").encode("utf-8"))
            except serial.SerialException as exc:
                self.status_var.set(f"Erreur: {exc}")

    def _send_set(self, label, var):
        val = var.get().strip()
        if not val:
            return
        if label.startswith("Consigne"):
            self._send(f"v{val}")
        elif label == "PWM":
            self._send(f"p{val}")
        elif label == "Kp":
            self._send(f"kp{val}")
        elif label == "Ki":
            self._send(f"ki{val}")
        elif label == "Kd":
            self._send(f"kd{val}")

    def _send_step(self, prefix, step, var):
        try:
            current = float(var.get())
        except ValueError:
            current = 0.0
        new_val = current + step
        if prefix == "v":
            if new_val < 0:
                new_val = 0
            var.set(str(int(new_val)))
            self._send(f"v{int(new_val)}")
            return
        if prefix == "p":
            if new_val < 0:
                new_val = 0
            var.set(str(int(new_val)))
            self._send(f"p{int(new_val)}")
            return
        if prefix in ("kp", "ki", "kd"):
            if new_val < 0:
                new_val = 0.0
            text = f"{new_val:.3f}".rstrip("0").rstrip(".")
            var.set(text if text else "0")
            self._send(f"{prefix}{text}")
            return
        if step > 0:
            self._send(f"{prefix}+")
        else:
            self._send(f"{prefix}-")

    def _send_stop(self):
        self._send("s")

    def _send_get_gains(self):
        self._send("g")

    def _schedule_update(self):
        self._process_lines()
        self.root.after(100, self._schedule_update)

    def _process_lines(self):
        updated = False
        while True:
            try:
                line = self.line_queue.get_nowait()
            except queue.Empty:
                break
            updated = True
            self._handle_line(line)

        if updated:
            self._update_plot()

    def _handle_line(self, line: str):
        m_pid = PID_PATTERN.search(line)
        if m_pid:
            self.detected_mode_var.set("PID")
            rpm = float(m_pid.group(1))
            cons = float(m_pid.group(2))
            self._append_sample(rpm, cons)
            return

        m_bo = BO_PATTERN.search(line)
        if m_bo:
            self.detected_mode_var.set("BO")
            rpm = float(m_bo.group(1))
            pwm = float(m_bo.group(2))
            self._append_sample(rpm, pwm)
            return

        m_gains = GAINS_PATTERN.search(line)
        if m_gains:
            self.kp_var.set(m_gains.group(1))
            self.ki_var.set(m_gains.group(2))
            self.kd_var.set(m_gains.group(3))
            return

    def _append_sample(self, rpm: float, aux: float):
        if self.start_time is None:
            self.start_time = time.time()
        t = time.time() - self.start_time
        self.data.append(Sample(t=t, rpm=rpm, aux=aux))
        if self.logging and self.log_handle:
            if self.log_start_time is None:
                self.log_start_time = time.time()
            t_ms = int((time.time() - self.log_start_time) * 1000)
            self.log_handle.write(f"{t_ms},{rpm},{aux}\n")

    def _update_plot(self):
        if not self.data:
            return
        xs = [s.t for s in self.data]
        rpm = [s.rpm for s in self.data]
        aux = [s.aux for s in self.data]

        self.rpm_line.set_data(xs, rpm)
        mode = self._current_mode()
        if mode == "pid":
            self.aux_line.set_data(xs, aux)
            self.aux_line.set_visible(True)
            self.aux_line.set_label("consigne")
            self.ax.set_ylabel("RPM / Consigne")
        elif mode == "bo":
            self.aux_line.set_data([], [])
            self.aux_line.set_visible(False)
            self.aux_line.set_label("_nolegend_")
            self.ax.set_ylabel("RPM")
        else:
            self.aux_line.set_data(xs, aux)
            self.aux_line.set_visible(True)
            self.aux_line.set_label("consigne/pwm")
            self.ax.set_ylabel("RPM / Consigne/PWM")
        self.ax.legend(loc="upper right")

        xmax = xs[-1]
        xmin = max(0.0, xmax - self.sample_window)
        self.ax.set_xlim(xmin, xmax if xmax > 1.0 else 1.0)

        ymin = min(min(rpm), min(aux))
        ymax = max(max(rpm), max(aux))
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        self.ax.set_ylim(ymin - 5, ymax + 5)

        self.canvas.draw_idle()

    def _current_mode(self):
        mode = self.mode_var.get()
        if mode == "auto":
            detected = self.detected_mode_var.get().lower()
            if detected in ("pid", "bo"):
                return detected
            return "auto"
        return mode

    def _start_logging(self):
        if self.logging:
            return
        mode = self._current_mode()
        if mode == "pid":
            self.log_header = "t_ms,rpm,cons"
        elif mode == "bo":
            self.log_header = "t_ms,rpm,pwm"
        else:
            self.log_header = "t_ms,rpm,aux"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_path = OUT_DIR / f"{OUT_PREFIX}{timestamp}.csv"
        self.log_handle = open(self.log_path, "w", encoding="utf-8")
        self.log_handle.write(self.log_header + "\n")
        self.log_start_time = time.time()
        self.logging = True
        self.log_status_var.set(f"Actif: {self.log_path.name}")

    def _stop_logging(self):
        if not self.logging:
            return
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()
        self.log_handle = None
        self.logging = False
        self.log_start_time = None
        self.log_status_var.set("Inactif")


def main():
    parser = argparse.ArgumentParser(description="Interface UI pour moteur (PID ou boucle ouverte)")
    parser.add_argument("--port", help="Port serie a utiliser (ex: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=BAUD, help="Vitesse serie (default: 9600)")
    args = parser.parse_args()

    root = tk.Tk()
    app = MotorUI(root, args.port, args.baud)

    def on_close():
        app.disconnect()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
