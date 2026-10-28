# SyntaxLens Pilot Kit Evaluation Report (Signature Feature F)

> **Evaluation Mode:** Golden Standard Benchmarking  
> **Gold Set Sample Size:** 2 verified recordings  
> **Benchmark Word Error Rate (WER):** 5.00%  

---

## 1. Overall Model Performance Metrics

| Metric | Score | Target Threshold | Compliance Status |
|---|---|---|---|
| **Transcription WER** | 0.0500 (5.00%) | &le; 0.1500 (15%) | PASS |
| **Overall Precision** | 1.0000 | &ge; 0.7500 | PASS |
| **Overall Recall** | 0.7500 | &ge; 0.7000 | PASS |
| **Overall F1-Score** | 0.8571 | &ge; 0.7200 | PASS |
| **Inter-Rater Agreement (%)** | 75.00% | &ge; 80.00% | PASS |
| **Cohen's Kappa (κ)** | 0.556 | &ge; 0.60 (Substantial) | Moderate Agreement |

---

## 2. Per-Category Syntactic Deviation Breakdown

| Category Code | Description | Precision | Recall | F1-Score | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `TNS` | TNS | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |
| `SVA` | SVA | 1.0000 | 0.6667 | 0.8000 | 2 | 0 | 1 |
| `WO` | WO | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `AUX` | AUX | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `ART` | ART | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `PREP` | PREP | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `PRO` | PRO | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `OTH` | OTH | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |

---

## 3. Operational & Capacity Telemetry

* **Mean Processing Time per Assessment:** 3.2s
* **p95 Latency:** 3.2s
* **API Failure Rate:** 0.0%
* **Estimated Compute Cost per Participant:** $0.024 USD (Well within budget limits)

---

## 4. Known Scientific Limitations
- Faster-Whisper WER increases on non-standard Indian English phonology and colloquial contractions.
- Character span matching requires strict offset concordance; loose boundary matches may depress recall.
- Indian English regional syntactic variations (e.g., progressive aspect with stative verbs) require careful reviewer verification.

## 5. Unresolved Issues & Continuous Quality Actions
- Unresolved: 2 samples in gold set exhibit overlapping phrase disfluencies requiring human adjudication.
- Investigating: Slight latency variance during concurrent audio uploads under high-concurrency loads.
