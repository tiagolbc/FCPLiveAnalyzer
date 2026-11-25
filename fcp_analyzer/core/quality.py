"""Warnings attached to a result. Codes are stable (used for translation and CSV)."""
from __future__ import annotations

import numpy as np

# code -> (pt-BR, en)
MESSAGES = {
    "no_voice": ("Nenhum trecho vozeado encontrado.", "No voiced segments found."),
    "short_ltas": ("LTAS curto: menos de {v:.0f} s de voz. O FCP é uma medida de LTAS de trechos longos.",
                   "Short LTAS: less than {v:.0f} s of voice. FCP is a long-term (LTAS) measure."),
    "sustained": ("Parece uma vogal/nota sustentada (F0 quase constante: faixa de {d:.1f} semitons). Lã et al. (2023): o FCP não se aplica a vogais sustentadas.",
                  "Looks like a sustained vowel/note (nearly constant F0: {d:.1f} semitone range). Lã et al. (2023): FCP does not apply to sustained vowels."),
    "high_f0": ("F0 médio alto ({f:.0f} Hz): harmônicos mais espaçados que a banda de análise; o LTAS mostra harmônicos isolados e o FCP fica menos confiável.",
                "High mean F0 ({f:.0f} Hz): harmonics are wider apart than the analysis bandwidth; the LTAS shows single harmonics and FCP is less reliable."),
    "clipping": ("Clipping em {c:.2f}% das amostras: níveis em agudos ficam distorcidos.",
                 "Clipping in {c:.2f}% of samples: high-frequency levels are distorted."),
    "low_fs": ("Taxa de amostragem {fs} Hz: faixas acima de {ny:.0f} Hz não existem.",
               "Sample rate {fs} Hz: bands above {ny:.0f} Hz are missing."),
    "uncalibrated": ("Sem calibração: níveis em dB relativos (o FCP e os ΔL não dependem disso).",
                     "Not calibrated: levels are relative dB (FCP and ΔL do not depend on it)."),
}

MIN_GLOBAL_VOICED_S = 10.0
SUSTAINED_ST = 2.0  # pitch range (semitones) below which a recording looks like one sustained note
HIGH_F0_HZ = 350.0
CLIP_FRAC = 0.001


def assess(res, fs, settings, *, pitch_range_st=None) -> list[tuple[str, dict]]:
    w = []
    if res.voiced_s <= 0:
        return [("no_voice", {})]
    if res.voiced_s < MIN_GLOBAL_VOICED_S:
        w.append(("short_ltas", {"v": MIN_GLOBAL_VOICED_S}))
    if pitch_range_st is not None and np.isfinite(pitch_range_st) and pitch_range_st < SUSTAINED_ST:
        w.append(("sustained", {"d": pitch_range_st}))
    if np.isfinite(res.f0_mean_hz) and res.f0_mean_hz > HIGH_F0_HZ:
        w.append(("high_f0", {"f": res.f0_mean_hz}))
    if res.clip_fraction > CLIP_FRAC:
        w.append(("clipping", {"c": 100 * res.clip_fraction}))
    if fs / 2 < settings.band_edges_hz[-1]:
        w.append(("low_fs", {"fs": int(fs), "ny": fs / 2}))
    if not settings.calibrated:
        w.append(("uncalibrated", {}))
    return w


def message(code: str, params: dict, lang: str = "pt") -> str:
    pt, en = MESSAGES.get(code, (code, code))
    txt = pt if lang.startswith("pt") else en
    try:
        return txt.format(**params)
    except Exception:
        return txt
