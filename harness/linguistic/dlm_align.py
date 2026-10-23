"""Vendored DiarizationLM text/alignment utilities -- the four functions core needs, freed
of the package's dependency pile (tensorflow-text, scipy, numba, datasets -- none of which
may enter the service venv; the pip install of `diarizationlm` was measured dragging all of
TensorFlow, which is how this file earns its existence).

Source: https://github.com/google/speaker-id/tree/master/DiarizationLM (Apache-2.0),
package `diarizationlm` 0.1.5. Faithful ports with two substitutions:
  - levenshtein_with_edits: their numba-jitted DP, run as plain Python -- our windows are
    ~50-250 words, so the O(n*m) table is thousands of cells, microseconds either way.
  - get_oracle_speakers: scipy.optimize.linear_sum_assignment replaced by exact brute force
    over speaker permutations. The matrix is n_speakers x n_speakers and the live use is
    TWO-speaker windows (the Fisher model's world), so "brute force" is comparing two
    permutations. Exact for n <= 8, which is more speakers than the tracker allows lanes.

The one composed addition, correct_labels(), is the whole reason core imports this: words
in, LLM completion in, per-word corrected labels out -- or None when the completion is a
confession (no speaker tags at all), which the caller must treat as a rejection.
"""
import dataclasses
import itertools

import numpy as np

PUNCTUATIONS = [",", ".", "_", "?", "!", "-", '"', "'"]

_CORRECT, _SUBSTITUTION, _INSERTION, _DELETION = 0, 1, 2, 3


@dataclasses.dataclass
class PromptOptions:
    emit_input_length: int = 896
    emit_target_length: int = 896
    prompt_prefix: str = ""
    prompt_suffix: str = " --> "
    completion_suffix: str = ""
    speaker_prefix: str = "<speaker:"
    speaker_suffix: str = ">"


def normalize_text(text: str) -> str:
    words = text.lower().strip().split()
    out = []
    for word in words:
        w = word
        for punc in PUNCTUATIONS:
            replaced = w.replace(punc, "")
            if len(replaced.split()) != 1:
                continue
            w = replaced
        out.append(w)
    return " ".join(out)


def create_diarized_text(word_labels, speaker_labels, po: PromptOptions = None) -> str:
    po = po or PromptOptions()
    output, prev = [], None
    for word, speaker in zip(word_labels, speaker_labels):
        if speaker != prev:
            output.append(po.speaker_prefix + speaker + po.speaker_suffix)
        output.append(word)
        prev = speaker
    return " ".join(output)


def extract_text_and_spk(completions: str, po: PromptOptions = None):
    """(text, spk) from '<speaker:N> w w ...'; unknown speaker tokens inherit the previous.
    Returns ("", "") when the completion carries no words."""
    po = po or PromptOptions()
    spk, previous_spk = "1", "1"
    result_text, result_spk = [], []
    for word in completions.split():
        if word.startswith(po.speaker_prefix):
            if not word.endswith(po.speaker_suffix):
                word += po.speaker_suffix
            spk = word[len(po.speaker_prefix):-len(po.speaker_suffix)]
            try:
                spk_int = int(spk)
                if not spk or spk_int < 1 or spk_int > 10:
                    raise ValueError
                previous_spk = spk
            except ValueError:
                spk = previous_spk
        else:
            result_text.append(word)
            result_spk.append(spk)
    return " ".join(result_text), " ".join(result_spk)


def levenshtein_with_edits(ref: str, hyp: str):
    """Their DP, de-numba'd. (edit_distance, [(ref_pos, hyp_pos)]); -1 marks ins/del."""
    align = []
    s1, s2 = ref.split(), hyp.split()
    n1, n2 = len(s1), len(s2)
    costs = np.zeros((n1 + 1, n2 + 1), dtype=np.int32)
    backptr = np.zeros((n1 + 1, n2 + 1), dtype=np.int32)
    for i in range(n1 + 1):
        costs[i][0] = i
    for j in range(n2):
        costs[0][j + 1] = j + 1
        for i in range(n1):
            ins = costs[i + 1][j] + 1
            del_ = costs[i][j + 1] + 1
            sub = costs[i][j] + (s1[i] != s2[j])
            best = min(ins, del_, sub)
            costs[i + 1][j + 1] = best
            if best == ins:
                backptr[i + 1][j + 1] = _INSERTION
            elif best == del_:
                backptr[i + 1][j + 1] = _DELETION
            elif s1[i] == s2[j]:
                backptr[i + 1][j + 1] = _CORRECT
            else:
                backptr[i + 1][j + 1] = _SUBSTITUTION
    i, j = n1, n2
    while i > 0 or j > 0:
        ed_op = backptr[i][j] if (i >= 0 and j >= 0) else (
            _DELETION if j < 0 else _INSERTION)
        if ed_op == _INSERTION:
            align.append((-1, j - 1))
            j -= 1
        elif ed_op == _DELETION:
            align.append((i - 1, -1))
            i -= 1
        else:
            align.append((i - 1, j - 1))
            i -= 1
            j -= 1
    align.reverse()
    return int(costs[n1][n2]), align


