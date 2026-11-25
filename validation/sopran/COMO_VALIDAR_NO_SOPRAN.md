# Validação do LTAS contra o Sopran

Objetivo: confirmar que o motor "sopran" do FCP Live Analyzer 2.0 reproduz o LTAS do Sopran
(janela Hanning, largura de banda de 350 Hz), usado por Lã, Silva e Granqvist (2023).

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `val1_noise_cluster.wav` | ruído com envelope −12 dB/oitava e um "cluster" de +14 dB em 3 kHz |
| `val2_noise_flat.wav` | o mesmo envelope, sem cluster (FCP esperado ≈ 0) |
| `val3_sine1k.wav` | seno de 1 kHz, −20 dBFS RMS (confere a escala de nível) |
| `../../examples/tenor_example.wav` | gravação real (tenor) |
| `../../examples/rock_example.wav` | gravação real (rock) |

## Passos no Sopran (para cada arquivo)

1. Abra o arquivo (File > Open).
2. Analysis > Spectrum.
3. Na aba **Settings** da janela Spectrum: Window = **Hanning**, Bandwidth [Hz] = **350**.
   Anote o valor de **"Window length"** que o Sopran mostra logo abaixo. Esse número diz qual
   definição de largura de banda o Sopran usa.
4. Level relative to: **1**. Frequency axis: tanto faz. Marque **Remove DC**.
5. Averaging: **Selection**. Na janela principal, selecione o arquivo inteiro (Ctrl+A ou arraste).
6. Clique em **Log spectrum** e depois em **Show log** / **Copy log**. Cole em um arquivo de texto
   com o mesmo nome do WAV e extensão `.txt` (por exemplo `val1_noise_cluster.txt`) nesta pasta.

Para as gravações reais (tenor e rock), faça também o LTAS só dos trechos vozeados, se você tiver
o script de remoção de não vozeados usado no artigo. Se não tiver, o LTAS do arquivo inteiro já ajuda.

## Depois

Rode, nesta pasta do projeto:

```
python tools/compare_sopran.py validation/sopran
```

O script lê cada `.txt`, calcula o FCP e os ΔL a partir do LTAS do Sopran com a mesma reta de
tendência do app e compara com o motor "sopran" do app (diferença por frequência e no FCP).
