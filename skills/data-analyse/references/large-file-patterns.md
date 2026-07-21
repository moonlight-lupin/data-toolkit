# Large-file patterns — vectorised operations cheat sheet

Use with `ingest.read_large` when a source has **10k+ rows**. Prefer vectorised pandas /
NumPy ops over Python row loops — a 200k-row ledger that finishes in seconds with the
left-hand forms can take minutes (or OOM) with the right-hand forms.

| Prefer | Avoid | Why |
|---|---|---|
| `df['col'] * 2` | `df.apply(lambda x: x * 2)` | Column arithmetic stays in C; `apply` is a Python loop |
| `df.itertuples(index=False)` | `df.iterrows()` | `iterrows` boxes every value as a Series; tuples are ~100× faster when you must iterate |
| `df[mask]` | `for i in range(len(df)): df.iloc[i]` | Boolean / fancy indexing is vectorised; `iloc` in a loop is quadratic-feeling |
| `np.where(df['a'] > 0, 'Y', 'N')` | `df['a'].map(lambda ...)` | `np.where` / boolean assignment beats per-cell Python callables |
| `df.groupby('a').agg({'b': 'sum'})` | `df.groupby('a').apply(custom_func)` | Named aggregations use the fast path; `apply` falls back to Python |

## Scope: `read_large` is Excel-only — CSV goes through `read_any`

`ingest.read_large` (the Parquet cache / stream path above) supports **`.xlsx` / `.xlsm` only**.
A large **CSV** is read by `ingest.read_any`, whose single-pass `csv.reader` returns list-of-rows
— fast (a 250k-row CSV ingests in well under a second) and the shape the analyse engine expects.
Ingestion is not the bottleneck at this scale; there is no chunked/pyarrow CSV path today, so a
genuinely memory-bound CSV (millions of rows) should be pre-split or loaded via your own
`pandas.read_csv(chunksize=…)` outside the toolkit. Don't assume `read_large` will take a CSV —
it raises `ValueError` on non-Excel extensions.

## Strategy reminder (`scripts/streaming.py`)

| Rows (data) | Strategy | Behaviour |
|---|---|---|
| < 10k | `direct` | Standard `pd.read_excel` / openpyxl is fine |
| 10k–100k | `parquet_cache` | Read once → Parquet cache → all subsequent reads from Parquet |
| 100k+ | `stream` | openpyxl `iter_rows` in 50k chunks → `ParquetWriter` → load Parquet |

After load, call `streaming.optimize_dtypes(df)` (downcast ints/floats, categorise
low-cardinality object columns) — typically **50–80%** memory reduction.

## Optional deps

`pyarrow` + `pandas` are optional. Without them `ingest.read_large` falls back to a
direct openpyxl read and warns that large files may OOM. See `README.md#mode--environment-compatibility`.
