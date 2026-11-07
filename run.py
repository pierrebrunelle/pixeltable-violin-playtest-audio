"""Drive the violin play-test pipeline: insert instruments, inspect chunks/tags.

    pxt schema update app.py violins
    python run.py            # insert the bench + print a report
    python run.py --report   # report only
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pixeltable as pxt

HERE = Path(__file__).parent
TARGET = os.environ.get('VIOLIN_TARGET', 'violins')


def media(kind: str, iid: str) -> str | None:
    p = HERE / 'data' / kind / f'{iid}.mp3'
    return str(p) if p.exists() else None


BENCH = [
    ('VLN-0412', 'violin', 'Stradivari 1715', 'spruce', ['warm', 'quick response', 'dull G'], [0.8, 0.9, 0.4]),
    ('VLN-0415', 'violin', 'Guarneri del Gesu', 'spruce', ['bright', 'sound post'], [0.9]),
    ('VLA-0098', 'viola', 'Brothers Amati', 'maple', ['deep C', 'even'], [0.95, 0.85]),
    ('VLN-0420', 'violin', 'Stainer', 'pernambuco', None, None),  # unknown tonewood -> error cell
    ('VLN-0421', 'violin', 'Stradivari 1715', 'willow', None, None),  # not strung yet: no take, no tags
]


def insert() -> None:
    t = pxt.get_table(f'{TARGET}/instruments')
    rows = [
        {
            'instrument_id': iid,
            'kind': kind,
            'pattern': pattern,
            'wood': wood,
            'playtest': media('playtests', iid),
            'voice_note': media('notes', iid),
            'tags': tags,
            'tag_scores': scores,
        }
        for iid, kind, pattern, wood, tags, scores in BENCH
    ]
    status = t.insert(rows, on_error='ignore')
    print(f'inserted {status.num_rows} rows, {status.num_excs} errors')


def report() -> None:
    inst = pxt.get_table(f'{TARGET}/instruments')
    chunks = pxt.get_table(f'{TARGET}/take_chunks')
    tags = pxt.get_table(f'{TARGET}/tag_rows')
    print(inst.select(inst.instrument_id, inst.take_loudness, inst.wood_group, inst.take_seconds).collect())
    for r in inst.select(inst.instrument_id, inst.note_text).collect():
        text = (r['note_text'] or {}).get('segments') if r['note_text'] else None
        joined = ' '.join(s['text'].strip() for s in text) if text else None
        print(f'{r["instrument_id"]}: {joined}')
    print(
        chunks.select(
            chunks.instrument_id, chunks.segment_start, chunks.segment_end, chunks.chunk_db, chunks.marking
        ).order_by(chunks.instrument_id, chunks.segment_start).collect()
    )
    per = chunks.group_by(chunks.instrument_id).select(chunks.instrument_id, n=pxt.functions.count(chunks.pos)).collect()
    print(per)
    print(tags.select(tags.instrument_id, tags.tag, tags.score).order_by(tags.instrument_id).collect())


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if not a.report:
        insert()
    report()
