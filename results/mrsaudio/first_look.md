# MRSAudio (MRSSpeech): a first look (2026-10-23)

Zhejiang University's MRSAudio (arXiv 2510.10396, NeurIPS 2025; https://github.com/MRSAudio/MRSAudio_Main; data on
Hugging Face as `verstar/MRSAudio`, CC BY 4.0 on the card). Script: `harness/mrsaudio/first_look.py`.

## What's in it
- **MRSSpeech:** two people (A and B) acting Chinese film and play scripts while standing and walking around a binaural
  head (the paper names a 3Dio Free Space). 410 drama folders are listed; 72 have audio in the index so far (the card
  says the upload is still running).
- **One file per utterance:** `<drama>_缩混_cut_<start>_<end>_<A|B>.wav`, 2 channels, 48 kHz. Start and end are seconds
  in the whole recording.
- **One pose file per utterance** beside it (`.npy`): a row every 50 ms with x, y, z (metres from the head), the time in
  the whole recording (ms), and a tag number. **x is the ear axis** (the delay follows x/r at corr +0.86, y/r at +0.60).
  Standing positions were measured by hand, walking ones by UWB (paper); no accuracy is given.

## What a sample of 120 utterances (3 dramas) shows
- **Distance:** horizontal median 1.33 m, 10th-90th percentile 0.81-1.73 m, max 2.2 m. 76% within 1.5 m.
- **The ears aren't bare mics.** The delay reaches 0.6-0.7 ms, where two bare mics 157 mm apart top out at 0.46 ms: the
  head bends the sound round, as STARSS23's sphere does. An angle read needs the head's own delay law, not the phone's.
- **Where the talkers stand:** of the 48 standing still, most are 30-70 deg off the ear axis's broadside, to the sides.
- **Angle from a plain GCC delay**, with a fitted law: 13-15 of 48 off by more than 20 deg (set aside); the rest
  average 8 deg. Whether the misses are the reads or the positions isn't separated here.

## For range
- **The unit fits:** one utterance per file, with the talker's position: exactly brief 21's one read per utterance.
  The talkers' distances within a drama span 2-2.6x, more than STARSS23's.
- **The ratios don't need expanding.** Relative range is a ratio to the anchor, and scaling every position by k leaves
  every ratio unchanged. What close data can't show is the CDR flattening beyond the critical distance (brief 20).
  That can't be faked by turning down the direct sound: that split is the CDR estimator's own job, so it would read
  back the law it was given.
- **Untested:** the CDR estimator's diffuse model assumes two bare mics. Between a head's ears the room's diffuse sound
  is less coherent, so the estimator will split direct from room differently. The anchor may cancel some of that.

## Decision (2026-10-23)
- **Parked for Stage 1.** The ears are a head, not a phone, so its angle and range numbers wouldn't speak for the
  phone either way.
- **Kept for Stage 2:** two talkers per drama, hundreds of labelled utterances each, with positions while they walk.
  A test bed for whether CAM++'s embedding moves with where the talker stands.
