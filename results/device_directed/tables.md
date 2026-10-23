## Pooled over the four devices

| method | model size | time per phrase | mean hit rate, 0-60 FA/h | hits at 1 FA/h | hits at 10 FA/h | hard negatives accepted at 10 FA/h: to a person / subject | foreign-phrase control accepted |
|---|---|---|---|---|---|---|---|
| keyword spotting | 645 bytes | 0.01 ms | 58% | 8.8% | 32.7% | 51.9% / 21.2% | 2.5% |
| shape only (n-gram) | 11.2 MB | 0.05 ms | 94% | 82.9% | 92.1% | 74.4% / 58.1% | 0.0% |
| shape and contrast (Jay's), n-gram | 11.2 MB | 0.17 ms | 96% | 83.8% | 94.6% | 81.9% / 71.2% | 0.6% |
| shape and contrast, n-gram, past context only | 11.2 MB | 0.11 ms | 95% | 83.1% | 93.5% | 76.2% / 63.1% | 0.0% |
| shape only (MiniLM) | 90.4 MB | 0.65 ms | 92% | 61.0% | 89.4% | 88.1% / 69.4% | 1.9% |
| shape and contrast (Jay's), MiniLM | 90.4 MB | 0.47 ms | 99% | 89.2% | 98.5% | 95.6% / 92.5% | 13.1% |
| shape and contrast, MiniLM, past context only | 90.4 MB | 0.51 ms | 95% | 71.7% | 92.3% | 85.6% / 80.6% | 2.5% |

## Per device, at 1 false accept(s) per hour

| method | device | hits | ami | calls (speakerphone) | lyrics | monologue | hard: to a person | hard: subject | foreign control |
|---|---|---|---|---|---|---|---|---|---|
| keyword spotting | car | 9.2% | 7.5% (0.0/h) | 15.0% (0.3/h) | 5.0% (0.0/h) | 10.0% (0.0/h) | 27.5% | 0.0% | 0.0% |
| keyword spotting | kitchen | 8.5% | 7.5% (0.0/h) | 12.5% (0.5/h) | 7.5% (0.0/h) | 0.0% (0.0/h) | 20.0% | 0.0% | 2.5% |
| keyword spotting | watch | 16.2% | 20.0% (0.4/h) | 17.5% (0.0/h) | 10.0% (0.0/h) | 20.0% (0.0/h) | 25.0% | 15.0% | 0.0% |
| keyword spotting | general | 1.5% | 0.0% (1.3/h) | 0.0% (0.0/h) | 5.0% (0.5/h) | 0.0% (0.0/h) | 7.5% | 0.0% | 0.0% |
| shape only (n-gram) | car | 86.9% | 90.0% (1.3/h) | 82.5% (1.3/h) | 87.5% (0.0/h) | 90.0% (0.0/h) | 47.5% | 0.0% | 0.0% |
| shape only (n-gram) | kitchen | 78.5% | 87.5% (0.7/h) | 80.0% (1.2/h) | 72.5% (0.5/h) | 60.0% (0.0/h) | 42.5% | 15.0% | 0.0% |
| shape only (n-gram) | watch | 89.2% | 95.0% (1.1/h) | 90.0% (1.3/h) | 82.5% (0.0/h) | 90.0% (0.0/h) | 65.0% | 45.0% | 0.0% |
| shape only (n-gram) | general | 68.5% | 75.0% (2.0/h) | 70.0% (0.7/h) | 65.0% (0.0/h) | 50.0% (0.0/h) | 20.0% | 37.5% | 0.0% |
| shape and contrast (Jay's), n-gram | car | 93.1% | 97.5% (2.0/h) | 90.0% (0.5/h) | 92.5% (0.0/h) | 90.0% (3.7/h) | 67.5% | 12.5% | 0.0% |
| shape and contrast (Jay's), n-gram | kitchen | 79.2% | 87.5% (1.6/h) | 80.0% (1.0/h) | 75.0% (0.0/h) | 60.0% (0.0/h) | 42.5% | 15.0% | 0.0% |
| shape and contrast (Jay's), n-gram | watch | 88.5% | 95.0% (1.8/h) | 87.5% (0.8/h) | 82.5% (0.0/h) | 90.0% (0.0/h) | 67.5% | 42.5% | 0.0% |
| shape and contrast (Jay's), n-gram | general | 76.2% | 85.0% (2.0/h) | 72.5% (0.7/h) | 75.0% (0.0/h) | 60.0% (0.0/h) | 27.5% | 37.5% | 0.0% |
| shape and contrast, n-gram, past context only | car | 90.0% | 92.5% (1.7/h) | 87.5% (1.0/h) | 90.0% (0.0/h) | 90.0% (0.0/h) | 60.0% | 0.0% | 0.0% |
| shape and contrast, n-gram, past context only | kitchen | 79.2% | 87.5% (1.3/h) | 80.0% (1.0/h) | 75.0% (0.5/h) | 60.0% (0.0/h) | 42.5% | 15.0% | 0.0% |
| shape and contrast, n-gram, past context only | watch | 88.5% | 95.0% (1.8/h) | 87.5% (0.8/h) | 82.5% (0.0/h) | 90.0% (0.0/h) | 60.0% | 45.0% | 0.0% |
| shape and contrast, n-gram, past context only | general | 70.0% | 75.0% (2.0/h) | 70.0% (0.7/h) | 67.5% (0.0/h) | 60.0% (0.0/h) | 20.0% | 35.0% | 0.0% |
| shape only (MiniLM) | car | 85.4% | 85.0% (2.0/h) | 85.0% (0.8/h) | 85.0% (0.0/h) | 90.0% (0.0/h) | 77.5% | 47.5% | 0.0% |
| shape only (MiniLM) | kitchen | 82.3% | 90.0% (0.7/h) | 82.5% (1.7/h) | 77.5% (0.0/h) | 70.0% (0.0/h) | 80.0% | 52.5% | 0.0% |
| shape only (MiniLM) | watch | 79.2% | 82.5% (2.8/h) | 85.0% (0.0/h) | 72.5% (0.0/h) | 70.0% (0.0/h) | 62.5% | 47.5% | 0.0% |
| shape only (MiniLM) | general | 47.7% | 50.0% (1.0/h) | 42.5% (1.5/h) | 52.5% (0.0/h) | 40.0% (0.0/h) | 22.5% | 20.0% | 0.0% |
| shape and contrast (Jay's), MiniLM | car | 95.4% | 100.0% (2.3/h) | 95.0% (0.5/h) | 92.5% (0.0/h) | 90.0% (0.0/h) | 92.5% | 67.5% | 2.5% |
| shape and contrast (Jay's), MiniLM | kitchen | 97.7% | 97.5% (1.3/h) | 100.0% (1.0/h) | 97.5% (0.0/h) | 90.0% (3.9/h) | 90.0% | 97.5% | 5.0% |
| shape and contrast (Jay's), MiniLM | watch | 95.4% | 90.0% (2.8/h) | 100.0% (0.0/h) | 95.0% (0.0/h) | 100.0% (0.0/h) | 95.0% | 87.5% | 0.0% |
| shape and contrast (Jay's), MiniLM | general | 79.2% | 72.5% (1.6/h) | 75.0% (1.0/h) | 92.5% (0.0/h) | 70.0% (0.0/h) | 60.0% | 57.5% | 0.0% |
| shape and contrast, MiniLM, past context only | car | 87.7% | 87.5% (1.3/h) | 87.5% (1.3/h) | 87.5% (0.0/h) | 90.0% (0.0/h) | 70.0% | 42.5% | 0.0% |
| shape and contrast, MiniLM, past context only | kitchen | 89.2% | 97.5% (0.0/h) | 87.5% (2.0/h) | 87.5% (0.5/h) | 70.0% (0.0/h) | 85.0% | 82.5% | 0.0% |
| shape and contrast, MiniLM, past context only | watch | 86.9% | 85.0% (2.5/h) | 92.5% (0.3/h) | 85.0% (0.0/h) | 80.0% (0.0/h) | 77.5% | 70.0% | 0.0% |
| shape and contrast, MiniLM, past context only | general | 59.2% | 60.0% (2.0/h) | 57.5% (0.7/h) | 62.5% (0.0/h) | 50.0% (0.0/h) | 12.5% | 25.0% | 0.0% |

## Per device, at 10 false accept(s) per hour

| method | device | hits | ami | calls (speakerphone) | lyrics | monologue | hard: to a person | hard: subject | foreign control |
|---|---|---|---|---|---|---|---|---|---|
| keyword spotting | car | 31.5% | 30.0% (1.3/h) | 42.5% (3.1/h) | 22.5% (0.0/h) | 30.0% (0.0/h) | 62.5% | 10.0% | 2.5% |
| keyword spotting | kitchen | 36.9% | 37.5% (4.9/h) | 40.0% (5.0/h) | 40.0% (0.5/h) | 10.0% (3.9/h) | 55.0% | 0.0% | 5.0% |
| keyword spotting | watch | 48.5% | 50.0% (3.6/h) | 52.5% (4.8/h) | 45.0% (1.1/h) | 40.0% (0.0/h) | 65.0% | 65.0% | 0.0% |
| keyword spotting | general | 13.8% | 10.0% (8.9/h) | 7.5% (4.9/h) | 25.0% (1.9/h) | 10.0% (0.0/h) | 25.0% | 10.0% | 2.5% |
| shape only (n-gram) | car | 96.2% | 97.5% (19.0/h) | 95.0% (5.1/h) | 97.5% (1.5/h) | 90.0% (40.6/h) | 82.5% | 32.5% | 0.0% |
| shape only (n-gram) | kitchen | 84.6% | 92.5% (21.6/h) | 85.0% (4.7/h) | 82.5% (1.6/h) | 60.0% (11.6/h) | 70.0% | 42.5% | 0.0% |
| shape only (n-gram) | watch | 96.2% | 97.5% (16.0/h) | 100.0% (6.3/h) | 90.0% (3.4/h) | 100.0% (25.6/h) | 82.5% | 82.5% | 0.0% |
| shape only (n-gram) | general | 92.3% | 92.5% (16.8/h) | 90.0% (10.3/h) | 95.0% (0.0/h) | 90.0% (7.7/h) | 60.0% | 90.0% | 0.0% |
| shape and contrast (Jay's), n-gram | car | 96.9% | 97.5% (16.0/h) | 97.5% (7.6/h) | 97.5% (2.5/h) | 90.0% (29.5/h) | 92.5% | 55.0% | 0.0% |
| shape and contrast (Jay's), n-gram | kitchen | 90.8% | 97.5% (14.4/h) | 87.5% (7.7/h) | 90.0% (2.7/h) | 80.0% (42.4/h) | 82.5% | 60.0% | 0.0% |
| shape and contrast (Jay's), n-gram | watch | 96.9% | 97.5% (21.0/h) | 100.0% (4.8/h) | 92.5% (1.7/h) | 100.0% (25.6/h) | 90.0% | 90.0% | 0.0% |
| shape and contrast (Jay's), n-gram | general | 93.1% | 95.0% (20.1/h) | 90.0% (7.8/h) | 95.0% (0.0/h) | 90.0% (7.7/h) | 57.5% | 90.0% | 0.0% |
| shape and contrast, n-gram, past context only | car | 96.2% | 97.5% (17.3/h) | 95.0% (6.4/h) | 97.5% (3.0/h) | 90.0% (29.5/h) | 90.0% | 52.5% | 0.0% |
| shape and contrast, n-gram, past context only | kitchen | 90.8% | 97.5% (17.7/h) | 87.5% (6.5/h) | 90.0% (1.6/h) | 80.0% (30.8/h) | 82.5% | 60.0% | 0.0% |
| shape and contrast, n-gram, past context only | watch | 95.4% | 97.5% (11.0/h) | 100.0% (4.5/h) | 87.5% (1.1/h) | 100.0% (11.0/h) | 82.5% | 80.0% | 0.0% |
| shape and contrast, n-gram, past context only | general | 93.1% | 95.0% (17.5/h) | 90.0% (9.6/h) | 95.0% (0.0/h) | 90.0% (11.6/h) | 62.5% | 90.0% | 0.0% |
| shape only (MiniLM) | car | 96.2% | 97.5% (13.7/h) | 100.0% (11.7/h) | 92.5% (1.5/h) | 90.0% (3.7/h) | 97.5% | 77.5% | 0.0% |
| shape only (MiniLM) | kitchen | 95.4% | 97.5% (6.5/h) | 95.0% (16.2/h) | 95.0% (2.7/h) | 90.0% (3.9/h) | 92.5% | 92.5% | 7.5% |
| shape only (MiniLM) | watch | 96.2% | 95.0% (22.1/h) | 100.0% (6.0/h) | 92.5% (0.6/h) | 100.0% (3.7/h) | 100.0% | 95.0% | 2.5% |
| shape only (MiniLM) | general | 75.4% | 70.0% (18.8/h) | 70.0% (9.1/h) | 85.0% (0.5/h) | 80.0% (0.0/h) | 70.0% | 55.0% | 0.0% |
| shape and contrast (Jay's), MiniLM | car | 100.0% | 100.0% (17.0/h) | 100.0% (8.9/h) | 100.0% (1.5/h) | 100.0% (7.4/h) | 97.5% | 95.0% | 27.5% |
| shape and contrast (Jay's), MiniLM | kitchen | 100.0% | 100.0% (15.4/h) | 100.0% (9.2/h) | 100.0% (0.5/h) | 100.0% (23.1/h) | 100.0% | 100.0% | 22.5% |
| shape and contrast (Jay's), MiniLM | watch | 100.0% | 100.0% (21.7/h) | 100.0% (5.8/h) | 100.0% (1.1/h) | 100.0% (7.3/h) | 100.0% | 97.5% | 12.5% |
| shape and contrast (Jay's), MiniLM | general | 93.1% | 95.0% (18.8/h) | 90.0% (7.8/h) | 97.5% (0.9/h) | 80.0% (15.4/h) | 95.0% | 87.5% | 15.0% |
| shape and contrast, MiniLM, past context only | car | 96.2% | 100.0% (16.7/h) | 97.5% (9.4/h) | 92.5% (2.0/h) | 90.0% (0.0/h) | 95.0% | 67.5% | 2.5% |
| shape and contrast, MiniLM, past context only | kitchen | 96.9% | 97.5% (11.1/h) | 100.0% (12.2/h) | 95.0% (3.2/h) | 90.0% (7.7/h) | 90.0% | 85.0% | 5.0% |
| shape and contrast, MiniLM, past context only | watch | 97.7% | 92.5% (17.4/h) | 100.0% (8.8/h) | 100.0% (0.6/h) | 100.0% (11.0/h) | 100.0% | 95.0% | 0.0% |
| shape and contrast, MiniLM, past context only | general | 80.0% | 75.0% (15.5/h) | 75.0% (11.0/h) | 92.5% (0.9/h) | 70.0% (3.9/h) | 75.0% | 67.5% | 0.0% |

(Each stream cell: hits there, and that stream's own false accepts per hour at the device's threshold.)

## Failing conditions (best method under 50% hits at 10 FA/h)

None.

## False accepts at 10 per hour, by kind

| method | device | false accepts | short (<= 2 words) | device vocabulary | request shape | question | other |
|---|---|---|---|---|---|---|---|
| keyword spotting | car | 16 | 0 | 16 | 0 | 0 | 0 |
| keyword spotting | kitchen | 37 | 0 | 37 | 0 | 0 | 0 |
| keyword spotting | watch | 31 | 0 | 31 | 0 | 0 | 0 |
| keyword spotting | general | 51 | 0 | 51 | 0 | 0 | 0 |
| shape only (n-gram) | car | 91 | 53 | 2 | 0 | 7 | 29 |
| shape only (n-gram) | kitchen | 91 | 77 | 3 | 0 | 4 | 7 |
| shape only (n-gram) | watch | 83 | 37 | 7 | 0 | 11 | 28 |
| shape only (n-gram) | general | 95 | 41 | 7 | 2 | 17 | 28 |
| shape and contrast (Jay's), n-gram | car | 91 | 59 | 2 | 1 | 7 | 22 |
| shape and contrast (Jay's), n-gram | kitchen | 91 | 61 | 3 | 0 | 4 | 23 |
| shape and contrast (Jay's), n-gram | watch | 88 | 52 | 3 | 0 | 11 | 22 |
| shape and contrast (Jay's), n-gram | general | 95 | 61 | 4 | 2 | 10 | 18 |
| shape and contrast, n-gram, past context only | car | 91 | 58 | 2 | 0 | 7 | 24 |
| shape and contrast, n-gram, past context only | kitchen | 91 | 69 | 3 | 0 | 6 | 13 |
| shape and contrast, n-gram, past context only | watch | 54 | 30 | 4 | 0 | 7 | 13 |
| shape and contrast, n-gram, past context only | general | 95 | 48 | 6 | 1 | 14 | 26 |
| shape only (MiniLM) | car | 91 | 7 | 20 | 0 | 9 | 55 |
| shape only (MiniLM) | kitchen | 91 | 5 | 38 | 0 | 5 | 43 |
| shape only (MiniLM) | watch | 88 | 12 | 38 | 0 | 6 | 32 |
| shape only (MiniLM) | general | 95 | 29 | 25 | 0 | 10 | 31 |
| shape and contrast (Jay's), MiniLM | car | 91 | 7 | 16 | 1 | 8 | 59 |
| shape and contrast (Jay's), MiniLM | kitchen | 91 | 13 | 22 | 1 | 7 | 48 |
| shape and contrast (Jay's), MiniLM | watch | 88 | 12 | 32 | 1 | 7 | 36 |
| shape and contrast (Jay's), MiniLM | general | 95 | 27 | 15 | 0 | 11 | 42 |
| shape and contrast, MiniLM, past context only | car | 91 | 36 | 11 | 0 | 8 | 36 |
| shape and contrast, MiniLM, past context only | kitchen | 91 | 24 | 13 | 1 | 7 | 46 |
| shape and contrast, MiniLM, past context only | watch | 88 | 19 | 27 | 0 | 6 | 36 |
| shape and contrast, MiniLM, past context only | general | 95 | 29 | 18 | 1 | 9 | 38 |
