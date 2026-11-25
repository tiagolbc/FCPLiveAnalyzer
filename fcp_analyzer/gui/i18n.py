"""Interface strings (Portuguese and English)."""
from __future__ import annotations

_LANG = "en"

T = {
    # toolbar / actions
    "live": ("Ao vivo", "Live"),
    "stop": ("Parar", "Stop"),
    "open": ("Abrir", "Open"),
    "play": ("Tocar", "Play"),
    "pause": ("Pausar", "Pause"),
    "batch": ("Lote", "Batch"),
    "export": ("Exportar", "Export"),
    "screenshot": ("Captura", "Screenshot"),
    "calibrate": ("Calibrar", "Calibrate"),
    "settings": ("Configurações", "Settings"),
    "help": ("Manual", "Manual"),
    "about": ("Sobre", "About"),
    "input": ("Entrada", "Input"),
    "output": ("Saída", "Output"),
    "refresh": ("Atualizar dispositivos", "Refresh devices"),
    # panels
    "fcp_window": ("FCP (janela de {w:g} s)", "FCP ({w:g} s window)"),
    "fcp_global": ("FCP global", "Global FCP"),
    "fcp_global_live": ("FCP global da sessão", "Session global FCP"),
    "at": ("em", "at"),
    "band_levels": ("Níveis por banda", "Band levels"),
    "level": ("Nível", "Level"),
    "voiced": ("Voz analisada", "Voiced time"),
    "f0": ("F0 médio", "Mean F0"),
    "leq": ("Leq (C), voz", "Leq (C), voiced"),
    "buzz": ("Buzz 5–8 kHz", "Buzz 5–8 kHz"),
    "experimental": ("experimental", "experimental"),
    "warnings": ("Avisos", "Warnings"),
    "no_warnings": ("Nenhum aviso.", "No warnings."),
    "legend_title": ("Cores do FCP (faixas visuais, não limiares validados)",
                     "FCP colours (visual bands, not validated thresholds)"),
    "legend_refs": ("Referências (Lã et al. 2023): leitura ≈ 4–5 dB · Fado-Canção ≈ 10 dB · barítonos líricos 15–20 dB",
                    "References (Lã et al. 2023): reading ≈ 4–5 dB · Fado-Canção ≈ 10 dB · opera baritones 15–20 dB"),
    "tab_ltas": ("LTAS", "LTAS"),
    "tab_scatter": ("FCP × Buzz", "FCP × Buzz"),
    "tab_table": ("Tabela", "Table"),
    "ltas_title": ("LTAS – espectro médio de longo termo (só voz)", "LTAS – long-term average spectrum (voiced only)"),
    "freq": ("Frequência (Hz)", "Frequency (Hz)"),
    "time": ("Tempo (s)", "Time (s)"),
    "curve_window": ("janela atual", "current window"),
    "curve_global": ("global", "global"),
    "curve_trend": ("reta de tendência 1–5 kHz", "trendline 1–5 kHz"),
    "show_global": ("Mostrar LTAS global", "Show global LTAS"),
    "show_buzz": ("Mostrar Buzz (experimental)", "Show Buzz (experimental)"),
    "freeze": ("Congelar", "Freeze"),
    # states
    "ready": ("Pronto. Abra um arquivo ou clique em Ao vivo.", "Ready. Open a file or click Live."),
    "analysing": ("Analisando {name}…", "Analysing {name}…"),
    "loaded": ("{name}: {dur:.1f} s, {fs} Hz. Espaço toca/pausa; clique na linha do tempo para navegar.",
               "{name}: {dur:.1f} s, {fs} Hz. Space plays/pauses; click the timeline to seek."),
    "live_running": ("Ao vivo: {dev} · {fs} Hz", "Live: {dev} · {fs} Hz"),
    "live_saved": ("Sessão salva em {path}", "Session saved to {path}"),
    "calibrated": ("Calibrado ({off:+.1f} dB)", "Calibrated ({off:+.1f} dB)"),
    "uncalibrated": ("Sem calibração (dB relativo)", "Not calibrated (relative dB)"),
    "drop_hint": ("Arraste um arquivo de áudio para cá", "Drop an audio file here"),
    "error": ("Erro", "Error"),
    "audio_error": ("Não foi possível abrir o dispositivo de áudio:\n{e}", "Could not open the audio device:\n{e}"),
    "load_error": ("Não foi possível abrir o arquivo:\n{e}", "Could not open the file:\n{e}"),
    "no_voice": ("Nenhum trecho vozeado encontrado neste arquivo.", "No voiced segments found in this file."),
    "export_done": ("Exportado para:\n{path}", "Exported to:\n{path}"),
    "nothing_export": ("Nada para exportar ainda.", "Nothing to export yet."),
    "batch_select": ("Selecione os arquivos de áudio", "Select audio files"),
    "batch_running": ("Analisando em lote…", "Batch analysis…"),
    "batch_done": ("Lote concluído: {ok} de {n} arquivos.\n{path}", "Batch finished: {ok} of {n} files.\n{path}"),
    "cancel": ("Cancelar", "Cancel"),
    "close": ("Fechar", "Close"),
    "ok": ("OK", "OK"),
    "lang_restart": ("O idioma muda ao reabrir o programa.", "The language changes when the program is reopened."),
    "open_folder": ("Abrir pasta", "Open folder"),
    "audio_files": ("Arquivos de áudio", "Audio files"),
    "review_take": ("Revisar gravação", "Review take"),
    # settings dialog
    "set_title": ("Configurações da análise", "Analysis settings"),
    "set_engine": ("Motor do LTAS", "LTAS engine"),
    "set_engine_sopran": ("Tipo Sopran (Hann, banda de análise) – padrão", "Sopran-like (Hann, analysis bandwidth) – default"),
    "set_engine_praat": ("Tipo Praat (To Ltas, faixas)", "Praat-like (To Ltas, bands)"),
    "set_bw": ("Largura de banda (Hz)", "Bandwidth (Hz)"),
    "set_bwdef": ("Definição da banda (motor Sopran)", "Bandwidth definition (Sopran engine)"),
    "set_grid": ("Pontos usados nas medidas", "Points used for the measures"),
    "set_grid_sopran": ("Grade do Sopran (~172 Hz) – padrão", "Sopran grid (~172 Hz) – default"),
    "set_grid_fine": ("Grade fina (~20 Hz)", "Fine grid (~20 Hz)"),
    "set_window": ("Janela do FCP dinâmico (s)", "Dynamic FCP window (s)"),
    "set_voiced": ("Só trechos vozeados (Lã et al. 2023)", "Voiced segments only (Lã et al. 2023)"),
    "set_floor": ("F0 mínimo (Hz)", "Pitch floor (Hz)"),
    "set_ceiling": ("F0 máximo (Hz)", "Pitch ceiling (Hz)"),
    "set_buzz_band": ("Faixa do Buzz (experimental)", "Buzz band (experimental)"),
    "set_lang": ("Idioma", "Language"),
    "set_exports": ("Pasta de exportação", "Exports folder"),
    "set_browse": ("Procurar…", "Browse…"),
    "set_defaults": ("Restaurar padrões", "Restore defaults"),
    "set_note": ("Mudanças valem para a próxima análise. Arquivos abertos são reanalisados.",
                 "Changes apply to the next analysis. Open files are re-analysed."),
    # calibration
    "cal_title": ("Calibração de nível (dB SPL)", "Level calibration (dB SPL)"),
    "cal_intro": ("Como no artigo de Lã et al.: grave um tom estável (por exemplo 1 kHz) e meça o seu nível no "
                  "microfone com um decibelímetro. Informe o valor lido. Não mude o ganho do microfone depois.",
                  "As in Lã et al.: record a steady tone (e.g. 1 kHz) and measure its level at the microphone "
                  "with a sound level meter. Enter the reading. Do not change the microphone gain afterwards."),
    "cal_spl": ("Nível do tom no microfone (dB SPL)", "Tone level at the microphone (dB SPL)"),
    "cal_record": ("Gravar 3 s do microfone", "Record 3 s from the microphone"),
    "cal_load": ("Usar um arquivo WAV do tom", "Use a WAV file of the tone"),
    "cal_manual": ("Ou digite o offset (dB)", "Or type the offset (dB)"),
    "cal_distance": ("Distância boca–microfone (cm, normaliza para 30 cm)", "Mouth–microphone distance (cm, normalised to 30 cm)"),
    "cal_none": ("Sem calibração", "No calibration"),
    "cal_result": ("Offset: {off:+.2f} dB (tom: {lvl:.1f} dBFS RMS)", "Offset: {off:+.2f} dB (tone: {lvl:.1f} dBFS RMS)"),
    "cal_clear": ("Remover calibração", "Remove calibration"),
    "cal_recording": ("Gravando…", "Recording…"),
    # table
    "tbl_measure": ("Medida", "Measure"),
    "tbl_window": ("Janela", "Window"),
    "tbl_global": ("Global", "Global"),
    "tbl_def": ("Definição", "Definition"),
}


def set_language(lang: str):
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "pt"


def lang() -> str:
    return _LANG


def tr(key: str, **kw) -> str:
    pt, en = T.get(key, (key, key))
    s = pt if _LANG == "pt" else en
    return s.format(**kw) if kw else s
