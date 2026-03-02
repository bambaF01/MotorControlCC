import time
import re
import sys
import threading
import queue
import argparse
from pathlib import Path
import serial
from serial.tools import list_ports

BAUD = 9600
OUT_PREFIX = "moteur_"
OUT_DIR = Path(__file__).resolve().parent


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


def main():
    parser = argparse.ArgumentParser(description="Logger serie pour moteurs (Arduino).")
    parser.add_argument("--port", help="Port serie a utiliser (ex: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=BAUD, help="Vitesse serie (default: 9600)")
    args = parser.parse_args()

    port = args.port or find_arduino_port()
    if not port:
        print("Aucun port serie detecte.")
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"{OUT_PREFIX}{timestamp}.csv"
    print(f"Port utilise: {port}")
    print(f"Enregistrement dans: {out}")
    print("Enregistrement CSV via commandes 'save' (start/stop).")
    print("Commandes interactives: save, v60, s, m, 1..6. Entree pour envoyer.")

    logging = False
    out_handle = None
    pattern = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?),\s*([+-]?\d+(?:\.\d+)?),\s*([+-]?\d+(?:\.\d+)?)\s*$")
    plotter_pattern = re.compile(r"rpm:\s*([+-]?\d+(?:\.\d+)?)\s+cons:\s*([+-]?\d+(?:\.\d+)?)")
    plotter_pwm_pattern = re.compile(r"rpm:\s*([+-]?\d+(?:\.\d+)?)\s+pwm:\s*([+-]?\d+(?:\.\d+)?)")
    monitor_start = time.time()
    cmd_queue = queue.Queue()

    def stdin_reader():
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            cmd = line.strip()
            if cmd:
                cmd_queue.put(cmd)
    with serial.Serial(port, args.baud, timeout=1) as ser:
        time.sleep(2.0)  # laisser le temps a la Due (ou autre Arduino) de redemarrer
        ser.reset_input_buffer()
        thread = threading.Thread(target=stdin_reader, daemon=True)
        thread.start()
        try:
            while True:
                while not cmd_queue.empty():
                    cmd = cmd_queue.get_nowait()
                    ser.write((cmd + "\n").encode("utf-8"))
                    print(f"Commande envoyee: {cmd}")

                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                if line == "CSV_START":
                    if not logging:
                        out_handle = open(out, "w", encoding="utf-8")
                        out_handle.write("t_ms,rpm,cons\n")
                        start_time = time.time()
                        logging = True
                        print("Enregistrement demarre.")
                    continue

                if line == "CSV_END":
                    if logging and out_handle:
                        out_handle.flush()
                        out_handle.close()
                        out_handle = None
                        logging = False
                        print(f"Enregistrement termine: {out}")
                        break
                    continue

                if logging:
                    m = pattern.match(line)
                    if m and out_handle:
                        out_handle.write(f"{m.group(1)},{m.group(2)},{m.group(3)}\n")
                    else:
                        # Afficher les messages de statut (ex: gains) sans polluer le CSV
                        print(line)
                else:
                    # Avant CSV_START, affiche simplement les messages
                    mplot = plotter_pattern.search(line)
                    if mplot:
                        t_ms = int((time.time() - monitor_start) * 1000)
                        #print(f"rpm:{mplot.group(1)} cons:{mplot.group(2)} tMs:{t_ms}")
                    else:
                        mplot_pwm = plotter_pwm_pattern.search(line)
                        if mplot_pwm:
                            t_ms = int((time.time() - monitor_start) * 1000)
                            #print(f"rpm:{mplot_pwm.group(1)} pwm:{mplot_pwm.group(2)} tMs:{t_ms}")
                        else:
                            print(line)
        except KeyboardInterrupt:
            print("Arret demande. Ecriture du fichier...")
        finally:
            if out_handle:
                out_handle.flush()
                out_handle.close()
                print(f"Fichier ecrit: {out}")


if __name__ == "__main__":
    main()
