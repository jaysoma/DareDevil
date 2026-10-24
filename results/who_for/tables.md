# Brief 22: tables

## Step 1: accepted at brief 19's thresholds (% of real requests, each against all four devices)

| method | FA/h | real, in place | real, spliced | directive | ask | commit | b19 to_person (generated) | b19 subject (generated) | b19 hits |
|---|---|---|---|---|---|---|---|---|---|
| keyword | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 20.0 | 3.8 | 8.8 |
| keyword | 10 | 0.9 | 0.9 | 0.8 | 3.0 | 0.9 | 51.9 | 21.2 | 32.7 |
| shape_ngram | 1 | 0.2 | 0.2 | 0.1 | 0.8 | 0.3 | 43.1 | 22.5 | 82.9 |
| shape_ngram | 10 | 2.3 | 2.3 | 1.8 | 5.3 | 3.8 | 74.4 | 58.1 | 92.1 |
| contrast_ngram | 1 | 0.2 | 0.2 | 0.1 | 0.8 | 0.3 | 50.6 | 30.6 | 83.8 |
| contrast_ngram | 10 | 2.4 | 3.4 | 1.6 | 6.1 | 5.6 | 81.9 | 71.2 | 94.6 |
| contrast_ngram_past | 1 | 0.1 | 0.2 | 0.0 | 0.8 | 0.0 | 43.8 | 28.7 | 83.1 |
| contrast_ngram_past | 10 | 2.1 | 2.9 | 1.4 | 4.5 | 5.3 | 76.2 | 63.1 | 93.5 |
| shape_embed | 1 | 0.2 | 0.2 | 0.2 | 0.0 | 0.3 | 46.9 | 35.6 | 61.0 |
| shape_embed | 10 | 3.8 | 3.8 | 4.0 | 3.8 | 2.1 | 88.1 | 69.4 | 89.4 |
| contrast_embed | 1 | 0.2 | 2.3 | 0.2 | 0.0 | 0.6 | 83.1 | 72.5 | 89.2 |
| contrast_embed | 10 | 4.4 | 19.6 | 4.1 | 3.8 | 5.9 | 95.6 | 92.5 | 98.5 |
| contrast_embed_past | 1 | 0.0 | 0.4 | 0.0 | 0.0 | 0.3 | 56.9 | 40.0 | 71.7 |
| contrast_embed_past | 10 | 0.6 | 2.7 | 0.5 | 0.0 | 0.9 | 85.6 | 80.6 | 92.3 |

### Per device, MiniLM contrast at 10 FA/h (in place / spliced)

| device | in place | spliced |
|---|---|---|
| car | 5.3 | 28.1 |
| kitchen | 6.3 | 27.4 |
| watch | 2.4 | 10.2 |
| general | 3.4 | 12.6 |

### The same words in place against spliced (paired, every request x device)

| method | median score in place - spliced | % lower in place | pairs |
|---|---|---|---|
| keyword | 0.0 | 0.0 | 2480 |
| shape_ngram | 0.0 | 0.0 | 2480 |
| contrast_ngram | -0.1276 | 73.9 | 2480 |
| contrast_ngram_past | -0.0819 | 66.3 | 2480 |
| shape_embed | 0.0 | 0.0 | 2480 |
| contrast_embed | -0.0724 | 86.1 | 2480 |
| contrast_embed_past | -0.0576 | 76.1 | 2480 |

### Device-shaped real requests (88 requests, 93 request x device pairs passing the device's MiniLM shape threshold at 10 FA/h): MiniLM contrast accepts

|  | in place | spliced |
|---|---|---|
| at 1 FA/h | 6.5 | 45.2 |
| at 10 FA/h | 43.0 | 96.8 |

### Full curves: % accepted as the threshold moves (per device, pooled), by false accepts per hour


