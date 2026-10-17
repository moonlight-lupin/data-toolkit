# Large-file patterns — vectorised operations cheat sheet

Use with `ingest.read_large_rows` / `ingest.read_large` when a source has **10k+ rows**. Prefer vectorised pandas /
NumPy ops over Python row loops — a 200k-row ledger that finishes in seconds with the
left-hand forms can take minutes (or OOM) with the right-hand forms.

| Prefer | Avoid | Why |
|---|---|---|
| `df['col'] * 2` | `df.apply(lambda x: x * 2)` | Column arithmetic stays in C; `apply` is a Python loop |
| `df.itertuples(index=False)` | `df.iterrows()` | `iterrows` boxes every value as a Series; tuples are ~100× faster when you must iterate |
| `df[mask]` | `for i in range(len(df)): df.iloc[i]` | Boolean / fancy indexing is vectorised; `iloc` in a loop is quadratic-feeling |
| `np.where(df['a'] > 0, 'Y', 'N')` | `df['a'].map(lambda ...)` | `np.where` / boolean assignment beats per-cell Python callables |
| `df.groupby('a').agg({'b': 'sum'})` | `df.groupby('a').apply(custom_func)` | Named aggregations use the fast path; `apply` falls back to Python |

## Which reader? `read_large_rows` (drop-in) vs `read_large` (DataFrame)

- **`ingest.read_large_rows(path, sheet=None)` → `(rows, note)`** — the drop-in for `read_any`:
  the same list-of-rows shape (header row first), so `dataclean` / `analyse` run unchanged. Excel
  goes through the Parquet cache / stream path below; any other type (`.csv`, `.pdf` …) is read
  with `read_any`, so it never raises just because the file isn't Excel.
- **`ingest.read_large(path, sheet=None)` → `(DataFrame, note)`** — **`.xlsx` / `.xlsm` only**
  (raises `ValueError` on `.csv` and other extensions). Use it when you want pandas for the
  vectorised ops above. Without pandas/pyarrow it falls back to `(rows, note)` from `read_xlsx`.
  To hand a DataFrame back to the row-based engines:
  `header, rows = list(df.columns), df.values.tolist()`.

A large **CSV** is read by `ingest.read_any` (or `read_large_rows`), whose single-pass
`csv.reader` returns list-of-rows — fast (a 250k-row CSV ingests in well under a second).
Ingestion is not the bottleneck at this scale; there is no chunked/pyarrow CSV path today, so a
genuinely memory-bound CSV (millions of rows) should be pre-split or loaded via your own
`pandas.read_csv(chunksize=…)` outside the toolkit.

## Strategy reminder (`scripts/streaming.py`)

| Rows (data) | Strategy | Behaviour |
|---|---|---|
| < 10k | `direct` | Standard `pd.read_excel` / openpyxl is fine |
| 10k–100k | `parquet_cache` | Read once → Parquet cache → all subsequent reads from Parquet |
| 100k+ | `stream` | openpyxl `iter_rows` in 50k chunks → `ParquetWriter` → load Parquet |

After load, call `streaming.optimize_dtypes(df)` (downcast ints/floats, categorise
low-cardinality object columns) — typically **50–80%** memory reduction.

## Optional deps

`pyarrow` + `pandas` are optional. Without them `ingest.read_large` / `read_large_rows` fall back to a
direct openpyxl read and warn that large files may OOM. See `README.md#mode--environment-compatibility`.
