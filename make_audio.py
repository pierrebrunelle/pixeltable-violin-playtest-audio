"""Generate the demo media once: synthetic violin play-test takes (numpy, offline)
and three short spoken luthier notes (OpenAI TTS, 3 calls; skipped if present).

    python make_audio.py
"""
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
SR = 22050

# instrument_id -> list of (note frequency Hz, seconds, vibrato depth), with silence between phrases
TAKES = {
    'VLN-0412': [(196.0, 1.6, 0.004), (293.7, 1.4, 0.005), (440.0, 1.8, 0.006), (659.3, 1.2, 0.006)],
    'VLN-0415': [(220.0, 2.2, 0.003), (330.0, 1.0, 0.0), (523.3, 2.4, 0.007)],
    'VLA-0098': [(130.8, 2.0, 0.004), (196.0, 2.0, 0.004), (293.7, 1.5, 0.005)],
    'VLN-0420': [(392.0, 0.9, 0.006), (493.9, 0.9, 0.006), (587.3, 0.9, 0.006), (784.0, 1.6, 0.008)],
}

NOTES = {
    'VLN-0412': ('onyx', 'Violin four twelve, Stradivari pattern, spruce top. The G string is a little dull, '
                         'otherwise the response is quick. Ready for varnish touch-up.'),
    'VLN-0415': ('nova', 'Four fifteen, Guarneri model. Bright E string, maybe too bright. '
                         'I want to move the sound post half a millimeter before the next play test.'),
    'VLA-0098': ('echo', 'Viola ninety eight. Deep C string, very even across the strings. '
                         'Customer pickup on Friday.'),
}


def bowed(freq: float, secs: float, vib: float) -> np.ndarray:
    t = np.arange(int(SR * secs)) / SR
    phase = 2 * np.pi * freq * (t + vib * np.sin(2 * np.pi * 5.5 * t) / (2 * np.pi * 5.5) * 2 * np.pi)
    # sawtooth-ish harmonic stack, like a bowed string
    sig = sum(np.sin(k * phase) / k for k in range(1, 9))
    env = np.minimum(1.0, t / 0.08) * np.minimum(1.0, (secs - t) / 0.15)
    return 0.25 * sig * env


def write_wav(path: Path, sig: np.ndarray) -> None:
    pcm = (np.clip(sig, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> None:
    for iid, phrases in TAKES.items():
        out = HERE / 'data' / 'playtests' / f'{iid}.mp3'
        if out.exists():
            continue
        parts = []
        for f, s, v in phrases:
            parts += [bowed(f, s, v), np.zeros(int(SR * 0.45))]
        wav = out.with_suffix('.wav')
        write_wav(wav, np.concatenate(parts))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-b:a', '96k', str(out)], check=True)
        wav.unlink()
        print('take', out.name)
    if not os.environ.get('OPENAI_API_KEY'):
        print('OPENAI_API_KEY not set; skipping spoken notes')
        return
    from openai import OpenAI

    client = OpenAI()
    for iid, (voice, text) in NOTES.items():
        out = HERE / 'data' / 'notes' / f'{iid}.mp3'
        if out.exists():
            continue
        r = client.audio.speech.create(model='gpt-4o-mini-tts', voice=voice, input=text, response_format='mp3')
        out.write_bytes(r.content)
        print('note', out.name)


if __name__ == '__main__':
    main()
