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
        self.analysis_history = []  # stores results for CSV
        self.precomputed_buffer = []  # Buffer para FCP pré-computado (apenas arquivos)
        self.playback_pointer = 0

        # 1. TOP BAR - Apenas Botões (em uma linha)
        top_bar = tk.Frame(root, bg="#e6e6e6")
        top_bar.pack(side=tk.TOP, fill=tk.X)

        # Botões
        self.live_button = ttk.Button(top_bar, text="LIVE", command=self.toggle_live)
        self.live_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.load_button = ttk.Button(top_bar, text="LOAD", command=self.load_audio)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.play_button = ttk.Button(top_bar, text="PLAY", command=self.play_loaded_audio, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.stop_button = ttk.Button(top_bar, text="STOP", command=self.stop_live, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=10)
        tk.Label(top_bar, text="Microphone:", bg="#e6e6e6").pack(side=tk.LEFT, padx=(15, 2))
        self.input_menu = ttk.Combobox(top_bar, values=self.input_devices, textvariable=self.selected_input,
                                       state="readonly", width=35)
        self.input_menu.pack(side=tk.LEFT, padx=2)
        tk.Label(top_bar, text="Output:", bg="#e6e6e6").pack(side=tk.LEFT, padx=(15, 2))
        self.output_menu = ttk.Combobox(top_bar, values=self.output_devices, textvariable=self.selected_output,
                                        state="readonly", width=35)
        self.output_menu.pack(side=tk.LEFT, padx=2)
        self.exit_button = ttk.Button(top_bar, text="EXIT", command=self.on_exit)
        self.exit_button.pack(side=tk.RIGHT, padx=7)
        self.about_button = ttk.Button(top_bar, text="ABOUT", command=self.show_about)
        self.about_button.pack(side=tk.RIGHT, padx=7)
        self.export_button = ttk.Button(top_bar, text="EXPORT CSV", command=self.export_csv)
        self.export_button.pack(side=tk.RIGHT, padx=7)


        # 2. LOGO + FCP DISPLAY ROW
        header_row = tk.Frame(root, bg="#e6e6e6")
        header_row.pack(side=tk.TOP, fill=tk.X)

        # --- Logo à esquerda ---
        logo_frame = tk.Frame(header_row, bg="#e6e6e6", width=170, height=95)
        logo_frame.pack(side=tk.LEFT, anchor="n", fill=tk.Y)
        logo_frame.pack_propagate(False)
        self.logo_img = Image.open("logo_fcp.png")
        self.logo_img = self.logo_img.resize((150, 150), Image.LANCZOS)
        self.logo_tk = ImageTk.PhotoImage(self.logo_img)
        tk.Label(logo_frame, image=self.logo_tk, bg="#e6e6e6").pack(side=tk.TOP, pady=10, padx=(10, 0))

        # --- FCP CENTRAL DISPLAY + LEGENDA ---
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
        self.fig, self.ax = plt.subplots(figsize=(10,5))
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
        # Find mask for points strictly inside band
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
            self.audio_buffer[-frames:] = indata[:,0]

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
        self.stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=FS, blocksize=int(FS*UPDATE_INTERVAL), dtype=AUDIO_DTYPE, device=input_idx)
        self.stream.start()
        self.running = True
        self.live_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_plot()

    def stop_live(self):
        self.running = False
        self.stop_playback = True
        sd.stop()  # Para o áudio imediatamente
        self.live_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def load_audio(self):
        self.stop_live()
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
                    continue  # Skip windows without enough voiced audio
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
                    "Trend_at_FCP_Peak": trend_at_fcp_peak,  # <-- Adicione aqui
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
                from fcp_voiced_ltas import extract_only_voiced_segments

                voiced_full = extract_only_voiced_segments(self.loaded_audio_data, self.loaded_audio_fs)
                if len(voiced_full) >= int(0.2 * self.loaded_audio_fs):  # pelo menos 200 ms vozeados
                    freqs_full, ltas_full = compute_ltas_like_praat(voiced_full, self.loaded_audio_fs,
                                                                    bandwidth=LTAS_BANDWIDTH)
                    _, _, _, _, global_fcp, _ = compute_fcp_praat_style(freqs_full, ltas_full)
                    self.fcp_mean_label.config(text=f"Global FCP = {global_fcp:.2f} dB")
                else:
                    self.fcp_mean_label.config(text="Global FCP = -- dB")

                # Update LTAS display (primeira janela)
                freqs, ltas = compute_ltas_voiced_like_praat(self.loaded_audio_data[:win_samples], fs, bandwidth=LTAS_BANDWIDTH)
                self.ax.clear()
                self.ax.plot(freqs, ltas, color='black')
                self.ax.set_xlim(0, 8000)
                self.ax.set_ylim(-60, np.max(ltas) + 10 if np.max(ltas) > -50 else -50)
                self.fill_band_exact_2_4kHz(freqs, ltas, color)
                self.ax.set_xlabel("Frequency (Hz)")
                self.ax.set_ylabel("Relative intensity (dB)")
                self.ax.set_title(f"LTAS (Loaded file: {self.loaded_audio_filename}, voiced only)", fontsize=16)
                self.ax.legend()
                self.canvas.draw()
                self.play_button.config(state=tk.NORMAL)
                self.export_button.config(state=tk.NORMAL)
                messagebox.showinfo("Ready", "Audio loaded and processed. Ready to play!")
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

                # Atualizar LTAS DINÂMICO!
                self.ax.clear()
                freqs, ltas = buf['freqs'], buf['ltas']
                self.ax.plot(freqs, ltas, color='black')
                self.ax.set_xlim(0, 8000)
                self.ax.set_ylim(-60, np.max(ltas) + 10 if np.max(ltas) > -50 else -50)
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
                    # Dispara o update da tela sincronizado
                    self.root.after(0, update_display)
                    sd.sleep(int(len(audio) / FS * 1000))
            except Exception as e:
                print("Playback stopped or error:", e)
            finally:
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.live_button.config(state=tk.NORMAL))
                self.stop_playback = False

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
        # Highlight only the band 2-4 kHz
        band_mask = (freqs >= 2000) & (freqs < 4000)
        self.ax.set_xlim(0, 8000)
        self.ax.set_ylim(-60, np.max(ltas)+10 if np.max(ltas)>-50 else -50)
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

        with open(save_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Only write the allowed keys to CSV
            for row in export_data:
                row_filtered = {k: row[k] for k in fieldnames if k in row}
                writer.writerow(row_filtered)

            # Calculate global means
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

        messagebox.showinfo("Export", f"CSV file saved:\n{save_path}")

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
            "Contact: tiagolbc@gmail.com\n\n"
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