**contrast_embed**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 86.9 | 70.6 | 0.0 | 1.4 |
| 0.5 | 88.5 | 74.4 | 0.0 | 1.5 |
| 1 | 91.9 | 85.0 | 0.3 | 2.6 |
| 2 | 94.0 | 92.5 | 0.6 | 4.6 |
| 3 | 95.8 | 94.4 | 1.0 | 6.8 |
| 5 | 96.3 | 96.9 | 1.7 | 10.6 |
| 7 | 97.3 | 96.9 | 2.8 | 14.7 |
| 10 | 98.3 | 98.1 | 4.4 | 19.6 |
| 15 | 99.6 | 98.8 | 7.0 | 27.0 |
| 20 | 99.6 | 98.8 | 9.3 | 33.1 |
| 30 | 99.6 | 99.4 | 13.1 | 42.6 |
| 45 | 99.8 | 99.4 | 19.4 | 54.3 |
| 60 | 100.0 | 100.0 | 25.1 | 63.6 |

**contrast_embed_past**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 68.3 | 52.5 | 0.0 | 0.2 |
| 0.5 | 72.1 | 55.0 | 0.0 | 0.3 |
| 1 | 80.8 | 61.9 | 0.0 | 0.6 |
| 2 | 84.4 | 71.2 | 0.0 | 0.8 |
| 3 | 86.5 | 74.4 | 0.0 | 0.9 |
| 5 | 90.4 | 80.6 | 0.1 | 1.3 |
| 7 | 91.7 | 85.0 | 0.3 | 1.8 |
| 10 | 92.7 | 90.0 | 0.6 | 2.9 |
| 15 | 93.7 | 90.6 | 1.0 | 4.4 |
| 20 | 94.8 | 92.5 | 1.4 | 5.7 |
| 30 | 96.7 | 93.1 | 3.1 | 9.4 |
| 45 | 98.3 | 96.9 | 6.4 | 18.0 |
| 60 | 99.6 | 98.1 | 11.0 | 28.3 |

**contrast_ngram**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 75.0 | 31.2 | 0.0 | 0.1 |
| 0.5 | 79.4 | 40.0 | 0.0 | 0.1 |
| 1 | 84.2 | 52.5 | 0.2 | 0.3 |
| 2 | 88.5 | 61.3 | 0.2 | 0.6 |
| 3 | 89.6 | 66.9 | 0.6 | 1.0 |
| 5 | 91.5 | 72.5 | 1.1 | 1.6 |
| 7 | 93.5 | 76.2 | 1.7 | 2.1 |
| 10 | 94.4 | 80.6 | 2.5 | 3.4 |
| 15 | 95.2 | 86.2 | 3.5 | 5.2 |
| 20 | 96.3 | 86.9 | 4.8 | 7.3 |
| 30 | 96.9 | 90.0 | 7.9 | 11.2 |
| 45 | 97.9 | 90.6 | 12.4 | 17.4 |
| 60 | 98.7 | 92.5 | 16.5 | 22.6 |

**shape_embed**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 59.4 | 46.2 | 0.0 | 0.0 |
| 0.5 | 67.7 | 53.8 | 0.0 | 0.0 |
| 1 | 73.7 | 61.3 | 0.2 | 0.2 |
| 2 | 80.2 | 73.1 | 0.5 | 0.5 |
| 3 | 84.0 | 75.6 | 1.0 | 1.0 |
| 5 | 87.9 | 84.4 | 1.5 | 1.5 |
| 7 | 89.6 | 88.1 | 2.7 | 2.7 |
| 10 | 90.8 | 90.0 | 3.8 | 3.8 |
| 15 | 92.5 | 92.5 | 5.9 | 5.9 |
| 20 | 94.0 | 93.8 | 7.3 | 7.3 |
| 30 | 95.4 | 95.0 | 10.6 | 10.6 |
| 45 | 96.5 | 95.6 | 15.8 | 15.8 |
| 60 | 97.3 | 96.9 | 21.1 | 21.1 |

**shape_ngram**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 68.7 | 25.6 | 0.0 | 0.0 |
| 0.5 | 73.8 | 31.9 | 0.1 | 0.1 |
| 1 | 80.8 | 44.4 | 0.2 | 0.2 |
| 2 | 86.5 | 55.0 | 0.4 | 0.4 |
| 3 | 88.8 | 61.9 | 0.8 | 0.8 |
| 5 | 90.8 | 68.8 | 1.3 | 1.3 |
| 7 | 91.0 | 70.0 | 1.6 | 1.6 |
| 10 | 92.3 | 74.4 | 2.3 | 2.3 |
| 15 | 93.8 | 79.4 | 3.5 | 3.5 |
| 20 | 94.4 | 82.5 | 4.8 | 4.8 |
| 30 | 95.4 | 85.6 | 7.1 | 7.1 |
| 45 | 96.2 | 86.9 | 9.7 | 9.7 |
| 60 | 96.5 | 88.1 | 12.8 | 12.8 |

