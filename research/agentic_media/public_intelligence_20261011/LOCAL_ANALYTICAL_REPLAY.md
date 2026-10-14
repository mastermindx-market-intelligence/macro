# Independent NVIDIA technical replay

The public dossier suggested useful analytical context, but its stockdata endpoint returned HTTP401 to one anonymous read. That endpoint was not retried or recovered through another identity, cache, host or carrier. No protected-output parity is claimed.

A bounded release/rights review accepted a different action: replay the incumbent pure engine against the separately authorized, committed `data/stocks/NVDA.parquet` input. The script binds exact input and engine hashes, validates the complete bar index and OHLCV ranges, and independently recomputes both moving-average distances. It never calls the data collector, a provider, Press planning/staging or publication.

Command run successfully:

```sh
python3 research/agentic_media/public_intelligence_20261011/replay_nvda_technicals.py --source-revision 9b86baae61ccaa858d99b53ee1023cbe866e9a4f
```

The input contains6,971 daily bars from1999-01-22 through2026-10-08. The calculation ran on2026-10-11. Those are different clocks. No rows were dropped or changed; complete finite inputs, coherent ranges, bounded indicators and two independent arithmetic checks passed. The replay binds the incumbent collector recipe (`StockPriceAdapter`, Yahoo `auto_adjust=True`) but cannot independently verify the historical vendor adjustment process or infer a license from public Git availability.

The computed values and full receipt are retained outside public Git in the operation's local evidence directory. `nvda_local_replay_manifest.json` binds that receipt without publishing the derived values. Analytical computation is first-party; the underlying market observations and government-event facts retain external provenance. Derived-publication rights remain unqualified, and stage/emit are false. The values have not been inserted into the article to manufacture validation acceptance.

Falsifier: changed input or engine hashes, a bar defect, failed independent arithmetic, or a disqualifying producer-rights scope prevents use of this replay. Qualification would require the applicable producer/derived-use rights and a real Brief intake before article acceptance. A later protected-endpoint or installed-engine check would be a separate proof, never implied by matching a visible number.
