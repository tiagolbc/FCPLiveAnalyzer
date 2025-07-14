# fcp_voiced_ltas.py

import numpy as np
import parselmouth
from scipy.signal import get_window

def get_voiced_mask(y, fs):
    snd = parselmouth.Sound(y, fs)
    pitch = snd.to_pitch(time_step=0.01)
    pitch_values = pitch.selected_array['frequency']
    pitch_times = pitch.xs()
    mask = np.zeros(len(y), dtype=bool)
    for i, t in enumerate(pitch_times):
        idx = int(t * fs)
        if idx < len(mask) and pitch_values[i] > 0:
            # Marca 10 ms ao redor do centro como vozeado
            win = int(0.01 * fs // 2)
            mask[max(0, idx-win):min(len(mask), idx+win)] = True
    # Dilata a máscara para evitar cortes abruptos
    from scipy.ndimage import binary_dilation
    mask = binary_dilation(mask, iterations=10)
    return mask

def compute_ltas_voiced_like_praat(y, fs, bandwidth=350):
    mask = get_voiced_mask(y, fs)
    win_len = int(0.04 * fs)
    hop_len = int(0.01 * fs)
    frames = []
    for start in range(0, len(y) - win_len + 1, hop_len):
        seg = y[start:start + win_len]
        msk = mask[start:start + win_len]
        if np.mean(msk) < 0.5:
            continue  # Só inclui janelas realmente vozeadas!
        segment = seg * np.hanning(win_len)
        spectrum = np.abs(np.fft.rfft(segment))
        spectrum_db = 20 * np.log10(spectrum + 1e-12)
        frames.append(spectrum_db)
    if not frames:
        return np.array([]), np.array([])
    frames = np.stack(frames)
    avg_spectrum = np.mean(frames, axis=0)
    freqs = np.fft.rfftfreq(win_len, 1/fs)
    bins = np.arange(0, freqs[-1] + bandwidth, bandwidth)
    ltas = [np.max(avg_spectrum[(freqs >= bins[i]) & (freqs < bins[i+1])]) for i in range(len(bins) - 1)]
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    return bin_centers, np.array(ltas)

def extract_only_voiced_segments(y, fs):
    """
    Returns a concatenated array with only the voiced segments, detected via Parselmouth (igual ao script do Praat).
    """
    snd = parselmouth.Sound(y, fs)
    pitch = snd.to_pitch(time_step=0.01)
    pitch_values = pitch.selected_array['frequency']
    pitch_times = pitch.xs()
    voiced = pitch_values > 0

    # Encontra inícios e fins dos segmentos vozeados
    segments = []
    start_time = None
    for i, v in enumerate(voiced):
        t = pitch_times[i]
        if v:
            if start_time is None:
                start_time = t
        else:
            if start_time is not None:
                if t - start_time >= 0.05:  # só pega segmentos maiores que 50 ms
                    segments.append((start_time, t))
                start_time = None
    if start_time is not None and pitch_times[-1] - start_time >= 0.05:
        segments.append((start_time, pitch_times[-1]))

    voiced_audio = []
    for t0, t1 in segments:
        i0 = int(t0 * fs)
        i1 = int(t1 * fs)
        voiced_audio.append(y[i0:i1])
    if voiced_audio:
        return np.concatenate(voiced_audio)
    else:
        return np.array([], dtype=y.dtype)