**keyword**

| FA/h | hits | to_person (generated, spliced) | real requests, in place | real requests, spliced |
|---|---|---|---|---|
| 0.25 | 8.5 | 18.1 | 0.0 | 0.0 |
| 0.5 | 8.5 | 18.1 | 0.0 | 0.0 |
| 1 | 8.8 | 20.0 | 0.0 | 0.0 |
| 2 | 14.4 | 28.7 | 0.0 | 0.0 |
| 3 | 14.4 | 28.7 | 0.0 | 0.0 |
| 5 | 29.6 | 47.5 | 0.5 | 0.5 |
| 7 | 32.7 | 51.9 | 0.9 | 0.9 |
| 10 | 32.7 | 51.9 | 0.9 | 0.9 |
| 15 | 32.7 | 51.9 | 0.9 | 0.9 |
| 20 | 32.7 | 51.9 | 0.9 | 0.9 |
| 30 | 32.7 | 51.9 | 0.9 | 0.9 |
| 45 | 63.3 | 75.6 | 8.6 | 8.6 |
| 60 | 74.6 | 90.6 | 12.7 | 12.7 |

## Step 2a: how often each cue fires (%)

| phrases | n | vocative | you | first_person | past_reported | bare_imperative |
|---|---|---|---|---|---|---|
| b19 instructions | 520 | 0.0 | 6.3 | 1.2 | 1.9 | 42.5 |
| b19 stream phrases | 30000 | 0.3 | 11.3 | 2.0 | 9.7 | 1.3 |
| b19 to_person (generated) | 160 | 10.6 | 13.8 | 20.0 | 18.1 | 0.0 |
| b19 subject (generated) | 160 | 7.5 | 16.2 | 3.1 | 20.0 | 3.8 |
| b19 foreign (real) | 160 | 1.2 | 23.1 | 1.2 | 21.2 | 0.0 |
| real directive | 502 | 0.0 | 50.2 | 3.6 | 3.2 | 13.5 |
| real ask | 33 | 0.0 | 100.0 | 0.0 | 9.1 | 0.0 |
| real commit | 85 | 0.0 | 30.6 | 41.2 | 1.2 | 17.6 |
| car in calls (SLURP car tests) | 328 | 0.0 | 8.5 | 2.4 | 0.6 | 50.0 |

## Step 2b: each cue as a veto on MiniLM contrast (threshold re-chosen so stream FA/h stay at the target)

| veto | FA/h | hits | to_person (gen.) | subject (gen.) | foreign (real) | real requests |
|---|---|---|---|---|---|---|
| none | 1 | 91.9 | 85.0 | 78.8 | 1.9 | 0.3 |
| none | 10 | 98.3 | 98.1 | 95.0 | 20.0 | 4.4 |
| vocative | 1 | 91.9 | 78.8 | 74.4 | 1.2 | 0.3 |
| vocative | 10 | 98.3 | 87.5 | 87.5 | 18.8 | 4.4 |
| you | 1 | 86.5 | 77.5 | 67.5 | 1.2 | 0.1 |
| you | 10 | 92.7 | 84.4 | 81.2 | 15.6 | 2.8 |
| first_person | 1 | 91.0 | 66.9 | 77.5 | 1.9 | 0.2 |
| first_person | 10 | 97.1 | 78.1 | 91.9 | 19.4 | 4.2 |
| past_reported | 1 | 90.6 | 71.9 | 63.7 | 1.2 | 0.3 |
| past_reported | 10 | 96.9 | 81.2 | 76.9 | 14.4 | 4.6 |
| first_person+past_reported | 1 | 89.6 | 53.8 | 62.5 | 1.2 | 0.2 |
| first_person+past_reported | 10 | 95.8 | 61.3 | 74.4 | 15.0 | 4.4 |
| all four | 1 | 84.4 | 44.4 | 50.0 | 0.0 | 0.1 |
| all four | 10 | 90.6 | 48.1 | 56.9 | 9.4 | 3.1 |

## Step 2c: learned combination (logistic regression, cross-fitted; never trained on generated phrases)

