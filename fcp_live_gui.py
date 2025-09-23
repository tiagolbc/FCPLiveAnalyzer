import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import sounddevice as sd
from tkinter import filedialog
from scipy.io import wavfile
from scipy.signal import resample
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from fcp_ltas import compute_ltas_like_praat, compute_fcp_praat_style, get_fcp_color
from fcp_voiced_ltas import compute_ltas_voiced_like_praat, extract_only_voiced_segments
import parselmouth
import sys
import threading
import time
import os
from PIL import Image, ImageTk
import csv
import statistics
from PIL import Image, ImageTk
import soundfile as sf
from splash import show_splash_screen
import sys
from datetime import datetime  # for timestamped export folders

FS = 44100
BUFFER_SECS = 1
LTAS_BANDWIDTH = 350
UPDATE_INTERVAL = 0.1
BUFFER_SIZE = int(FS * BUFFER_SECS)
AUDIO_DTYPE = 'int16'

COLOR_CODES = [
    ('0–5 dB', '#1f77b4'),      # blue
    ('5–10 dB', '#2ca02c'),     # green
    ('10–15 dB', '#ff7f0e'),    # orange
    ('15–20 dB', '#d62728')     # red
]

class FCPLiveGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FCP Live Analyzer")
        self.root.state('zoomed')
        self.running = False
        self.after_id = None
        self.audio_buffer = np.zeros(BUFFER_SIZE)
        self.input_devices = self.get_devices(kind='input')
        self.output_devices = self.get_devices(kind='output')
        self.selected_input = tk.StringVar(value=self.input_devices[0] if self.input_devices else '')
        self.selected_output = tk.StringVar(value=self.output_devices[0] if self.output_devices else '')
        self.analysis_history = []  # stores results for CSV (LIVE session)
        self.precomputed_buffer = []  # Precomputed FCP buffer (file playback only)
        self.playback_pointer = 0
        self.stop_playback = False  # stop flag used in stop_live()
        self.mode = 'idle'  # 'idle' | 'live' | 'playback'

        # 1. TOP BAR - buttons in one single row
        top_bar = tk.Frame(root, bg="#e6e6e6")
        top_bar.pack(side=tk.TOP, fill=tk.X)

        # Buttons (existing)
        self.live_button = ttk.Button(top_bar, text="LIVE", command=self.toggle_live)
        self.live_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.load_button = ttk.Button(top_bar, text="LOAD", command=self.load_audio)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.play_button = ttk.Button(top_bar, text="PLAY", command=self.play_loaded_audio, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.stop_button = ttk.Button(top_bar, text="STOP", command=lambda: self.stop_live(do_export=True),
                                      state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=10)

        # Batch analysis button (NEW)
        self.batch_button = ttk.Button(top_bar, text="BATCH", command=self.batch_analysis)
        self.batch_button.pack(side=tk.LEFT, padx=5, pady=10)

        tk.Label(top_bar, text="Microphone:", bg="#e6e6e6").pack(side=tk.LEFT, padx=(15, 2))
        self.input_menu = ttk.Combobox(top_bar, values=self.input_devices, textvariable=self.selected_input,
                                       state="readonly", width=35)
        self.input_menu.pack(side=tk.LEFT, padx=2)
        tk.Label(top_bar, text="Output:", bg="#e6e6e6").pack(side=tk.LEFT, padx=(15, 2))
        self.output_menu = ttk.Combobox(top_bar, values=self.output_devices, textvariable=self.selected_output,
                                        state="readonly", width=35)
        self.output_menu.pack(side=tk.LEFT, padx=2)

        # Right-aligned actions (existing + NEW)
        self.exit_button = ttk.Button(top_bar, text="EXIT", command=self.on_exit)
        self.exit_button.pack(side=tk.RIGHT, padx=7)
        self.about_button = ttk.Button(top_bar, text="ABOUT", command=self.show_about)
        self.about_button.pack(side=tk.RIGHT, padx=7)

        # Screenshot button (NEW)
        self.screenshot_button = ttk.Button(top_bar, text="SCREENSHOT", command=self.save_screenshot)
        self.screenshot_button.pack(side=tk.RIGHT, padx=7)

        # Existing CSV export (manual)
        self.export_button = ttk.Button(top_bar, text="EXPORT CSV", command=self.export_csv)
        self.export_button.pack(side=tk.RIGHT, padx=7)

        # 2. LOGO + FCP DISPLAY ROW
        header_row = tk.Frame(root, bg="#e6e6e6")
        header_row.pack(side=tk.TOP, fill=tk.X)

        # --- Logo (left) ---
        logo_frame = tk.Frame(header_row, bg="#e6e6e6", width=170, height=95)
        logo_frame.pack(side=tk.LEFT, anchor="n", fill=tk.Y)
        logo_frame.pack_propagate(False)
        self.logo_img = Image.open("logo_fcp.png")
        self.logo_img = self.logo_img.resize((150, 150), Image.LANCZOS)
        self.logo_tk = ImageTk.PhotoImage(self.logo_img)
        tk.Label(logo_frame, image=self.logo_tk, bg="#e6e6e6").pack(side=tk.TOP, pady=10, padx=(10, 0))

        # --- FCP central display + legend ---
        center_frame = tk.Frame(header_row, bg="#e6e6e6")
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fcp_label = tk.Label(center_frame, text="FCP = -- dB", font=("Calibri", 22, "bold"), fg="gray",
                                  bg="#e6e6e6")
        self.fcp_label.pack(pady=(10, 2))
        self.fcp_mean_label = tk.Label(center_frame, text="Mean FCP = -- dB", font=("Calibri", 16, "bold"),
                                       fg="#444444", bg="#e6e6e6")
        self.fcp_mean_label.pack(pady=(2, 8))
        legend_frame = tk.Frame(center_frame, bg="#e6e6e6")
        legend_frame.pack()
        tk.Label(legend_frame, text="FCP color legend:", font=("Calibri", 10, "bold"), bg="#e6e6e6").grid(row=0,
                                                                                                          column=0,
                                                                                                          columnspan=2,
                                                                                                          pady=(0, 2))
        for i, (label, color) in enumerate(COLOR_CODES, 1):
            box = tk.Label(legend_frame, width=2, height=1, bg=color)
            box.grid(row=i, column=0, padx=3)
            tk.Label(legend_frame, text=label, font=("Calibri", 10), bg="#e6e6e6").grid(row=i, column=1, sticky='w')

        # --- Spectral plot (center) ---
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
        self.plot_initialized = False

        self.stream = None

    def fill_band_exact_2_4kHz(self, freqs, ltas, color, label="2-4kHz band"):
        """
        Fill the region between 2kHz and 4kHz using linear interpolation for exact boundaries.
        """
        band_start = 2000
        band_end = 4000
        # Mask for points strictly inside the band
        mask = (freqs > band_start) & (freqs < band_end)
        # Interpolate at boundaries if needed
        freq_interp = np.concatenate((
            [band_start],
            freqs[mask],
            [band_end]
        ))
        ltas_interp = np.concatenate((
            [np.interp(band_start, freqs, ltas)],
            ltas[mask],
            [np.interp(band_end, freqs, ltas)]
        ))
        ylim_low = self.ax.get_ylim()[0]
        self.ax.fill_between(
            freq_interp,
            ltas_interp,
            y2=ylim_low,
            color=color, alpha=0.5, label=label
        )

    def get_devices(self, kind='input'):
        devices = []
        default_idx = sd.default.device[0] if kind == 'input' else sd.default.device[1]
        for idx, dev in enumerate(sd.query_devices()):
            if (kind == 'input' and dev['max_input_channels'] > 0) or (kind == 'output' and dev['max_output_channels'] > 0):
                devices.append(f"{dev['name']} (index {idx})")
        # Prefer default device first
        if devices and default_idx is not None and 0 <= default_idx < len(sd.query_devices()):
            def_name = sd.query_devices(default_idx)['name']
            default_str = f"{def_name} (index {default_idx})"
            if default_str in devices:
                devices.remove(default_str)
                devices.insert(0, default_str)
        return devices

    def get_device_index(self, device_name):
        if "(index" in device_name:
            return int(device_name.split("(index")[1].split(")")[0])
        return None

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if indata.shape[1] > 0:
            self.audio_buffer = np.roll(self.audio_buffer, -frames)
            self.audio_buffer[-frames:] = indata[:, 0]

    def toggle_live(self):
        if not self.running:
            self.start_live()
        else:
            self.stop_live()

    def start_live(self):
        input_idx = self.get_device_index(self.selected_input.get())
        self.analysis_history.clear()
        self.fcp_mean_label.config(text="Mean FCP = -- dB")
        if input_idx is None:
            messagebox.showerror("Error", "Please select a valid microphone/input device.")
            return
        # Stop previous stream if any
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
        self.stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=FS,
                                     blocksize=int(FS * UPDATE_INTERVAL), dtype=AUDIO_DTYPE, device=input_idx)
        self.stream.start()
        self.running = True
        self.live_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.mode = 'live'

        self.update_plot()

    def stop_live(self, *, do_export=True):
        """
        Stop LIVE or PLAYBACK. Auto-export only if this stop comes from LIVE mode.
        """
        self.running = False
        self.stop_playback = True
        sd.stop()
        self.live_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        # ---- Auto-export ONLY for LIVE sessions ----
        try:
            if do_export and (self.mode == 'live') and self.analysis_history:
                out_dir = self._ensure_exports_dir(prefix="Live")
                # CSV e (opcional) Excel a partir do histórico do LIVE
                self._export_csv_to_path(self.analysis_history, os.path.join(out_dir, "fcp_live.csv"))
                self._export_excel_optional(self.analysis_history, os.path.join(out_dir, "fcp_live.xlsx"))
                # Plot de evolução (LIVE usa índice * UPDATE_INTERVAL)
                self._save_fcp_evolution_plot(self.analysis_history,
                                              source="live",
                                              png_path=os.path.join(out_dir, "fcp_evolution.png"))
                # LTAS
                self.fig.savefig(os.path.join(out_dir, "ltas_current.png"), dpi=300)
                messagebox.showinfo("Export", f"Auto-export completed:\n{out_dir}")
        except Exception as e:
            messagebox.showwarning("Export warning", f"Auto-export skipped or failed:\n{e}")


    def load_audio(self):
        # Stop anything running, but DO NOT export when simply preparing to load a file
        self.stop_live(do_export=False)
        self.analysis_history.clear()
        self.precomputed_buffer = []
        self.playback_pointer = 0

        wav_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if not wav_path:
            return
        self.loaded_audio_filename = os.path.basename(wav_path)
        try:
            fs, data = wavfile.read(wav_path)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if fs != FS:
                n_samples = int(len(data) * FS / fs)
                data = resample(data, n_samples)
                fs = FS
            data = data.astype(np.float64)
            self.loaded_audio_data = data
            self.loaded_audio_fs = fs
            # --- Precompute all FCP windows ---
            win_samples = int(BUFFER_SECS * FS)
            step_samples = int(UPDATE_INTERVAL * FS)
            total_len = len(data)
            # Show message while processing
            self.fcp_label.config(text="Processing audio...", fg="gray")
            self.fcp_mean_label.config(text="Global FCP = -- dB")
            self.root.update()
            for start in range(0, total_len - win_samples + 1, step_samples):
                buf = data[start:start + win_samples]
                freqs, ltas = compute_ltas_voiced_like_praat(buf, fs, bandwidth=LTAS_BANDWIDTH)
                if len(ltas) < 1 or np.isnan(ltas).all():
                    continue  # skip windows without enough voiced audio
                Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, fcp, trend_at_fcp_peak = compute_fcp_praat_style(freqs, ltas)
                self.precomputed_buffer.append({
                    "filename": self.loaded_audio_filename,
                    "window_start_sec": start / fs,
                    "window_end_sec": (start + win_samples) / fs,
                    "Lmax_0_2": Lmax_0_2,
                    "Lmax_2_5": Lmax_2_5,
                    "Lmax_5_8": Lmax_5_8,
                    "Lmax_2_4": Lmax_2_4,
                    "FCP": fcp,
                    "Trend_at_FCP_Peak": trend_at_fcp_peak,
                    "Delta_0_2_2_5": Lmax_2_5 - Lmax_0_2,
                    "Delta_2_5_5_8": Lmax_5_8 - Lmax_2_5,
                    "Delta_0_2_5_8": Lmax_5_8 - Lmax_0_2,
                    "Delta_2_4": Lmax_2_4,
                    "freqs": freqs,
                    "ltas": ltas
                })

            # Show preview of first window (dynamic FCP) and true global FCP (over all voiced)
            if self.precomputed_buffer:
                first = self.precomputed_buffer[0]
                color = get_fcp_color(first['FCP'])
                self.fcp_label.config(text=f"FCP = {first['FCP']:.2f} dB", fg=color)

                # ------ Global FCP: calculate only on all voiced audio concatenated ------
                voiced_full = extract_only_voiced_segments(self.loaded_audio_data, self.loaded_audio_fs)
                if len(voiced_full) >= int(0.2 * self.loaded_audio_fs):  # at least 200 ms voiced
                    freqs_full, ltas_full = compute_ltas_like_praat(voiced_full, self.loaded_audio_fs,
                                                                    bandwidth=LTAS_BANDWIDTH)
                    _, _, _, _, global_fcp, _ = compute_fcp_praat_style(freqs_full, ltas_full)
                    self.fcp_mean_label.config(text=f"Global FCP = {global_fcp:.2f} dB")
                else:
                    self.fcp_mean_label.config(text="Global FCP = -- dB")

                # Update LTAS display (first window)
                freqs, ltas = compute_ltas_voiced_like_praat(self.loaded_audio_data[:win_samples], fs,
                                                             bandwidth=LTAS_BANDWIDTH)
                self.ax.clear()
                self.ax.plot(freqs, ltas, color='black')
                self.ax.set_xlim(0, 8000)
                self.ax.set_ylim(0, 140)
                self.fill_band_exact_2_4kHz(freqs, ltas, color)
                self.ax.set_xlabel("Frequency (Hz)")
                self.ax.set_ylabel("Relative intensity (dB)")
                self.ax.set_title(f"LTAS (Loaded file: {self.loaded_audio_filename}, voiced only)", fontsize=16)
                self.ax.legend()
                self.canvas.draw()
                self.play_button.config(state=tk.NORMAL)
                self.export_button.config(state=tk.NORMAL)
                messagebox.showinfo("Ready", "Audio loaded and processed. Ready to play!")
                self.mode = 'idle'

            else:
                self.fcp_label.config(text="FCP = -- dB", fg='gray')
                self.fcp_mean_label.config(text="Global FCP = -- dB")
                self.play_button.config(state=tk.DISABLED)
                self.export_button.config(state=tk.DISABLED)
                messagebox.showwarning("No voiced data", "No voiced segments found in any window.")

        except Exception as e:
            messagebox.showerror("Error loading audio", f"Could not load audio file.\n\n{e}")

    def play_loaded_audio(self):
        if not hasattr(self, 'loaded_audio_data') or self.loaded_audio_data is None:
            messagebox.showwarning("Warning", "No audio loaded.")
            return
        if not self.precomputed_buffer:
            messagebox.showwarning("Warning", "No precomputed analysis buffer found.")
            return

        audio = self.loaded_audio_data.astype(np.float32)
        fs = self.loaded_audio_fs
        if fs != FS:
            n_samples = int(len(audio) * FS / fs)
            audio = resample(audio, n_samples)
            fs = FS
        if hasattr(audio, "ndim") and audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        audio = audio / np.max(np.abs(audio) + 1e-6)

        self.stop_playback = False
        self.mode = 'playback'
        self.stop_button.config(state=tk.NORMAL)
        self.live_button.config(state=tk.DISABLED)

        win_samples = int(BUFFER_SECS * FS)
        step_samples = int(UPDATE_INTERVAL * FS)
        n_windows = len(self.precomputed_buffer)
        playback_pointer = [0]
        audio_len = len(audio)

        def audio_callback(outdata, frames, time_info, status):
            if self.stop_playback or playback_pointer[0] >= audio_len:
                outdata[:] = np.zeros((frames, 1))
                raise sd.CallbackStop()
            chunk = audio[playback_pointer[0]:playback_pointer[0] + frames]
            if len(chunk) < frames:
                chunk = np.pad(chunk, (0, frames - len(chunk)))
            outdata[:, 0] = chunk
            playback_pointer[0] += frames

        def update_display():
            window_idx = int(playback_pointer[0] / step_samples)
            if 0 <= window_idx < n_windows:
                buf = self.precomputed_buffer[window_idx]
                color = get_fcp_color(buf['FCP'])
                self.fcp_label.config(text=f"FCP = {buf['FCP']:.2f} dB", fg=color)

                # Dynamic LTAS update
                self.ax.clear()
                freqs, ltas = buf['freqs'], buf['ltas']
                self.ax.plot(freqs, ltas, color='black')
                self.ax.set_xlim(0, 8000)
                self.ax.set_ylim(0, 140)
                self.fill_band_exact_2_4kHz(freqs, ltas, color)
                self.ax.set_xlabel("Frequency (Hz)")
                self.ax.set_ylabel("Relative intensity (dB)")
                self.ax.set_title(f"LTAS (Playback: {self.loaded_audio_filename})", fontsize=16)
                self.ax.legend()
                self.canvas.draw()

            if not self.stop_playback and playback_pointer[0] < audio_len:
                self.root.after(int(UPDATE_INTERVAL * 1000), update_display)
            else:
                self.fcp_label.config(text="FCP = -- dB", fg="gray")

        def run_playback():
            try:
                with sd.OutputStream(samplerate=FS, channels=1, blocksize=2048, callback=audio_callback):
                    # schedule UI updates
                    self.root.after(0, update_display)
                    sd.sleep(int(len(audio) / FS * 1000))
            except Exception as e:
                print("Playback stopped or error:", e)
            finally:
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.live_button.config(state=tk.NORMAL))
                self.stop_playback = False
                self.mode = 'idle'

        t = threading.Thread(target=run_playback)
        t.daemon = True
        t.start()

    def update_plot(self):
        if not self.running:
            return
        freqs, ltas = compute_ltas_like_praat(self.audio_buffer, FS, bandwidth=LTAS_BANDWIDTH)
        Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, fcp, trend_at_fcp_peak = compute_fcp_praat_style(freqs, ltas)
        color = get_fcp_color(fcp)
        self.analysis_history.append({
            "filename": "LIVE",
            "Lmax_0_2": Lmax_0_2,
            "Lmax_2_5": Lmax_2_5,
            "Lmax_5_8": Lmax_5_8,
            "Lmax_2_4": Lmax_2_4,
            "FCP": fcp,
            "Delta_0_2_2_5": Lmax_2_5 - Lmax_0_2,
            "Delta_2_5_5_8": Lmax_5_8 - Lmax_2_5,
            "Delta_0_2_5_8": Lmax_5_8 - Lmax_0_2,
            "Delta_2_4": Lmax_2_4
        })
        self.ax.clear()
        # Plot LTAS
        self.ax.plot(freqs, ltas, color='black')
        # Highlight the 2–4 kHz band
        self.ax.set_xlim(0, 8000)
        self.ax.set_ylim(0, 140)
        self.fill_band_exact_2_4kHz(freqs, ltas, color)
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Relative intensity (dB)")
        self.ax.set_title("Long-Term Average Spectrum", fontsize=16)
        self.ax.legend()
        # Update FCP label with color
        if np.isnan(fcp):
            self.fcp_label.config(text="FCP = -- dB", fg='gray')
        else:
            self.fcp_label.config(text=f"FCP = {fcp:.1f} dB", fg=color)

        valid_fcps = [row["FCP"] for row in self.analysis_history if not np.isnan(row["FCP"])]
        if valid_fcps:
            mean_fcp = np.mean(valid_fcps)
            self.fcp_mean_label.config(text=f"Mean FCP = {mean_fcp:.2f} dB")
        else:
            self.fcp_mean_label.config(text="Mean FCP = -- dB")
        self.canvas.draw()
        self.after_id = self.root.after(int(UPDATE_INTERVAL * 1000), self.update_plot)

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def on_exit(self):
        self.running = False
        self.stop_stream()
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.root.destroy()
        sys.exit(0)

    # --------- EXISTING manual CSV export (unchanged signature) ---------
    def export_csv(self):
        fieldnames = [
            "filename", "window_start_sec", "window_end_sec",
            "Lmax_0_2", "Lmax_2_5", "Lmax_5_8", "Lmax_2_4",
            "FCP", "Trend_at_FCP_Peak",
            "Delta_0_2_2_5", "Delta_2_5_5_8",
            "Delta_0_2_5_8", "Delta_2_4"
        ]

        export_data = self.precomputed_buffer if self.precomputed_buffer else self.analysis_history

        if not export_data:
            messagebox.showinfo("Export", "No analysis data to export.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save FCP Analysis Data"
        )
        if not save_path:
            return

        # Delegate to helper that writes and appends a global means row
        self._export_csv_to_path(export_data, save_path)
        messagebox.showinfo("Export", f"CSV file saved:\n{save_path}")

    # -------------------- Screenshot button handler --------------------
    def save_screenshot(self):
        """
        Save a PNG of the current LTAS figure via a file dialog.
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")],
            title="Save Screenshot (LTAS figure)"
        )
        if not file_path:
            return
        try:
            self.fig.savefig(file_path, dpi=300)
            messagebox.showinfo("Screenshot", f"Saved:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Screenshot error", f"Could not save screenshot:\n{e}")

    # -------------------- Batch analysis (enhanced) --------------------
    def batch_analysis(self):
        """
        Analyze multiple WAV files at once.
        Exports:
          - batch_summary.csv : one row per file with global FCP and summary stats
          - batch_windows.csv : per-window data (FCP etc.) for each file
          - per-file images in subfolders:
              * fcp_evolution.png (FCP vs time)
              * ltas_current.png  (global voiced-only LTAS with 2–4 kHz highlight)
          - (optional) Excel versions if pandas is available
        """
        wav_paths = filedialog.askopenfilenames(title="Select WAV files for batch analysis",
                                                filetypes=[("WAV files", "*.wav")])
        if not wav_paths:
            return

        out_dir = self._ensure_exports_dir(prefix="Batch")
        summary_rows = []
        per_window_rows = []

        try:
            for path in wav_paths:
                file_name = os.path.basename(path)
                file_stub = os.path.splitext(file_name)[0]
                file_dir = os.path.join(out_dir, file_stub)
                os.makedirs(file_dir, exist_ok=True)

                try:
                    fs0, data = wavfile.read(path)
                    if data.ndim > 1:
                        data = np.mean(data, axis=1)
                    if fs0 != FS:
                        n_samples = int(len(data) * FS / fs0)
                        data = resample(data, n_samples)
                        fs = FS
                    else:
                        fs = fs0
                    data = data.astype(np.float64)

                    # Global voiced-only LTAS & FCP
                    freqs_full = None
                    ltas_full = None
                    voiced_full = extract_only_voiced_segments(data, fs)
                    if len(voiced_full) >= int(0.2 * fs):
                        freqs_full, ltas_full = compute_ltas_like_praat(voiced_full, fs, bandwidth=LTAS_BANDWIDTH)
                        L0_2, L2_5, L5_8, L2_4, global_fcp, trend_at_peak = compute_fcp_praat_style(freqs_full, ltas_full)
                    else:
                        # Not enough voiced audio; mark as NaN
                        L0_2 = L2_5 = L5_8 = L2_4 = global_fcp = trend_at_peak = np.nan

                    # Sliding windows per-file
                    win_samples = int(BUFFER_SECS * fs)
                    step_samples = int(UPDATE_INTERVAL * fs)
                    n = len(data)
                    window_fcps = []
                    file_window_rows = []  # keep a per-file copy for local plots
                    for start in range(0, n - win_samples + 1, step_samples):
                        buf = data[start:start + win_samples]
                        freqs, ltas = compute_ltas_voiced_like_praat(buf, fs, bandwidth=LTAS_BANDWIDTH)
                        if len(ltas) < 1 or np.isnan(ltas).all():
                            continue
                        Lw0_2, Lw2_5, Lw5_8, Lw2_4, fcp_w, _ = compute_fcp_praat_style(freqs, ltas)
                        row = {
                            "filename": file_name,
                            "window_start_sec": start / fs,
                            "window_end_sec": (start + win_samples) / fs,
                            "Lmax_0_2": Lw0_2,
                            "Lmax_2_5": Lw2_5,
                            "Lmax_5_8": Lw5_8,
                            "Lmax_2_4": Lw2_4,
                            "FCP": fcp_w,
                            "Delta_0_2_2_5": Lw2_5 - Lw0_2,
                            "Delta_2_5_5_8": Lw5_8 - Lw2_5,
                            "Delta_0_2_5_8": Lw5_8 - Lw0_2,
                            "Delta_2_4": Lw2_4
                        }
                        per_window_rows.append(row)
                        file_window_rows.append(row)
                        window_fcps.append(fcp_w)

                    # Summary stats per file (based on windows)
                    mean_fcp = float(np.nanmean(window_fcps)) if window_fcps else np.nan
                    sd_fcp = float(np.nanstd(window_fcps, ddof=1)) if len(window_fcps) > 1 else np.nan
                    duration_sec = len(data) / fs

                    summary_rows.append({
                        "filename": file_name,
                        "duration_sec": round(duration_sec, 3),
                        "global_Lmax_0_2": L0_2,
                        "global_Lmax_2_5": L2_5,
                        "global_Lmax_5_8": L5_8,
                        "global_Lmax_2_4": L2_4,
                        "global_FCP": global_fcp,
                        "global_Trend_at_FCP_Peak": trend_at_peak,
                        "windows_mean_FCP": mean_fcp,
                        "windows_sd_FCP": sd_fcp,
                        "windows_count": len(window_fcps)
                    })

                    # --- NEW: per-file plots in its own folder ---
                    # 1) FCP evolution over time (only if we have windows)
                    if file_window_rows:
                        self._save_fcp_evolution_plot(file_window_rows,
                                                      source="precomputed",
                                                      png_path=os.path.join(file_dir, "fcp_evolution.png"))

                    # 2) Global voiced-only LTAS with band highlight (if available)
                    if freqs_full is not None and ltas_full is not None and not np.isnan(global_fcp):
                        band_color = get_fcp_color(global_fcp)
                        title = f"LTAS (Global voiced-only) – {file_name}"
                        self._save_ltas_plot_standalone(
                            freqs_full, ltas_full, band_color, title,
                            os.path.join(file_dir, "ltas_current.png"),
                            fcp_value=global_fcp
                        )

                except Exception as file_err:
                    summary_rows.append({
                        "filename": file_name,
                        "duration_sec": "NaN",
                        "global_Lmax_0_2": "NaN",
                        "global_Lmax_2_5": "NaN",
                        "global_Lmax_5_8": "NaN",
                        "global_Lmax_2_4": "NaN",
                        "global_FCP": "NaN",
                        "global_Trend_at_FCP_Peak": "NaN",
                        "windows_mean_FCP": "NaN",
                        "windows_sd_FCP": "NaN",
                        "windows_count": 0,
                        "error": str(file_err)
                    })

            # Write CSVs
            summary_csv = os.path.join(out_dir, "batch_summary.csv")
            windows_csv = os.path.join(out_dir, "batch_windows.csv")
            self._write_rows_to_csv(summary_rows, summary_csv)
            self._write_rows_to_csv(per_window_rows, windows_csv)

            # Optional: write Excel if pandas is available
            self._export_batch_excel_optional(summary_rows, per_window_rows, os.path.join(out_dir, "batch_results.xlsx"))

            messagebox.showinfo("Batch", f"Batch analysis completed.\n\nFolder:\n{out_dir}\n\n"
                                         f"- {os.path.basename(summary_csv)}\n"
                                         f"- {os.path.basename(windows_csv)}\n"
                                         f"+ Per-file images in subfolders")

        except Exception as e:
            messagebox.showerror("Batch error", f"Batch analysis failed:\n{e}")

    # -------------------- Helpers for exports & plots --------------------
    def _ensure_exports_dir(self, prefix="Export"):
        """
        Create a timestamped directory under ./Exports/ and return its path.
        """
        base = "Exports"
        os.makedirs(base, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(base, f"{prefix}_{ts}")
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _export_csv_to_path(self, export_data, save_path):
        """
        Write export_data (list of dicts) to CSV including a final 'Global Mean' row
        when numeric fields exist.
        """
        fieldnames = [
            "filename", "window_start_sec", "window_end_sec",
            "Lmax_0_2", "Lmax_2_5", "Lmax_5_8", "Lmax_2_4",
            "FCP", "Trend_at_FCP_Peak",
            "Delta_0_2_2_5", "Delta_2_5_5_8",
            "Delta_0_2_5_8", "Delta_2_4"
        ]
        with open(save_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            # Only write allowed keys
            for row in export_data:
                row_filtered = {k: row[k] for k in fieldnames if k in row}
                writer.writerow(row_filtered)
            # Global means
            global_means = {"filename": "Global Mean"}
            numeric_fields = [
                "Lmax_0_2", "Lmax_2_5", "Lmax_5_8", "Lmax_2_4",
                "FCP", "Trend_at_FCP_Peak",
                "Delta_0_2_2_5", "Delta_2_5_5_8",
                "Delta_0_2_5_8", "Delta_2_4"
            ]
            for field in numeric_fields:
                values = [row[field] for row in export_data if field in row and not np.isnan(row[field])]
                global_means[field] = round(np.mean(values), 2) if values else "NaN"
            writer.writerow(global_means)

    def _write_rows_to_csv(self, rows, path):
        """
        Write arbitrary list[dict] rows to CSV with inferred headers.
        """
        if not rows:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                pass
            return
        # infer headers from union of keys preserving a reasonable order
        keys = set()
        for r in rows:
            keys.update(r.keys())
        ordered = ["filename"] + sorted(k for k in keys if k != "filename")
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ordered)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in ordered})

    def _export_excel_optional(self, export_data, xlsx_path):
        """
        Try to write export_data into an Excel file. If pandas is not available, silently skip.
        """
        try:
            import pandas as pd
            # normalize list of dicts to DataFrame with the standard columns
            fieldnames = [
                "filename", "window_start_sec", "window_end_sec",
                "Lmax_0_2", "Lmax_2_5", "Lmax_5_8", "Lmax_2_4",
                "FCP", "Trend_at_FCP_Peak",
                "Delta_0_2_2_5", "Delta_2_5_5_8",
                "Delta_0_2_5_8", "Delta_2_4"
            ]
            df = pd.DataFrame([{k: row.get(k, np.nan) for k in fieldnames} for row in export_data])
            # Global means row
            numeric_fields = [
                "Lmax_0_2", "Lmax_2_5", "Lmax_5_8", "Lmax_2_4",
                "FCP", "Trend_at_FCP_Peak",
                "Delta_0_2_2_5", "Delta_2_5_5_8",
                "Delta_0_2_5_8", "Delta_2_4"
            ]
            if not df.empty:
                means = {"filename": "Global Mean"}
                for nf in numeric_fields:
                    vals = pd.to_numeric(df[nf], errors='coerce')
                    means[nf] = round(vals.mean(), 2)
                df_means = pd.DataFrame([means])
                with pd.ExcelWriter(xlsx_path, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="data")
                    df_means.to_excel(writer, index=False, sheet_name="summary")
        except Exception:
            # quietly skip if pandas/xlsxwriter is not available
            pass

    def _export_batch_excel_optional(self, summary_rows, window_rows, xlsx_path):
        """
        Write batch results to Excel with two sheets if pandas is available.
        """
        try:
            import pandas as pd
            df_summary = pd.DataFrame(summary_rows)
            df_windows = pd.DataFrame(window_rows)
            with pd.ExcelWriter(xlsx_path, engine='xlsxwriter') as writer:
                df_summary.to_excel(writer, index=False, sheet_name="summary")
                df_windows.to_excel(writer, index=False, sheet_name="windows")
        except Exception:
            pass

    def _save_fcp_evolution_plot(self, data_rows, source, png_path):
        """
        Save a PNG plotting FCP over time.
        - source='precomputed': use window_start_sec/window_end_sec
        - source='live': use sequential index * UPDATE_INTERVAL
        """
        times = []
        fcps = []
        if source == "precomputed":
            for r in data_rows:
                if ("FCP" in r) and (not np.isnan(r["FCP"])):
                    if "window_start_sec" in r and "window_end_sec" in r:
                        t = 0.5 * (r["window_start_sec"] + r["window_end_sec"])
                    else:
                        t = np.nan
                    times.append(t)
                    fcps.append(r["FCP"])
        else:  # live
            for i, r in enumerate(data_rows):
                if ("FCP" in r) and (not np.isnan(r["FCP"])):
                    t = i * UPDATE_INTERVAL
                    times.append(t)
                    fcps.append(r["FCP"])

        if not fcps:
            return  # nothing to plot

        fig = plt.figure(figsize=(8, 3.5))
        ax = fig.add_subplot(111)
        ax.plot(times, fcps, linewidth=2)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("FCP (dB)")
        ax.set_title("FCP Evolution Over Time")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(png_path, dpi=300)
        plt.close(fig)

    def _save_ltas_plot_standalone(self, freqs, ltas, band_color, title, png_path, fcp_value=None):
        """
        Save a standalone LTAS plot with a highlighted 2–4 kHz band and given color.
        """
        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)
        ax.plot(freqs, ltas, color='black')
        ax.set_xlim(0, 8000)
        ax.set_ylim(0, 140)

        # Fill 2–4 kHz band with interpolation for exact boundaries
        band_start, band_end = 2000, 4000
        mask = (freqs > band_start) & (freqs < band_end)
        freq_interp = np.concatenate(([band_start], freqs[mask], [band_end]))
        ltas_interp = np.concatenate((
            [np.interp(band_start, freqs, ltas)],
            ltas[mask],
            [np.interp(band_end, freqs, ltas)]
        ))
        ax.fill_between(freq_interp, ltas_interp, y2=ax.get_ylim()[0],
                        color=band_color, alpha=0.5, label="2–4 kHz band")

        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Relative intensity (dB)")
        ax.set_title(title, fontsize=16)
        ax.legend()
        fig.tight_layout()

        # --- Overlay: Global FCP annotation (optional) ---
        try:
            if (fcp_value is not None) and (not np.isnan(fcp_value)):
                ax.text(
                    0.02, 0.95, f"Global FCP = {fcp_value:.2f} dB",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=12, fontweight="bold",
                    color=band_color,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=band_color, alpha=0.85)
                )
        except Exception:
            # Stay silent if np is not available or value is NaN, etc.
            pass

        fig.savefig(png_path, dpi=300)
        plt.close(fig)

    # -------------------- ABOUT (existing) -------------------------------
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About FCP Live Analyzer")
        about_win.configure(bg="#e6e6e6")
        about_win.resizable(False, False)
        about_win.geometry("900x700")  # Landscape style

        # Frame for text and scrollbar
        frame = tk.Frame(about_win, bg="#e6e6e6")
        frame.pack(expand=True, fill="both", padx=20, pady=18)

        # Scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        # Text widget
        text_widget = tk.Text(
            frame,
            wrap="word",
            font=("Calibri", 11),
            bg="#e6e6e6",
            relief="flat",
            width=85,
            height=20,
            yscrollcommand=scrollbar.set,
            state="normal"
        )

        about_text = (
            "FCP Live Analyzer is a free software tool developed to help singers monitor and train their vocal adjustments "
            "that facilitate the emergence of the 'singer's formant'—a unique resonance feature that enhances vocal projection "
            "and brilliance, especially in classical singing.\n\n"
            "This application implements the Formant Cluster Prominence (FCP) measure as described in the article:\n"
            "Lã, Filipa MB, Luciano S. Silva, and Svante Granqvist. “Long-term average spectrum characteristics of Portuguese Fado-Canção from Coimbra.” "
            "Journal of Voice 37, no. 4 (2023): 631-e7.\n\n"
            "What is FCP?\n"
            "FCP (Formant Cluster Prominence) is an acoustic metric that quantifies how prominent the cluster of higher formants (typically F3, F4, and F5) "
            "is in a singer’s spectrum, especially between 2–4 kHz. This “cluster” is critical for the so-called singer’s formant—a spectral feature that allows the singing voice to stand out over orchestral accompaniment.\n\n"
            "What is the singer’s formant?\n"
            "The singer’s formant is a resonance phenomenon characterized by a strong spectral peak between 2 and 4 kHz, allowing the singer’s voice to project and be heard clearly.\n"
            "For a deeper discussion, see:\n"
            "Sundberg J. Quarterly Progress and Status Report: The Singer’s Formant Revisited. 1995: 83–96.\n\n"
            "Purpose and use:\n"
            "This software is intended for singers, teachers, and researchers. It enables real-time and offline analysis of the FCP, empowering vocalists to adjust their technique and monitor the acoustic emergence of the singer’s formant during practice or performance.\n\n"
            "Author:\n"
            "Tiago Lima Bicalho Cruz, PhD\n"
            "Contact: fonotechacademy@gmail.com\n\n"
            "This software is provided free of charge."
        )

        text_widget.insert("1.0", about_text)
        text_widget.config(state="disabled")
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)

        # Close button
        tk.Button(
            about_win,
            text="Close",
            font=("Calibri", 12, "bold"),
            command=about_win.destroy,
            bg="#e6e6e6",
            relief="raised"
        ).pack(pady=(0, 18))

if __name__ == "__main__":
    def start_main_app():
        root = tk.Tk()
        import tkinter.font as tkFont
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(family="Calibri", size=11)
        app = FCPLiveGUI(root)
        try:
            root.mainloop()
        except KeyboardInterrupt:
            app.on_exit()

    show_splash_screen(start_main_app)
