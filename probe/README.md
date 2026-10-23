# probe

`daredevil_mode_activated.wav` is the phone saying "Daredevil mode activated." in the 2017 iOS 11 Siri voice.

## How it was made

Kyutai Pocket TTS, `pocket-tts` 3.1.0 on CPU (torch 2.14.0), run on the desktop:

    pocket-tts generate --voice voices/siri-ios11.safetensors --text "Daredevil mode activated."

- **Voice:** `siri-ios11.safetensors`, exported with `pocket-tts export-voice` from clips of the iOS 11 Siri voice.
- **Settings:** the default English model, with every other option at its 3.1.0 default, including sampler-decode-steps 1, eos-threshold -4.0, max-tokens 50 and device cpu.

## Format

Pocket TTS wrote a 24 kHz, mono, 16-bit PCM WAV, 1.4 s long. This file is that output resampled 2:1 with scipy's `resample_poly` to 48 kHz, mono, 16-bit PCM (134,444 bytes), because the phone's player (`Pulse.playWav`) plays every file at its fixed 48 kHz.

The phone plays this exact file (SHA-256 `2e07e6b25595bb5e9e7a469e99ed75739bf1a651a27b72acc857f0b459714dfe`), copied into the Siri app's files folder and fired with `/play?name=daredevil_mode_activated.wav`.
