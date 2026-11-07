# Schema evolution log

The tables in `app.py` grew in three steps. Every step was reviewed with
`pxt schema diff app.py violins` (exit code 2 = changes pending) before `pxt schema update`.

## v1: initial pipeline
`instruments` (audio, voice note, typed tag lists), `take_chunks` (`audio_splitter`, 2.5 s,
silence-aware) and `tag_rows` (`list_iterator`, `mode='padded'`).

## v2: additive (safe)
- `instruments.bridge_mm: pxt.Float | None`
- `instruments.take_secs` (computed from `take_meta`)
- `take_chunks.chunk_secs = segment_end - segment_start`

`pxt schema update app.py violins` applies these without flags.

## v3: destructive + unsupported
- `family` replaced by `wood_group` (drop + add, destructive)
- `take_secs` had the wrong JSON path. Changing a computed column's expression in place is
  unsupported, so it was replaced by a new column `take_seconds`.
- `take_chunks` changed the iterator from `duration=2.5` to `duration=2.0`. An iterator change is
  unsupported in place: drop the view first, then let `schema update` recreate it.

```bash
pxt drop violins/take_chunks -f
pxt schema update app.py violins --allow-destructive -f
```

Tip: `schema update` adds a new computed column over the existing rows and stops at the first row
that raises. If old data can fail, make the UDF return a value for those rows (see
`wood_group_of` in `udfs.py`) or clean up the rows first.
