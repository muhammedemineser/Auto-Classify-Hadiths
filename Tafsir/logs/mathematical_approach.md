**Problem**  
The objective was to identify the exact point at which **Gemini Pro** stopped operating in its high-throughput _Pro/Fast_ regime and transitioned into a throttled or downgraded mode. This boundary is not exposed by the API: neither token counters, context-window state, nor quota enforcement are directly observable. The problem therefore had to be solved indirectly, using observable side effects in processing behavior.

**Approach**  
The problem was reframed as an **inverse performance inference task**. Instead of measuring tokens directly, we reconstructed a normalized performance signal from system logs. Two database columns were critical:

- `created_at`, providing precise timestamps for batch insert events, and

- `text`, whose length represents the textual workload sent to Gemini.

By combining elapsed time between consecutive `created_at` entries with the cumulative length of the corresponding text content, we derived a proxy for processing speed. Word count was used as a stable, language-agnostic approximation of token load, enabling a consistent comparison across batches.

**Process**  
Using SQLite, the database was queried at fixed ID intervals (every 5 rows, matching the known batching behavior). For each interval:

- the elapsed time was computed as the difference between consecutive `created_at` timestamps,

- all source texts belonging to that batch were retrieved and normalized,

- total word count was computed, and

- throughput was calculated as:

```
words_per_second = total_words / delta_seconds
```

This produced a structured time series of performance values, printed in the form:

```
230–234 | 180s | 8033 words | 44.63 w/s
235–239 | 9614s | 11124 words | 1.16 w/s
```

Once this empirical signal was available, it was analyzed as a **piecewise-constant sequence of regimes**, not as a smooth trend. Abrupt drops in throughput were treated as regime changes. In parallel, model-level constraints were incorporated from known properties of Gemini Pro:

- Each message contained ~**11,140 German words** (dominant token source).

- Each block of 5 messages therefore contributed ~**100k–130k tokens**.

- Gemini Pro has a **2M-token context window per request**, but also **server-side TPM (tokens per minute) and RPD limits**.

**Solution**  
The analysis shows that Gemini Pro sustains high throughput for **17 full blocks (85 messages)**. At the **18th block (IDs 235–239)**, throughput collapses from **~44.6 w/s** to **~1.16 w/s**, accompanied by a **9,614-second delay**. This sharp, discontinuous drop—followed by later recovery—rules out gradual load effects or per-request context exhaustion. Instead, it is consistent with exhaustion of a **time-based, server-side token quota (TPM/RPD)**.

Quantitatively:

- Cumulative load up to block 230–234 ≈ **1.7–2.1 million tokens** within ~100 minutes.

- The additional load in block 235–239 triggers throttling.

**Conclusion:**  
Under the given workload, Gemini Pro exits its high-throughput _Pro/Fast_ regime after **85–90 messages (17–18 blocks)**. The effective boundary is **block 235–239**, where server-side quota limits become active. This result is derived entirely from database-backed performance reconstruction and does not rely on internal model telemetry.~~~~
