<!-- pixeltable-example-app: 20261107-violin-playtest-audio -->
# violin workshop play-test recordings media pipeline built with Pixeltable

![violin workshop play-test recordings media pipeline built with Pixeltable](.github/social-preview.png)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pierrebrunelle/pixeltable-violin-playtest-audio?quickstart=1)
[![Built with Pixeltable](https://img.shields.io/badge/built%20with-Pixeltable-5b4bff)](https://pixeltable.com)
[![PyPI - pixeltable](https://img.shields.io/pypi/v/pixeltable?label=pixeltable)](https://pypi.org/project/pixeltable/)
[![GitHub stars](https://img.shields.io/github/stars/pixeltable/pixeltable?style=social)](https://github.com/pixeltable/pixeltable)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

A small violin workshop records a play-test take and a spoken luthier note for every instrument on the bench. This Pixeltable media pipeline stores the audio, measures loudness, transcribes the notes locally with WhisperX, cuts each take into silence-aware chunks with audio_splitter, and fans the luthier's tag lists out into one row per tag with list_iterator. Instruments that are not strung yet simply produce no chunk or tag rows. The schema evolves in three steps with pxt schema diff/update, including a destructive change and an iterator change.

[Pixeltable](https://pixeltable.com) is open-source, Python-native **multimodal AI data infrastructure**: tables, incremental computed columns, UDFs, indexes and serving in one library, running locally or on Pixeltable Cloud.

> ⭐ **Like this example?** Star [pixeltable/pixeltable](https://github.com/pixeltable/pixeltable) on GitHub. It helps other developers find it.

## What this example shows

- **Incremental computed columns** powered by plain Python UDFs (`@pxt.udf`)
- **Multimodal media columns** with configurable media destinations
- **Importable UDF module**: UDFs live in `udfs.py`; tables and queries live in `app.py` (Pixeltable resolves UDFs by module path)
- **`pixeltable.toml`** declares a local database and a **Pixeltable Cloud** database, so the same code deploys with `pxt db update`



## What's inside

| File | What it is |
|------|------------|
| `.devcontainer/devcontainer.json` | GitHub Codespaces / Dev Container config: Python 3.12, installs `requirements.txt` |
| `.github/social-preview.png` | Social preview image (1280x640) |
| `CITATION.cff` | Citation metadata (authors, license, release date, keywords) |
| `MIGRATIONS.md` | Sample data |
| `app.py` | Tables declared as Python classes and `@pxt.query` functions |
| `data/notes/VLA-0098.mp3` | Sample data |
| `data/notes/VLN-0412.mp3` | Sample data |
| `data/notes/VLN-0415.mp3` | Sample data |
| `data/playtests/VLA-0098.mp3` | Sample data |
| `data/playtests/VLN-0412.mp3` | Sample data |
| `data/playtests/VLN-0415.mp3` | Sample data |
| `data/playtests/VLN-0420.mp3` | Sample data |
| `make_audio.py` | Generate the demo media once: synthetic violin play-test takes (numpy, offline) |
| `pixeltable.toml` | Project config: the local database plus a Pixeltable Cloud database (sizing, deploy excludes) |
| `run.py` | Drive the violin play-test pipeline: insert instruments, inspect chunks/tags |
| `udfs.py` | Pixeltable UDFs (`@pxt.udf`) in their own importable module, imported by `app.py` |
| `requirements.txt` / `pyproject.toml` | Dependencies (`pixeltable>=0.7.24`) |

**Tables**

| Table | Stored columns | Computed columns |
|-------|---------|------------------|
| `instruments` | `instrument_id`, `kind`, `pattern`, `wood`, `playtest`, `voice_note`, `tags`, `tag_scores`, `bridge_mm` | `take_meta`, `take_loudness`, `wood_group`, `note_text` |
| `take_chunks` | - | `chunk_db`, `marking`, `chunk_uid`, `session`, `stamp`, `wood_check` |
| `tag_rows` | - | `tag_upper` |

## Run in your browser (GitHub Codespaces)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pierrebrunelle/pixeltable-violin-playtest-audio?quickstart=1)

1. Click **Open in GitHub Codespaces** above (or [this link](https://codespaces.new/pierrebrunelle/pixeltable-violin-playtest-audio?quickstart=1)). The dev container installs Python 3.12 and `pixeltable>=0.7.24` from `requirements.txt`.
2. In the codespace terminal, create the tables, seed them and run the app:

   ```bash
   pxt schema update app.py violins
   python make_audio.py  # synthetic takes offline; spoken notes need OPENAI_API_KEY (3 TTS calls)
   python run.py
   ```


## Quickstart

Requires Python 3.11+ and `pixeltable>=0.7.24`.

```bash
git clone https://github.com/pierrebrunelle/pixeltable-violin-playtest-audio.git
cd pixeltable-violin-playtest-audio
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create the tables in a local catalog directory named `violins`
pxt schema update app.py violins

python make_audio.py  # synthetic takes offline; spoken notes need OPENAI_API_KEY (3 TTS calls)
python run.py
```

## Deploy to Pixeltable Cloud

The same `app.py` runs on [Pixeltable Cloud](https://pixeltable.com). Sign in (or get a free trial database with `pxt new`), point the second database entry in `pixeltable.toml` at your own database, then deploy:

```bash
pxt login                       # or: export PIXELTABLE_API_KEY=<your-api-key>
# edit pixeltable.toml: name = 'pxt://<your-org>:<your-db>'
pxt db update pxt://<your-org>:<your-db>                 # build the image and upload the project
pxt schema update app.py pxt://<your-org>:<your-db>       # create the tables at the database root (no per-app folder)
```

Keep keys in environment variables or `pxt secret set`, never in code.

## Code walkthrough

**1. Business logic is plain Python, in `udfs.py`.** A `@pxt.udf` function can be used as a column expression. Pixeltable records UDFs by module path (`udfs.session_stamp`), so they live in their own importable module rather than inline in the app: the daemon, serving workers and Pixeltable Cloud import it again by that path.

```python
# udfs.py
@pxt.udf()
def session_stamp(instrument_id: str) -> str:
    """Parenthesized @pxt.udf(): deterministic by default since pxt 0.7.24 (#1913).

    Inside a component view it is evaluated once per base row, so every chunk of
    one take shares the same stamp.
    """
    return f'{instrument_id}:{uuid.uuid4().hex[:8]}'
```

**2. Tables are Python classes (`app.py`).** Annotated attributes are stored columns; attributes assigned an expression are **computed columns** (`chunk_db`, `marking`, `chunk_uid`, `session`, `stamp`, `wood_check`), evaluated incrementally on every insert or update and recomputed when their inputs change.

```python
# app.py
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
```

**3. Queries are functions (`app.py`).** `@pxt.query` wraps a Pixeltable query so it can be called from Python or exposed as a route:

```python
# app.py
@pxt.query
def loud_chunks(min_db: float):
    """Chunks at or above min_db dBFS, loudest first."""
    return (
        TakeChunks.where(TakeChunks.chunk_db >= min_db)
        .order_by(TakeChunks.chunk_db, asc=False)
        .select(TakeChunks.instrument_id, TakeChunks.segment_start, TakeChunks.segment_end, TakeChunks.chunk_db)
    )
```

## Learn more

- 🌐 Website: https://pixeltable.com
- 📚 Docs: https://docs.pixeltable.com
- 💻 Source: https://github.com/pixeltable/pixeltable (⭐ star it if Pixeltable is useful to you)
- 📦 PyPI: https://pypi.org/project/pixeltable/
- 🧩 More example apps: https://pierrebrunelle.github.io/awesome-pixeltable-apps/

**[More Pixeltable example apps →](https://pierrebrunelle.github.io/awesome-pixeltable-apps/)**

---

<sub>Built as part of a daily series of Pixeltable example apps · Pixeltable 0.7.24 · Python, incremental computed columns · Licensed under Apache-2.0.</sub>
