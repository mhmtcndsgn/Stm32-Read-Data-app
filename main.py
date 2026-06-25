import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import datetime
import os
import sys
import time
import platform
import subprocess
import re
# Matplotlib – grafik için
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
IS_MAC   = platform.system() == "Darwin"
IS_WIN   = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
# ──────────────────────────────────────────────────
# RENK PALETİ
# ──────────────────────────────────────────────────
BG_DARK       = "#0d1117"
BG_CARD       = "#161b22"
BG_CARD2      = "#1c2333"
ACCENT        = "#238636"
ACCENT_HOVER  = "#2ea043"
ACCENT2       = "#1f6feb"
BORDER        = "#30363d"
TEXT_PRIMARY  = "#e6edf3"
TEXT_SECONDARY= "#8b949e"
TEXT_SUCCESS  = "#3fb950"
TEXT_WARNING  = "#d29922"
TEXT_ERROR    = "#f85149"
TEXT_INFO     = "#58a6ff"
RED_BTN       = "#b91c1c"
RED_HOVER     = "#dc2626"
class STM32Logger:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("STM32 Veri Kaydedici")
        self.root.geometry("900x680")
        self.root.minsize(820, 600)
        self.root.configure(bg=BG_DARK)
        # İkonu set et (varsa)
        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass
        # State
        self.serial_port: serial.Serial | None = None
        self.is_running   = False
        self.read_thread: threading.Thread | None = None
        self.save_path    = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop", "stm32_data.txt"))
        self.port_var     = tk.StringVar()
        self.baud_var     = tk.StringVar(value="9600")
        self.status_var   = tk.StringVar(value="Bağlı değil")
        self.total_lines  = 0
        self.session_start= None
        self._build_ui()
        self._refresh_ports()
    # ──────────────────────────────────────────────
    # UI İNŞAAT
    # ──────────────────────────────────────────────
    def _build_ui(self):
        # Başlık
        hdr = tk.Frame(self.root, bg=BG_DARK, pady=12)
        hdr.pack(fill="x", padx=0)
        title_frame = tk.Frame(hdr, bg=BG_DARK)
        title_frame.pack(side="left", padx=24)
        tk.Label(title_frame, text="⚡ STM32", font=("Segoe UI", 22, "bold"),
                 fg=ACCENT2, bg=BG_DARK).pack(side="left")
        tk.Label(title_frame, text=" Veri Kaydedici", font=("Segoe UI", 22, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_DARK).pack(side="left")
        tk.Label(hdr, text="v1.2.0", font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(side="right", padx=24, anchor="s", pady=4)
        # Ince çizgi
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        # Ana içerik
        content = tk.Frame(self.root, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=18, pady=14)
        # Sol panel
        left = tk.Frame(content, bg=BG_DARK, width=300)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        self._build_connection_card(left)
        self._build_file_card(left)
        self._build_stats_card(left)
        # Sağ panel — terminal
        right = tk.Frame(content, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)
        self._build_terminal(right)
        # Alt durum çubuğu
        self._build_statusbar()
    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=BG_CARD, bd=0, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="x", pady=(0, 10))
        hdr = tk.Frame(outer, bg=BG_CARD2, pady=7)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=("Segoe UI", 10, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD2, padx=12).pack(anchor="w")
        body = tk.Frame(outer, bg=BG_CARD, padx=12, pady=10)
        body.pack(fill="x")
        return body
    def _build_connection_card(self, parent):
        body = self._card(parent, "🔌  Bağlantı Ayarları")
        tk.Label(body, text="COM Port", font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")
        port_frame = tk.Frame(body, bg=BG_CARD)
        port_frame.pack(fill="x", pady=(3, 8))
        self.port_cb = ttk.Combobox(port_frame, textvariable=self.port_var,
                                    state="readonly", font=("Segoe UI", 10), width=16)
        self.port_cb.pack(side="left", fill="x", expand=True)
        self._btn(port_frame, "⟳", self._refresh_ports, width=3,
                  bg=BG_CARD2, fg=TEXT_INFO).pack(side="left", padx=(6, 0))
        tk.Label(body, text="Baud Rate", font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")
        self.baud_cb = ttk.Combobox(body, textvariable=self.baud_var,
                                    values=["1200","2400","4800","9600","19200",
                                            "38400","57600","115200","230400","460800"],
                                    state="readonly", font=("Segoe UI", 10))
        self.baud_cb.pack(fill="x", pady=(3, 12))
        self.connect_btn = self._btn(body, "▶  Bağlan", self._toggle_connection,
                                     bg=ACCENT, fg=TEXT_PRIMARY, padx=8)
        self.connect_btn.pack(fill="x")
    def _build_file_card(self, parent):
        body = self._card(parent, "💾  Kayıt Dosyası")
        tk.Label(body, text="Kayıt Yolu", font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")
        path_frame = tk.Frame(body, bg=BG_CARD)
        path_frame.pack(fill="x", pady=(3, 8))
        self.path_entry = tk.Entry(path_frame, textvariable=self.save_path,
                                   font=("Segoe UI", 9), bg=BG_CARD2, fg=TEXT_PRIMARY,
                                   insertbackground=TEXT_PRIMARY, relief="flat",
                                   highlightthickness=1, highlightbackground=BORDER)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._btn(path_frame, "📂", self._browse_file, width=3,
                  bg=BG_CARD2, fg=TEXT_WARNING).pack(side="left", padx=(6, 0))
        self._btn(body, "📄  Dosyayı Aç", self._open_file,
                   bg=BG_CARD2, fg=TEXT_INFO, padx=8).pack(fill="x")
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(10, 0))
        tk.Label(body, text="Grafik", font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w", pady=(8, 3))
        self._btn(body, "📈  Grafik Oluştur", self._show_graph,
                  bg=ACCENT2, fg=TEXT_PRIMARY, padx=8).pack(fill="x")
    def _build_stats_card(self, parent):
        body = self._card(parent, "📊  İstatistikler")
        rows = [
            ("Toplam Satır",   "stat_lines",   TEXT_SUCCESS),
            ("Son Veri",       "stat_last",    TEXT_PRIMARY),
            ("Süre",           "stat_duration",TEXT_INFO),
        ]
        self.stat_vars = {}
        for label, key, color in rows:
            row = tk.Frame(body, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", font=("Segoe UI", 9),
                     fg=TEXT_SECONDARY, bg=BG_CARD, width=14, anchor="w").pack(side="left")
            v = tk.StringVar(value="—")
            self.stat_vars[key] = v
            tk.Label(row, textvariable=v, font=("Segoe UI", 9, "bold"),
                     fg=color, bg=BG_CARD).pack(side="left")
    def _build_terminal(self, parent):
        hdr = tk.Frame(parent, bg=BG_CARD2, pady=7,
                       highlightthickness=1, highlightbackground=BORDER)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📡  Gelen Veriler", font=("Segoe UI", 10, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD2, padx=12).pack(side="left")
        self._btn(hdr, "🗑 Temizle", self._clear_terminal,
                  bg=BG_CARD2, fg=TEXT_WARNING).pack(side="right", padx=8)
        self.terminal = scrolledtext.ScrolledText(
            parent, bg="#010409", fg=TEXT_SUCCESS,
            font=self._mono_font(10),
            relief="flat", state="disabled", wrap="word",
            insertbackground=TEXT_SUCCESS,
            selectbackground=ACCENT2, selectforeground=TEXT_PRIMARY,
            highlightthickness=1, highlightbackground=BORDER
        )
        self.terminal.pack(fill="both", expand=True)
        # Tag'ler
        self.terminal.tag_config("info",    foreground=TEXT_INFO)
        self.terminal.tag_config("success", foreground=TEXT_SUCCESS)
        self.terminal.tag_config("warning", foreground=TEXT_WARNING)
        self.terminal.tag_config("error",   foreground=TEXT_ERROR)
        self.terminal.tag_config("ts",      foreground=TEXT_SECONDARY)
        self.terminal.tag_config("data",    foreground="#a5d6ff")
    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=BG_CARD2, pady=5,
                       highlightthickness=1, highlightbackground=BORDER)
        bar.pack(fill="x", side="bottom")
        self.status_dot = tk.Label(bar, text="●", font=("Segoe UI", 11),
                                   fg=TEXT_ERROR, bg=BG_CARD2)
        self.status_dot.pack(side="left", padx=(12, 4))
        tk.Label(bar, textvariable=self.status_var, font=("Segoe UI", 9),
                 fg=TEXT_SECONDARY, bg=BG_CARD2).pack(side="left")
        tk.Label(bar, text="STM32 Veri Kaydedici  •  © 2025",
                 font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_CARD2).pack(side="right", padx=12)
    # ──────────────────────────────────────────────
    # YARDIMCI
    # ──────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg=BG_CARD2, fg=TEXT_PRIMARY,
             width=None, padx=6):
        kw = dict(text=text, command=cmd, font=("Segoe UI", 9, "bold"),
                  bg=bg, fg=fg, activebackground=ACCENT_HOVER, activeforeground=TEXT_PRIMARY,
                  relief="flat", cursor="hand2", pady=6, padx=padx, bd=0)
        if width:
            kw["width"] = width
        b = tk.Button(parent, **kw)
        b.bind("<Enter>", lambda e: b.configure(bg=ACCENT_HOVER if bg == ACCENT else BG_CARD))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b
    def _font_exists(self, name):
        import tkinter.font as tkfont
        return name in tkfont.families()
    def _mono_font(self, size=10):
        """İşletim sistemine göre en uygun monospace fontu seç."""
        import tkinter.font as tkfont
        families = tkfont.families()
        candidates = ["Cascadia Code", "JetBrains Mono", "SF Mono",
                      "Menlo", "Monaco", "Consolas", "Courier New"]
        for f in candidates:
            if f in families:
                return (f, size)
        return ("Courier", size)
    def _log(self, text, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"[{ts}] ", "ts")
        self.terminal.insert("end", text + "\n", tag)
        self.terminal.see("end")
        self.terminal.configure(state="disabled")
    def _set_status(self, text, connected=False):
        self.status_var.set(text)
        self.status_dot.configure(fg=TEXT_SUCCESS if connected else TEXT_ERROR)
    # ──────────────────────────────────────────────
    # PORT İŞLEMLERİ
    # ──────────────────────────────────────────────
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports:
            if self.port_var.get() not in ports:
                self.port_var.set(ports[0])
            self._log(f"{len(ports)} port bulundu: {', '.join(ports)}", "info")
        else:
            self.port_var.set("")
            self._log("Hiç COM portu bulunamadı.", "warning")
    def _toggle_connection(self):
        if self.is_running:
            self._disconnect()
        else:
            self._connect()
    def _connect(self):
        port = self.port_var.get()
        baud = self.baud_var.get()
        if not port:
            messagebox.showerror("Hata", "Lütfen bir COM portu seçin.")
            return
        try:
            self.serial_port = serial.Serial(port, int(baud), timeout=2)
            self.is_running  = True
            self.session_start = time.time()
            self.total_lines = 0
            self.connect_btn.configure(text="⏹  Durdur", bg=RED_BTN)
            self.connect_btn.bind("<Enter>", lambda e: self.connect_btn.configure(bg=RED_HOVER))
            self.connect_btn.bind("<Leave>", lambda e: self.connect_btn.configure(bg=RED_BTN))
            self._set_status(f"{port} @ {baud} baud — Bağlı", connected=True)
            self._log(f"Bağlandı → {port}  ({baud} baud)", "success")
            # Okuma thread'i
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            # Süre güncelleme döngüsü
            self._update_duration()
        except serial.SerialException as e:
            messagebox.showerror("Bağlantı Hatası", str(e))
            self._log(f"Bağlantı hatası: {e}", "error")
    def _disconnect(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.connect_btn.configure(text="▶  Bağlan", bg=ACCENT)
        self.connect_btn.bind("<Enter>", lambda e: self.connect_btn.configure(bg=ACCENT_HOVER))
        self.connect_btn.bind("<Leave>", lambda e: self.connect_btn.configure(bg=ACCENT))
        self._set_status("Bağlı değil")
        self._log("Bağlantı kesildi.", "warning")
        self.stat_vars["stat_duration"].set("—")
    # ──────────────────────────────────────────────
    # VERİ OKUMA
    # ──────────────────────────────────────────────
    def _read_loop(self):
        while self.is_running:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    raw  = self.serial_port.readline()
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self._process_data(line)
                else:
                    time.sleep(0.05)
            except serial.SerialException as e:
                self.root.after(0, self._log, f"Seri port hatası: {e}", "error")
                self.root.after(0, self._disconnect)
                break
            except Exception as e:
                self.root.after(0, self._log, f"Beklenmeyen hata: {e}", "error")
    def _process_data(self, line: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.total_lines += 1
        # Terminale yaz (thread-safe)
        self.root.after(0, self._log, f"{line}", "data")
        # İstatistik güncelle
        self.root.after(0, self.stat_vars["stat_lines"].set, str(self.total_lines))
        short = line[:22] + "…" if len(line) > 25 else line
        self.root.after(0, self.stat_vars["stat_last"].set, short)
        # Dosyaya kaydet
        try:
            path = self.save_path.get()
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {line}\n")
        except Exception as e:
            self.root.after(0, self._log, f"Dosya yazma hatası: {e}", "error")
    def _update_duration(self):
        if self.is_running and self.session_start:
            elapsed = int(time.time() - self.session_start)
            h, rem  = divmod(elapsed, 3600)
            m, s    = divmod(rem, 60)
            self.stat_vars["stat_duration"].set(f"{h:02d}:{m:02d}:{s:02d}")
            self.root.after(1000, self._update_duration)
    # ──────────────────────────────────────────────
    # DOSYA İŞLEMLERİ
    # ──────────────────────────────────────────────
    def _browse_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Metin Dosyası", "*.txt"), ("CSV Dosyası", "*.csv"), ("Tüm Dosyalar", "*.*")],
            title="Kayıt Dosyası Seç"
        )
        if path:
            self.save_path.set(path)
    def _open_file(self):
        path = self.save_path.get()
        if os.path.exists(path):
            try:
                if IS_WIN:
                    os.startfile(path)          # Windows
                elif IS_MAC:
                    subprocess.run(["open", path])   # macOS
                else:
                    subprocess.run(["xdg-open", path])  # Linux
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı:\n{e}")
        else:
            messagebox.showwarning("Uyarı", "Dosya henüz oluşturulmadı veya bulunamadı.")
    # ──────────────────────────────────────────────
    # GRAFİK
    # ──────────────────────────────────────────────
    def _show_graph(self):
        if not HAS_MPL:
            messagebox.showerror(
                "Eksik Kütüphane",
                "Grafik için matplotlib gerekli.\n\n"
                "Kurmak için terminale şunu yazın:\n"
                "  pip install matplotlib"
            )
            return
        path = self.save_path.get()
        if not os.path.exists(path):
            messagebox.showwarning("Uyarı", "Henüz kaydedilmiş veri yok.")
            return
        # ── Dosyayı oku ve ayrıştır ──────────────────
        timestamps = []
        series: dict[str, list] = {}   # {etiket: [değerler]}
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Zaman damgasını çıkar: [2025-06-25 16:35:00]
                ts_match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(.*)", line)
                if not ts_match:
                    continue
                try:
                    ts = datetime.datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                raw_data = ts_match.group(2).strip()
                # Birden fazla alan: "Sicaklik:25.3 Nem:60.1" veya "25.3,60.1"
                # Her sayısal değeri ayrı seri olarak sakla
                found_any = False
                # Önce key:value çiftlerini dene
                kv_pairs = re.findall(r'([\w\u00c0-\u024f]+)\s*[:=]\s*([+-]?\d+\.?\d*)', raw_data)
                if kv_pairs:
                    for key, val in kv_pairs:
                        if key not in series:
                            series[key] = []
                        series[key].append((ts, float(val)))
                    found_any = True
                if not found_any:
                    # Sadece sayı(lar) varsa
                    numbers = re.findall(r'[+-]?\d+\.?\d*', raw_data)
                    for i, n in enumerate(numbers):
                        key = f"Kanal {i+1}" if len(numbers) > 1 else "Değer"
                        if key not in series:
                            series[key] = []
                        series[key].append((ts, float(n)))
        if not series:
            messagebox.showinfo(
                "Veri Yok",
                "Dosyada çizilecek sayısal veri bulunamadı.\n\n"
                "Beklenen format:\n"
                "  [tarih saat] Sicaklik:25.3\n"
                "  [tarih saat] 25.3"
            )
            return
        # ── Grafik penceresi ─────────────────────────
        win = tk.Toplevel(self.root)
        win.title("📈  Veri Grafiği")
        win.geometry("1000x600")
        win.configure(bg=BG_DARK)
        win.grab_set()
        # Matplotlib dark fig
        colors = ["#58a6ff", "#3fb950", "#f78166", "#d29922",
                  "#bc8cff", "#ff7b72", "#79c0ff", "#56d364"]
        fig = Figure(figsize=(10, 5), dpi=100, facecolor=BG_DARK)
        ax  = fig.add_subplot(111, facecolor="#010409")
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["top"].set_color(BORDER)
        ax.spines["left"].set_color(BORDER)
        ax.spines["right"].set_color(BORDER)
        ax.xaxis.label.set_color(TEXT_SECONDARY)
        ax.yaxis.label.set_color(TEXT_SECONDARY)
        ax.title.set_color(TEXT_PRIMARY)
        ax.grid(True, color=BORDER, linestyle="--", linewidth=0.5, alpha=0.7)
        for idx, (label, pts) in enumerate(series.items()):
            pts.sort(key=lambda x: x[0])
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            color = colors[idx % len(colors)]
            ax.plot(xs, ys, marker="o", markersize=4, linewidth=2,
                    color=color, label=label)
        # X ekseni: otomatik tarih formatı
        fig.autofmt_xdate()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax.set_title("STM32 Sensör Verileri", fontsize=12, pad=12, color=TEXT_PRIMARY)
        ax.set_xlabel("Zaman", fontsize=9, color=TEXT_SECONDARY)
        ax.set_ylabel("Değer", fontsize=9, color=TEXT_SECONDARY)
        if len(series) > 1:
            leg = ax.legend(facecolor=BG_CARD2, edgecolor=BORDER,
                            labelcolor=TEXT_PRIMARY, fontsize=9)
        fig.tight_layout(pad=1.5)
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        # Toolbar (zoom, pan, kaydet)
        toolbar_frame = tk.Frame(win, bg=BG_CARD2)
        toolbar_frame.pack(fill="x", side="bottom")
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.config(background=BG_CARD2)
        toolbar._message_label.config(background=BG_CARD2, foreground=TEXT_SECONDARY)
        for child in toolbar.winfo_children():
            try:
                child.config(background=BG_CARD2)
            except Exception:
                pass
        toolbar.update()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)
        # Bilgi etiketi
        total_pts = sum(len(v) for v in series.values())
        info = tk.Label(
            win,
            text=f"  {total_pts} veri noktası  •  {len(series)} seri  "
                 f"  |  Zoom: kaydır  •  Pan: sürükle  •  💾 Kaydet: toolbar",
            font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_DARK, anchor="w"
        )
        info.pack(fill="x", padx=6, pady=(0, 4))
    def _clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")
        self._log("Terminal temizlendi.", "info")
    # ──────────────────────────────────────────────
    # KAPAT
    # ──────────────────────────────────────────────
    def on_close(self):
        if self.is_running:
            self._disconnect()
        self.root.destroy()
# ──────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        root = tk.Tk()
        # ttk stil
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=BG_CARD2, background=BG_CARD2,
                        foreground=TEXT_PRIMARY, selectbackground=ACCENT2,
                        selectforeground=TEXT_PRIMARY, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, arrowcolor=TEXT_SECONDARY)
        style.map("TCombobox",
                  fieldbackground=[("readonly", BG_CARD2)],
                  foreground=[("readonly", TEXT_PRIMARY)])
        app = STM32Logger(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
    except Exception:
        # --windowed modunda hatalar görünmez; bu sayede ekranda gösterilir
        import traceback
        err = traceback.format_exc()
        try:
            # Tkinter penceresi açılmışsa messagebox kullan
            import tkinter.messagebox as mb
            mb.showerror(
                "Uygulama Hatası",
                f"Program başlatılırken bir hata oluştu:\n\n{err}\n\n"
                "Bu mesajı bir ekran görüntüsü alarak geliştiriciye iletin."
            )
        except Exception:
            pass
        # Hata logunu masaüstüne de kaydet
        try:
            log_path = os.path.join(os.path.expanduser("~"), "Desktop", "stm32_hata.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
