# FCP Live Analyzer 2.0

Live and offline measurement of the **Formant Cluster Prominence (FCP)** and the LTAS band measures
(Lmax, ΔL1–ΔL4) of Lã, Silva & Granqvist (2023), *Journal of Voice* 37(4):631.e7–631.e15.

* FCP = largest difference between the voiced-only LTAS (Hann window, 350 Hz bandwidth, power average)
  and a trendline fitted between 1 and 5 kHz (linear in log frequency), inside 2–4 kHz.
* Reproduces Sopran's FCP and slope within 0.02 dB on the validation files (`validation/sopran`).
* Live input (incremental, ~4 ms per update), file playback with display synchronised to the audio
  stream, batch analysis, dB SPL calibration (30 cm), CSV/PNG export, Portuguese and English interface.
* Buzz (5–8 kHz) is the author's own **experimental** measure, not validated in the literature.

## Run

```
pip install -r requirements.txt
python main.py [file.wav]
```

Windows executable: `build_exe.ps1` (runs the tests, builds the manuals and `dist\FCP_Live_Analyzer\`).

## Layout

| Path | Content |
| --- | --- |
| `fcp_analyzer/core` | Analysis (no GUI): LTAS engines, voicing, measures, calibration, live analyser, export, batch |
| `fcp_analyzer/gui` | PySide6 + pyqtgraph interface |
| `tests` | 65 automatic tests (`python -m pytest tests`) |
| `validation/sopran` | Sopran reference LTAS and FCP values |
| `tools` | `compare_sopran.py`, `compare_v1.py`, `build_manuals.py` |
| `docs` | User manuals (pt-BR, EN) in Markdown, HTML and PDF |

## License and credit

Apache License 2.0 — see `LICENSE` and `NOTICE`. Redistributions and derivative works must keep the
NOTICE file and credit the author, Tiago Lima Bicalho Cruz. To cite: `CITATION.cff`.
