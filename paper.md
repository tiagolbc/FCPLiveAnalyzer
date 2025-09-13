# FCP Live Analyzer: Real-Time and Batch Measurement of Formant Cluster Prominence for Singing Voice Research and Pedagogy

**Authors**

- Tiago Lima Bicalho Cruz (Independent Researcher, ORCID: [0000-0002-8355-5436](https://orcid.org/0000-0002-8355-5436), [tiagolbc@gmail.com](mailto:tiagolbc@gmail.com))

## Summary

**FCP Live Analyzer** is a free, open-source tool for acoustic analysis of the singing voice, focused on the measurement of *Formant Cluster Prominence* (FCP)—a robust indicator of the “singer’s formant” phenomenon. The software provides both real-time (“live”) feedback and batch file analysis, supporting pedagogical, clinical, and research applications. Results can be exported for further analysis. FCP Live Analyzer implements the algorithm as described by Lã et al. (2023), enabling objective measurement and visualization of the formant cluster responsible for vocal brilliance and projection in classical singing.

## Statement of Need

Despite decades of research into the acoustic signature of the professional singing voice, most available analysis tools either do not implement FCP directly or lack the ability to provide instant feedback during practice and teaching. Teachers, students, and researchers often rely on cumbersome workflows involving Praat scripting, complex DAW setups, or non-standardized measurements. **FCP Live Analyzer** addresses this gap by providing a lightweight, platform-independent application that computes and displays FCP (with all major supporting metrics) in real time or from pre-recorded audio. This bridges the gap between advanced voice science and the daily needs of vocal professionals and researchers.

## Installation

**FCP Live Analyzer** is distributed as open-source Python code. The recommended installation procedure is as follows:

### Prerequisites

- Python 3.8 or later (tested on Windows, macOS, Linux)
- Pip (Python package manager)

### Step-by-step

1. Clone the repository:
   ```sh
   git clone https://github.com/tiagolbc/fcp-live-analyzer.git
   cd fcp-live-analyzer
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the application:
   ```sh
   python fcp_live_gui.py
   ```

## Introduction

The human singing voice is a complex acoustic phenomenon shaped by physiological, artistic, and cultural factors. One of the most celebrated features in Western classical singing, particularly among operatic voices, is the “singer’s formant.” This spectral phenomenon allows trained singers, especially tenors and baritones, to project their voices over a full orchestra without amplification, ensuring clarity and brilliance in large performance spaces [@Sundberg1974; @Sundberg1987].

The singer’s formant is typically observed as a prominent spectral peak centered around 2.5–3.5 kHz in the long-term average spectrum (LTAS) of the singing voice [@Bartholomew1934; @Sundberg1977]. This peak arises due to the clustering of the third, fourth, and fifth vocal tract resonances (R3, R4, R5), resulting from specific vocal tract adjustments—primarily lowering of the larynx and narrowing of the aryepiglottic sphincter [@Sundberg1974; @Sundberg1987; @Titze2003]. The increased energy in this frequency region is advantageous due to reduced orchestral masking and the human ear’s heightened sensitivity to frequencies between 2 and 4 kHz [@Robinson1957; @Sundberg1995]. The singer’s formant is thus crucial for vocal projection and the characteristic timbre of operatic singing.

While much research has focused on the singer’s formant in Western classical singing [@Sundberg1990; @Sundberg2001; @Sundberg2013], there remains a need for objective, robust, and reproducible metrics to quantify the degree of “formant clustering” responsible for this effect. *Formant Cluster Prominence* (FCP) has recently emerged as a promising metric to address this need [@La2023].

### What is Formant Cluster Prominence (FCP)?

FCP is an acoustic measure designed to quantify the prominence of the cluster of higher vocal tract formants (typically R3–R5) that forms the spectral envelope known as the singer’s formant [@La2023]. FCP is calculated as the difference in decibels (dB) between the maximum spectral level within the 2–4 kHz region and a linear trendline fitted to the LTAS between 1 and 5 kHz. This approach compensates for overall spectral slope and vocal loudness, providing a more robust indicator of formant clustering than previous indices, such as the Hammarberg index or the simple difference between SPL and the 2.2–3.6 kHz band [@Hammarberg1980; @Bloothooft1986].

Mathematically, FCP is expressed as:

$$
\mathrm{FCP} = L_{\text{peak}}(2\text{–}4\,\mathrm{kHz}) - L_{\text{trend}}(f_{\text{peak}})
$$

Where:
- \(L_{\text{peak}}(2\text{–}4\,\mathrm{kHz})\) is the highest spectral level in the 2–4 kHz range of the LTAS.
- \(L_{\text{trend}}(f_{\text{peak}})\) is the value of the linear regression (trendline) fitted to the LTAS between 1 and 5 kHz, evaluated at the frequency \(f_{\text{peak}}\) where the maximum occurs.

This measure is less sensitive to variations in vowel, loudness, and spectral slope, allowing comparisons across singers, voice types, and singing styles [@La2023].

### Purpose and Application of FCP

FCP enables objective, reproducible comparisons of the extent to which different singers and styles exhibit formant clustering associated with the singer’s formant. In classical singing, high FCP values typically correspond to a well-defined singer’s formant, a hallmark of professional operatic voices [@Sundberg1995; @Sundberg2013]. In contrast, popular music genres, traditional styles, and contemporary commercial music (CCM) often show less pronounced formant clustering, with high-frequency energy distributed differently or absent [@Sundberg2012; @Borch2002].

The singer’s formant serves as both an acoustic signature of classical technique and a functional adaptation for projection and clarity on the operatic stage. FCP provides a direct way to quantify this adaptation, track its development during training, and compare it across individuals, genres, and contexts [@La2023].

### The Singer’s Formant: Acoustic and Physiological Significance

The singer’s formant results from subtle physiological adjustments—lowering the larynx, widening the pharyngeal cavity, and constricting the aryepiglottic space—bringing the third, fourth, and fifth formants into close proximity, creating a reinforced spectral peak in the 2–4 kHz range [@Sundberg1974; @Sundberg1987; @Titze2003]. This clustering facilitates audibility over orchestral accompaniment and contributes to the “ring” and brilliance of operatic voices. Studies show that audiences and expert listeners prefer voices with a singer’s formant, especially in demanding acoustic environments [@Monson2011].

### Relevance Across Singing Styles

While the singer’s formant and high FCP values are standard in classical singing, they are less common in popular, traditional, and folk styles. For example, Portuguese Fado and Fado-Canção show variable presence of the singer’s formant, with contemporary Fado-Canção singers producing more energy in higher frequency bands (5–8 kHz) rather than strong formant clustering [@La2023]. In genres like rock, pop, and world music, the singer’s formant may be absent or replaced by other spectral strategies [@Borch2002; @Sundberg2012].

### Scientific and Pedagogical Importance

FCP quantification is valuable for voice research, pedagogy, and clinical applications. For researchers, FCP enables large-scale comparisons of voices and styles, studies of training effects, and tracking of vocal changes. For teachers and students, FCP offers a feedback tool to monitor resonance strategies and technique development. In clinical contexts, deviations in FCP may inform voice disorder diagnoses or vocal function assessments [@Hammarberg1980].

In summary, FCP is a scientifically grounded, practical metric bridging voice science, pedagogy, and performance. It provides an accessible, objective means to quantify the acoustic effect central to classical vocal projection and resonance, with applications in research, teaching, and live feedback.

## Software Description

### Purpose and Features

- Real-time (live) and offline (batch) measurement of FCP from microphone or file input.
- Graphical display of Long-Term Average Spectrum (LTAS), including color-coded 2–4 kHz band.
- Display of FCP and supporting metrics: \(L_{\max,0\text{–}2\,\mathrm{kHz}}\), \(L_{\max,2\text{–}5\,\mathrm{kHz}}\), \(L_{\max,5\text{–}8\,\mathrm{kHz}}\), \(L_{\max,2\text{–}4\,\mathrm{kHz}}\), deltas, and the trendline value at the FCP peak.
- Export of analysis results for statistical or pedagogical tracking.
- Automatic calculation of Global FCP (from all voiced audio) and Mean FCP (running average during live mode).
- Intuitive GUI for users with no programming experience.
- One-click screenshot of the current LTAS plot (PNG), suitable for reports and teaching material.
- Batch processing of multiple WAV files with per-file summaries and full per-window metrics.

### Implementation and Architecture

- Developed in Python (compatible with Windows, macOS, Linux).
- Uses standard scientific libraries (numpy, scipy, sounddevice, matplotlib, tkinter, PIL).
- The signal is analyzed using a rolling buffer for live mode and windowed analysis for file mode. Voiced segments are automatically detected, and only these are included in FCP computation.
- Calculation of the LTAS is performed via overlapping Hanning windows, averaged in the frequency domain.
- The FCP value for each window is computed per Lã et al. (2023).
- All metrics and parameters are displayed in real time.

### Calculation of FCP

The FCP algorithm, as implemented, follows the description by Lã et al. (2023):

1. Compute the LTAS using 40 ms Hanning windows with 10 ms hop size.
2. For each window, compute the spectrum in dB and average across windows.
3. Find the maximum value within 2–4 kHz: \(L_{\text{peak}}\).
4. Fit a linear regression (trendline) to the LTAS between 1–5 kHz.
5. Evaluate the trendline at the frequency of the spectral maximum in 2–4 kHz: \(L_{\text{trend}}(f_{\text{peak}})\).
6. Subtract to obtain FCP:

\[
\mathrm{FCP} = L_{\text{peak}}(2\text{–}4\,\mathrm{kHz}) - L_{\text{trend}}(f_{\text{peak}})
\]

This approach is robust to differences in loudness, vowel, and recording setup.

### Available Analysis Modes

- **File mode (Load File):** Analyze any WAV file. Displays the LTAS and all metrics. Computes “Global FCP” using all voiced audio.
- **Live mode:** Provides real-time feedback. Displays FCP for each rolling buffer. The “Mean FCP” label shows the running mean for the current live session.
- **Export:** All analyzed windows are exportable, with both per-window and global means for all metrics.
- **Batch mode:** Processes multiple WAV files in one step, generating per-file summaries and per-window metrics suitable for large-scale studies.
- **Screenshot:** Saves the current LTAS plot as a high-resolution PNG via a file dialog.

### Data Export and Organization

The application supports automatic, structured export of analysis artifacts to facilitate reproducibility and sharing:

- **Auto-export on STOP (Live or Playback):** When stopping a session, a timestamped directory is created under `Exports/LiveOrPlayback_YYYYMMDD_HHMMSS/` containing:
  - CSV with analysis data (`fcp_live.csv` for live sessions or `fcp_windows.csv` for file playback).
  - Optional Excel (`.xlsx`) containing the same data and a summary sheet (if `pandas` is available).
  - `fcp_evolution.png` (FCP over time).
  - `ltas_current.png` (current LTAS figure).

- **Batch outputs:** Running batch analysis creates `Exports/Batch_YYYYMMDD_HHMMSS/` with:
  - `batch_summary.csv` (one row per file: duration, global voiced-only FCP, band maxima, window-based mean/SD FCP, window count).
  - `batch_windows.csv` (all per-window FCP metrics across files).
  - Optional `batch_results.xlsx` (summary + windows sheets, if `pandas` is available).
  - Per-file subfolders `/<file_stem>/` containing:
    - `fcp_evolution.png` (FCP vs. time for that file).
    - `ltas_current.png` (global voiced-only LTAS with the 2–4 kHz band highlighted and color-coded by global FCP).

- **Organization:** All outputs are grouped into clearly named, timestamped folders under `Exports/`, keeping runs separate and traceable.

## Illustrative Examples

### Example 1: Tenor with Singer’s Formant

A professional tenor singing an operatic phrase, displaying a pronounced FCP (>15 dB) and a prominent LTAS peak near 3 kHz.

![Tenor FCP](/figures/tenor_example.png){#fig:tenor_example width=90%}

### Example 2: Female Opera Singer—Sustained Vowel

A female opera singer performing a sustained /a/ vowel, exhibiting a clear spectral clustering in 2–4 kHz.

![Alto FCP](../figures/female_sustained.png){#fig:female_sustained width=90%}

### Example 3: Rock Singer Without Singer’s Formant

A male rock singer in a typical rock ballad passage, with no visible “formant cluster” in 2–4 kHz and low FCP values.

![Rock Singer FCP](../figures/rock_example.png){#fig:rock_example width=90%}

## Comparison with Existing Tools

While several programs offer LTAS or spectral analysis (e.g., Praat, VoceVista, Wavelab), few implement the exact FCP calculation as defined by Lã et al. (2023). Most require manual window selection, do not provide real-time feedback, or lack direct export of all relevant metrics. FCP Live Analyzer stands out by providing an open, automated, and user-friendly solution specifically for singer’s formant research and pedagogy.

## Acknowledgements

The development of FCP Live Analyzer was inspired by research on the acoustic properties of professional singing, especially the foundational work of Johan Sundberg and recent advances by Filipa Lã and colleagues. The software is dedicated to the international community of singers, teachers, and voice scientists.

## References

\bibliography{paper}
