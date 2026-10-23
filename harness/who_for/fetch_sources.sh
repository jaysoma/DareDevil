#!/bin/bash
# Brief 22's sources, into SOURCES_DIR (the same as brief 19's, plus NLTK's names list). Nothing here is committed.
# Requests go one at a time with a pause between them, so hosts don't read the run as bot traffic.
# usage: fetch_sources.sh SOURCES_DIR
set -euo pipefail
D=$1; mkdir -p "$D"/{slurp,ami,swda,nltk,models/minilm/onnx}
G=https://raw.githubusercontent.com
get() { curl -sSL --retry 3 --retry-delay 5 -o "$1" "$2"; sleep 2; }
for f in train devel test; do get "$D/slurp/$f.jsonl" "$G/pswietojanski/slurp/master/dataset/slurp/$f.jsonl"; done
get "$D/ami/amixml.zip" "https://zenodo.org/api/records/3561298/files/gcunhase%2FAMICorpusXML-v2.1.zip/content"
get "$D/swda/swda.zip" "$G/cgpotts/swda/master/swda.zip"
for c in gutenberg brown names; do get "$D/nltk/$c.zip" "$G/nltk/nltk_data/gh-pages/packages/corpora/$c.zip"; done
H=https://huggingface.co
for f in onnx/model.onnx tokenizer.json config.json; do get "$D/models/minilm/$f" "$H/sentence-transformers/all-MiniLM-L6-v2/resolve/main/$f"; done
pip install -q numpy onnxruntime tokenizers matplotlib
