#!/usr/bin/env bash
# Download optional local model assets. Nothing here is required to run the app;
# Saaras v4 (remote) is the primary recogniser.
set -euo pipefail

TARGET="${1:-all}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$ROOT/models"
mkdir -p "$MODELS"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing dependency: $1"; exit 1; }; }

silero() {
  echo "==> Silero VAD (onnx)"
  mkdir -p "$MODELS"
  curl -fL -o "$MODELS/silero_vad.onnx" \
    https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx
  echo "    -> $MODELS/silero_vad.onnx"
}

whisper() {
  echo "==> Whisper (faster-whisper)"
  python -m pip install --upgrade faster-whisper
  python - <<'PY'
from faster_whisper import WhisperModel
import os
size = os.environ.get("WHISPER_MODEL", "small")
print(f"    downloading whisper-{size} …")
WhisperModel(size, device="cpu", compute_type="int8")
print("    weights cached by Hugging Face")
PY
}

indicconformer() {
  echo "==> IndicConformer checkpoints"
  mkdir -p "$MODELS/indicconformer"
  cat <<'MSG'
    Automatic download is intentionally not scripted: AI4Bharat publishes the
    checkpoints through Hugging Face model cards, and each language file is
    large. Download the languages you need and place them as:

      models/indicconformer/indicconformer_hi.nemo
      models/indicconformer/indicconformer_ta.nemo
      ...

    Then set INDICCONFORMER_ENABLED=true and INDICCONFORMER_MODEL_DIR=./models/indicconformer
    Install the runtime first:  pip install "nemo_toolkit[asr]"
MSG
}

indictrans2() {
  echo "==> IndicTrans2 (distilled 200M, indic->en)"
  need python
  python -m pip install --upgrade "transformers>=4.40" torch sentencepiece
  python - <<'PY'
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
name = "ai4bharat/indictrans2-indic-en-dist-200M"
print(f"    downloading {name} …")
AutoTokenizer.from_pretrained(name, trust_remote_code=True)
AutoModelForSeq2SeqLM.from_pretrained(name, trust_remote_code=True)
print("    cached")
PY
}

case "$TARGET" in
  silero) silero ;;
  whisper) whisper ;;
  indicconformer) indicconformer ;;
  indictrans2) indictrans2 ;;
  all) silero; whisper; indicconformer; indictrans2 ;;
  *) echo "usage: $0 [all|silero|whisper|indicconformer|indictrans2]"; exit 1 ;;
esac