def get_aligned_hyp_speakers(hyp_text: str, ref_text: str, ref_spk: str) -> str:
    _, align = levenshtein_with_edits(normalize_text(ref_text), normalize_text(hyp_text))
    ref_spk_list = ref_spk.split()
    out = []
    for i, j in align:
        if i == -1:
            out.append("-1")
        elif j == -1:
            continue
        else:
            out.append(ref_spk_list[i])
    return " ".join(out)


def _assign(cost: np.ndarray):
    """Exact linear-sum assignment (maximize) by permutation search; n <= 8 by contract."""
    n = cost.shape[0]
    best_perm, best_val = tuple(range(n)), -1.0
    for perm in itertools.permutations(range(n)):
        v = float(sum(cost[i, perm[i]] for i in range(n)))
        if v > best_val:
            best_perm, best_val = perm, v
    return list(range(n)), list(best_perm)


def get_oracle_speakers(hyp_spk: str, hyp_spk_align: str):
    hyp_spk_list = [int(x) for x in hyp_spk.split()]
    hyp_spk_align_list = [int(x) for x in hyp_spk_align.split()]
    max_spk = max(max(hyp_spk_list), max(hyp_spk_align_list))
    cost = np.zeros((max_spk, max_spk))
    for aligned, original in zip(hyp_spk_align_list, hyp_spk_list):
        if aligned >= 1 and original >= 1:
            cost[aligned - 1, original - 1] += 1
    row_index, col_index = _assign(cost)
    oracle = hyp_spk_list.copy()
    for i in range(len(hyp_spk_list)):
        if hyp_spk_align_list[i] == -1:
            if hyp_spk_list[i] == -1:
                oracle[i] = 1 if i == 0 else oracle[i - 1]
            continue
        oracle[i] = col_index[hyp_spk_align_list[i] - 1] + 1
    return oracle


def transcript_preserving_speaker_transfer(src_text, src_spk, tgt_text, tgt_spk) -> str:
    """TPST: move src's speaker opinions onto tgt's exact words. The safety property the
    whole scheme rests on -- an LLM may rewrite, drop, or invent words, and only its LABEL
    opinions survive onto the transcript we actually painted."""
    if len(tgt_text.split()) != len(tgt_spk.split()):
        raise ValueError("tgt_text and tgt_spk must have the same length")
    if len(src_text.split()) != len(src_spk.split()):
        raise ValueError("src_text and src_spk must have the same length")
    tgt_spk_align = get_aligned_hyp_speakers(
        hyp_text=tgt_text, ref_text=src_text, ref_spk=src_spk)
    return " ".join(str(x) for x in get_oracle_speakers(tgt_spk, tgt_spk_align))


def correct_labels(words, spks, completion, po: PromptOptions = None):
    """Per-word corrected labels for OUR words, or None when the completion is unusable
    (no recognizable content -- the six-speaker collapse mode). Rejection thresholds on
    how MUCH moved are the caller's policy, not this function's."""
    po = po or PromptOptions()
    src_text, src_spk = extract_text_and_spk(completion, po)
    if not src_text.strip() or not src_spk.strip():
        return None
    if po.speaker_prefix not in completion:
        return None                     # tagless completion: the model didn't do the task
    try:
        out = transcript_preserving_speaker_transfer(
            src_text=src_text, src_spk=src_spk,
            tgt_text=" ".join(words), tgt_spk=" ".join(spks))
    except ValueError:
        return None
    return out.split()
