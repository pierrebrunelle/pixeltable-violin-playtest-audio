"""Violin workshop play-test audio pipeline built with Pixeltable.

A small violin workshop records a play-test take of every finished instrument
plus a spoken luthier note. Pixeltable stores the audio, transcribes the notes
locally with WhisperX, splits each take into silence-aware chunks with
audio_splitter, and fans the luthier's tag lists out into one row per tag with
list_iterator. Instruments that are not strung yet (no take, no tags) simply
produce no chunk or tag rows.

Layout: UDFs live in udfs.py; this file holds table models and @pxt.query.

    python make_audio.py
    pxt schema update app.py violins
    python run.py
"""

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf

from udfs import chunk_stamp, dynamics, loudness_dbfs, session_stamp, take_summary, wood_family, wood_group_of

TableModel = pxt.model_base()


class Instruments(TableModel, name='instruments'):
    """One finished (or nearly finished) instrument on the workshop bench."""

    instrument_id = pxt.Column(type=pxt.String, primary_key=True)
    kind: pxt.String
    pattern: pxt.String
    wood: pxt.String
    playtest: pxt.Audio | None
    voice_note: pxt.Audio | None
    tags: pxt.Json[list[str]] | None
    tag_scores: pxt.Json[list[float]] | None
    bridge_mm: pxt.Float | None  # v2: bridge height, measured at the bench

    take_meta = pxtf.audio.get_metadata(playtest)
    take_loudness = loudness_dbfs(playtest)
    wood_group = wood_group_of(wood)  # v3: replaces 'family' (tolerant of unknown woods)
    take_seconds = take_meta.streams[0].duration_seconds  # v3: replaces take_secs (bad JSON path)
    note_text = pxtf.whisperx.transcribe(voice_note, model='tiny.en', compute_type='int8', language='en')


class TakeChunks(
    TableModel,
    name='take_chunks',
    base=Instruments,
    iterator=pxtf.audio.audio_splitter(
        Instruments.playtest, duration=2.0, min_silence_len=0.3, silence_thresh=-35.0, min_segment_duration=0.4
    ),
):
    """Silence-aware chunks of every play-test take."""

    chunk_secs = segment_end - segment_start  # type: ignore[name-defined]  # noqa: F821  (v2)
    chunk_db = loudness_dbfs(audio_segment)  # type: ignore[name-defined]  # noqa: F821
    marking = dynamics(chunk_db)
    chunk_uid = pxtf.uuid.uuid4().to_string()
    session = session_stamp(Instruments.instrument_id)
    stamp = chunk_stamp(Instruments.instrument_id)
    wood_check = wood_family(Instruments.wood)


class TagRows(
    TableModel,
    name='tag_rows',
    base=Instruments,
    iterator=pxtf.json.list_iterator(tag=Instruments.tags, score=Instruments.tag_scores, mode='padded'),
):
    """One row per luthier tag (scores padded with null when the list is shorter)."""

    tag_upper = pxtf.string.upper(tag)  # type: ignore[name-defined]  # noqa: F821


@pxt.query
def loud_chunks(min_db: float):
    """Chunks at or above min_db dBFS, loudest first."""
    return (
        TakeChunks.where(TakeChunks.chunk_db >= min_db)
        .order_by(TakeChunks.chunk_db, asc=False)
        .select(TakeChunks.instrument_id, TakeChunks.segment_start, TakeChunks.segment_end, TakeChunks.chunk_db)
    )


@pxt.query
def instruments_tagged(tag: str):
    """Instruments carrying a given tag."""
    return TagRows.where(TagRows.tag == tag).select(TagRows.instrument_id, TagRows.pattern, TagRows.score)
