#!/bin/bash
# Brief 19's sources and models, fetched into SOURCES_DIR. Nothing here is committed to the repo.
# Network: raw.githubusercontent.com, zenodo.org, huggingface.co and its file CDN (us.aws.cdn.hf.co), plus PyPI.
# usage: fetch_sources.sh SOURCES_DIR
set -euo pipefail
D=$1; mkdir -p "$D"/{slurp,ami,swda,nltk,models/minilm/onnx}
G=https://raw.githubusercontent.com
# SLURP text (CC BY 4.0): the instructions
for f in train devel test; do curl -sSL --retry 3 -o "$D/slurp/$f.jsonl" "$G/pswietojanski/slurp/master/dataset/slurp/$f.jsonl"; done
curl -sSL -o "$D/slurp/LICENSE.txt" "$G/pswietojanski/slurp/master/LICENSE.txt"
# AMI meeting transcripts (CC BY 4.0), as extracted by gcunhase/AMICorpusXML, Zenodo snapshot
curl -sSL --retry 3 -o "$D/ami/amixml.zip" "https://zenodo.org/api/records/3561298/files/gcunhase%2FAMICorpusXML-v2.1.zip/content"
# Switchboard telephone calls, via the Switchboard Dialog Act Corpus release (github.com/cgpotts/swda)
curl -sSL --retry 3 -o "$D/swda/swda.zip" "$G/cgpotts/swda/master/swda.zip"
# NLTK's public-domain Gutenberg selection (Blake, the KJV Psalms, Shakespeare) and the Brown corpus
curl -sSL --retry 3 -o "$D/nltk/gutenberg.zip" "$G/nltk/nltk_data/gh-pages/packages/corpora/gutenberg.zip"
curl -sSL --retry 3 -o "$D/nltk/brown.zip" "$G/nltk/nltk_data/gh-pages/packages/corpora/brown.zip"
# models: all-MiniLM-L6-v2 (Apache 2.0, ONNX) and Qwen2.5 0.5B / 1.5B Instruct (Apache 2.0, Q4_K_M GGUF)
H=https://huggingface.co
for f in onnx/model.onnx tokenizer.json config.json; do curl -sSL --retry 3 -o "$D/models/minilm/$f" "$H/sentence-transformers/all-MiniLM-L6-v2/resolve/main/$f"; done
for m in 0.5B 1.5B; do l=$(echo $m | tr A-Z a-z)
  curl -sSL --retry 3 -o "$D/models/qwen2.5-$l-instruct-q4_k_m.gguf" "$H/Qwen/Qwen2.5-$m-Instruct-GGUF/resolve/main/qwen2.5-$l-instruct-q4_k_m.gguf"; done
pip install -q numpy onnxruntime tokenizers llama-cpp-python matplotlib
