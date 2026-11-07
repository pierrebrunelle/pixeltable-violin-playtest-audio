"""UDFs for the violin workshop play-test pipeline (pure Python, no table imports)."""

from __future__ import annotations

import uuid

import av
import numpy as np
import pixeltable as pxt

KNOWN_WOODS = {'spruce', 'maple', 'willow', 'poplar'}


@pxt.udf()
def session_stamp(instrument_id: str) -> str:
    """Parenthesized @pxt.udf(): deterministic by default since pxt 0.7.24 (#1913).

    Inside a component view it is evaluated once per base row, so every chunk of
    one take shares the same stamp.
    """
    return f'{instrument_id}:{uuid.uuid4().hex[:8]}'


@pxt.udf(is_deterministic=False)
def chunk_stamp(instrument_id: str) -> str:
    """Explicitly nondeterministic: evaluated per chunk row."""
    return f'{instrument_id}:{uuid.uuid4().hex[:8]}'


@pxt.udf
def wood_family(wood: str) -> str:
    """Tonewood family; raises on an unknown wood so the cell holds an error."""
    w = wood.strip().lower()
    if w not in KNOWN_WOODS:
        raise ValueError(f'unknown tonewood: {wood!r}')
    return 'top' if w == 'spruce' else 'back/sides'


@pxt.udf
def loudness_dbfs(audio: pxt.Audio) -> float:
    """Mean loudness of an audio file in dBFS (decoded with PyAV)."""
    with av.open(str(audio)) as c:
        frames = [f.to_ndarray().astype(np.float64) for f in c.decode(audio=0)]
    if not frames:
        return -120.0
    x = np.concatenate([f.reshape(-1) for f in frames])
    if np.issubdtype(frames[0].dtype, np.integer):
        x = x / 32768.0
    rms = float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0
    return round(20 * np.log10(max(rms, 1e-6)), 1)


@pxt.udf
def dynamics(dbfs: float) -> str:
    """Rough dynamic marking for a chunk."""
    if dbfs < -45:
        return 'rest'
    if dbfs < -24:
        return 'piano'
    if dbfs < -16:
        return 'mezzo'
    return 'forte'


@pxt.udf
def take_summary(duration: float, sample_rate: int) -> str:
    return f'{duration:.1f}s @ {sample_rate} Hz'


@pxt.udf
def wood_group_of(wood: str) -> str:
    """Tolerant variant used by the v3 schema: unknown woods map to 'unknown'.

    `pxt schema update` adds computed columns over existing rows with on_error='abort',
    so a column that can fail on old data blocks the migration.
    """
    w = wood.strip().lower()
    if w not in KNOWN_WOODS:
        return 'unknown'
    return 'top' if w == 'spruce' else 'back/sides'
