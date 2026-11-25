# Changelog

## 2.0.0 — 2026-11-25

Complete rewrite. Results differ from 1.2.1; use `tools/compare_v1.py` to compare.

### Method (fixes)
- FCP is now the **maximum of (LTAS − trendline)** inside 2–4 kHz (Lã et al. 2023). 1.2.1 took the LTAS
  peak and subtracted the trendline at that peak (kept as `FCP_at_peak_v1_dB` for comparison).
- LTAS: Hann window with 350 Hz bandwidth (−6 dB definition, 5.714 ms, as Sopran) and **power** averaging.
  1.2.1 averaged dB spectra of 40 ms frames and took the maximum inside 350 Hz bins.
- Measures on Sopran's frequency grid by default; matches Sopran's own FCP/slope within 0.02 dB.
- ΔL1–ΔL4 with the paper's signs (1.2.1 exported −ΔL1, −ΔL2, −ΔL4; ΔL3 was missing; `Delta_2_4` was Lmax(2–4)).
- Real calibration (reference tone, dB SPL, 30 cm normalisation) instead of a fixed +94 dB offset.
- C-weighted Leq of the voiced signal.
- Buzz: one documented definition (P90 in the band minus the FCP trendline at 5 kHz), labelled experimental,
  off by default. The harmonic-density normalisation of 1.2.1 was removed.
- Automatic warnings: short LTAS, sustained vowel/note, high F0, clipping, low sample rate, uncalibrated.
- FCP colour bands documented as visual bands, not validated thresholds.

### Software
- New PySide6 + pyqtgraph interface (dark theme), Portuguese and English.
- Live analysis is incremental (about 4 ms per update) with session-global FCP in real time;
  the take is saved, re-analysed and exported when Live stops.
- Playback display driven by the audio stream position (minus device latency); click the timeline to seek.
- Batch analysis in a background thread with progress and cancel; per-file folders.
- Exports: summary, windows, LTAS (with trendline) CSV, PNG figures, settings JSON in every summary.
- WAV, FLAC, AIFF, OGG, MP3 input; drag and drop.
- 65 automatic tests (synthetic signals with known FCP, paper tables, Praat, Sopran, live = file, GUI).
- Packaging: dependency `praat-parselmouth`; one-folder executable; Qt splash screen (cross-platform).
- License: Apache 2.0 with NOTICE (credit to the author); the conflicting EULA was dropped.