| features | FA/h | hits | to_person (gen.) | subject (gen.) | foreign (real) | real requests |
|---|---|---|---|---|---|---|
| contrast only | 1 | 92.3 | 85.6 | 78.8 | 1.9 | 0.3 |
| contrast only | 10 | 98.5 | 98.1 | 96.2 | 18.1 | 4.3 |
| + vocative | 1 | 92.3 | 84.4 | 77.5 | 1.9 | 0.3 |
| + vocative | 10 | 98.5 | 96.2 | 95.0 | 18.1 | 4.3 |
| + you | 1 | 91.9 | 84.4 | 77.5 | 1.2 | 0.1 |
| + you | 10 | 98.7 | 96.2 | 96.2 | 15.0 | 3.2 |
| + first_person | 1 | 92.1 | 84.4 | 78.8 | 1.9 | 0.2 |
| + first_person | 10 | 98.5 | 96.9 | 96.2 | 17.5 | 4.2 |
| + past_reported | 1 | 92.1 | 85.6 | 79.4 | 1.2 | 0.3 |
| + past_reported | 10 | 98.3 | 98.1 | 96.9 | 21.9 | 4.1 |
| + bare_imperative | 1 | 93.3 | 86.2 | 78.1 | 1.9 | 0.5 |
| + bare_imperative | 10 | 98.8 | 98.1 | 96.2 | 18.1 | 5.2 |
| all cues | 1 | 91.9 | 83.1 | 76.9 | 1.9 | 0.2 |
| all cues | 10 | 98.8 | 95.6 | 93.1 | 17.5 | 3.8 |

Coefficients (fold 0), all cues: {"bias": -12.882, "contrast": 6.241, "vocative": -2.096, "you": -1.951, "first_person": -1.28, "past_reported": 0.125, "bare_imperative": 0.333}

## Step 3: car instructions in real calls against real requests in other calls

| method | FA/h (brief 19 car threshold; combos: the calls' own) | car instructions found | real requests accepted | calls FA/h at that threshold | P(instruction scores above request) |
|---|---|---|---|---|---|
| keyword | 1 | 12.2 | 0.0 | 0.35 | 0.831 |
| keyword | 10 | 32.0 | 0.0 | 2.6 | 0.831 |
| shape_ngram | 1 | 85.4 | 0.3 | 0.49 | 0.994 |
| shape_ngram | 10 | 96.0 | 1.6 | 5.34 | 0.994 |
| contrast_ngram | 1 | 93.3 | 0.5 | 0.91 | 0.996 |
| contrast_ngram | 10 | 97.3 | 2.7 | 6.18 | 0.996 |
| contrast_ngram_past | 1 | 89.9 | 0.2 | 0.77 | 0.996 |
| contrast_ngram_past | 10 | 97.3 | 3.1 | 5.48 | 0.996 |
| shape_embed | 1 | 87.2 | 0.0 | 0.21 | 0.989 |
| shape_embed | 10 | 96.6 | 3.9 | 10.04 | 0.989 |
| contrast_embed | 1 | 97.0 | 0.5 | 0.56 | 0.999 |
| contrast_embed | 10 | 99.4 | 5.3 | 10.39 | 0.999 |
| contrast_embed_past | 1 | 86.0 | 0.0 | 0.21 | 0.999 |
| contrast_embed_past | 10 | 96.0 | 0.6 | 9.06 | 0.999 |
| combo: contrast only | 1 | 97.9 | 0.5 | 1 | 0.999 |
| combo: contrast only | 10 | 99.4 | 5.2 | 10 | 0.999 |
| combo: all cues | 1 | 97.9 | 1.0 | 1 | 0.999 |
| combo: all cues | 10 | 99.4 | 5.3 | 10 | 0.999 |

## Real requests accepted at 10 FA/h (MiniLM contrast): catalogue

```
{
 "accepted_pairs": 108,
 "requests": 79,
 "by_kind": {
  "directive": 83,
  "commit": 20,
  "ask": 5
 },
 "by_device": {
  "general": 21,
  "kitchen": 39,
  "watch": 15,
  "car": 33
 },
 "with_any_person_cue": 50.9,
 "by_cue": {
  "bare_imperative": 32,
  "you": 49,
  "first_person": 9
 },
 "words_median": 7.0
}
```
