# SentinelSat IDS — Failure Mode Root Cause & Phase 5 Adversarial Test Plan
**Author:** Systems/Simulation Lead (Role C)
**Audience:** ML Lead, team review
**Status:** Draft — hypotheses to validate against actual feature-importance / SHAP output

---

## 1. Failure Mode A: Normal → DataInjection (1,786 cases)

### 1.1 What's actually happening
The model is treating **statistical irregularity** as a proxy for **malicious injection**, rather than distinguishing *why* telemetry looks irregular. Any legitimate operational state that produces bursty, high-entropy, or timing-irregular telemetry will sit in the same feature-space neighborhood as an injected payload.

### 1.2 Root-cause hypotheses (rank by likelihood, confirm with ML Lead)

| # | Hypothesis | Why it produces this exact confusion | How to confirm |
|---|---|---|---|
| 1 | **Rate/entropy features dominate over semantic/content features.** If the model leans heavily on packet-rate variance, payload entropy, or inter-arrival jitter, it can't tell "ADCS in detumble mode dumping high-frequency gyro data" from "attacker injecting synthetic telemetry." | Both produce elevated entropy + burst rate relative to steady-state baseline. | Pull top-15 SHAP features for the 1,786 misclassified rows — if rate/entropy features dominate over subsystem-ID or opcode-diversity features, this is confirmed. |
| 2 | **Training data under-represents legitimate high-activity operational modes** (ground pass downlink dumps, ADCS maneuvers, payload science bursts, safe-mode transitions). NOS3/cFS sims often generate "Normal" mostly as steady-state housekeeping telemetry, so the model never learns that Normal has a *wide* dynamic range. | Class imbalance within "Normal" itself — steady-state overrepresented vs. legitimate-but-rare bursty Normal. | Check per-subsystem / per-mode label distribution inside the Normal class. If >90% of Normal samples are steady-state housekeeping, this is the primary driver. |
| 3 | **Window boundary artifacts.** If windowing is fixed-size and non-overlapping, a window that captures the *onset* of a legitimate burst (e.g., first 2s of a ground-pass downlink) looks anomalous by any within-window baseline comparison, before enough context accumulates to normalize it. | Onset transients look identical regardless of cause. | Check whether misclassified windows cluster near known legitimate-mode transition timestamps in the scenario logs. |
| 4 | **Checksum/CRC noise treated as injection signal.** cFS telemetry over noisy sim links can produce legitimate bit errors that superficially resemble malformed/injected packets if the feature set includes checksum-fail rate. | Same low-level signal, two different causes (RF noise vs. attacker tampering). | Check if misclassified windows correlate with simulated link-noise parameters in NOS3 config, not with any injected-payload flag. |

### 1.3 What an attacker would need to produce to land here (evasion angle)
This confusion is a **detection gap an attacker can exploit deliberately**, not just an accident:
- Inject data during a window that *coincides with* a legitimate high-activity mode (ground pass, maneuver) — the injection is masked by expected irregularity. This is the dangerous direction: attacker timing injection to legitimate telemetry bursts specifically to blend in.
- Keep injected payload entropy and packet rate within the statistical envelope of legitimate bursty Normal — i.e., mimicry rather than brute-force flooding.
- Avoid tripping content-level tells (duplicate sequence numbers, opcode outside expected range for that subsystem) if those aren't weighted features — confirms hypothesis 1 if this evasion works in simulation.

### 1.4 What an "unlucky" noise pattern looks like (non-adversarial angle)
- A benign but statistically rare combination: simultaneous ADCS maneuver + ground-pass downlink + minor link noise, producing a Normal window that's an outlier along every axis the model uses, with no malicious intent at all.
- This is the scenario that actually matters most for false-positive rate in deployment — an operator will lose trust in the IDS fast if routine ops trigger alerts.

---

## 2. Failure Mode B: CmdFlood ↔ DataInjection mutual confusion (1,254 + 451 cases)

### 2.1 What's actually happening
Two attack classes that differ in **intent and direction** (commands sent *to* the satellite vs. data injected *into* telemetry) are colliding because the feature set likely encodes them as **volume + repetition**, which both classes share.

### 2.2 Root-cause hypotheses

| # | Hypothesis | Why it causes bidirectional confusion | How to confirm |
|---|---|---|---|
| 1 | **Directionality isn't a strong feature.** If uplink command volume and downlink telemetry volume aren't cleanly separated (or get aggregated into a combined "packet rate" feature), a burst of either looks like a burst of "something." | This explains why confusion goes both ways — CmdFlood→DataInj (1,254) and DataInj→CmdFlood (451) — a shared rate feature doesn't care which direction the burst is in. | Check whether uplink/downlink channel is an explicit categorical feature or gets collapsed pre-training. |
| 2 | **Low opcode/content diversity is shared between the two attack types.** CmdFlood = repeated command opcodes at high rate. DataInjection, if implemented in your sim as repeated/replayed telemetry frames, also has low content diversity at high rate. The model may just be learning "low diversity + high rate = attack class X or Y" without a clean separating feature. | Both attacks are "spam" at the feature level even though their payload semantics differ. | Compare content-diversity distributions (unique opcode count, unique payload hash count) between the two classes in training data — if they overlap heavily, this is confirmed. |
| 3 | **Asymmetric class sizes causing biased decision boundary.** The 1,254 vs. 451 split (not symmetric) suggests the model defaults toward CmdFlood more often when uncertain — check if CmdFlood is the majority class of the two, which would bias ambiguous cases toward it via prior probability. | Explains why the confusion isn't 50/50. | Compare raw class counts for CmdFlood vs. DataInjection in training set. |
| 4 | **Combined attacks in ground truth.** If any scenario scripts *actually* combine command flooding with data injection (a plausible real attacker move — flood commands to overload the bus while injecting false telemetry to mask state), some "confusion" may be the model correctly detecting a blended attack that only has one ground-truth label. | Explains persistent, non-improvable confusion no matter how features are tuned. | Audit scenario scripts for co-occurring CmdFlood + DataInjection windows with single-class labels. |

### 2.3 What an attacker would need to produce to trigger this deliberately
- Launch a data-injection attack disguised as command traffic volume (or vice versa) specifically to land in the ambiguous decision region between the two classes, betting the SOC/IDS response playbook for CmdFlood is less aggressive (e.g., rate-limiting) than for DataInjection (e.g., full quarantine) — attacker picks whichever misclassification produces the weaker response.
- Pace the attack just under whatever rate threshold cleanly separates the classes in training data, so it sits in the ambiguous band by construction.

### 2.4 What an unlucky pattern looks like
- A single stuck/looping ground station script that legitimately retransmits the same command repeatedly due to a bug (not malice) — this would plausibly land in the same ambiguous zone as CmdFlood, and cross-contaminate into DataInjection if retransmitted telemetry ACKs are also repetitive.

---

## 3. Phase 5 Adversarial Test Scenario Plan

Structuring this so each scenario maps directly onto a root-cause hypothesis above — the point isn't just "generate edge cases," it's generate edge cases that isolate *which* hypothesis is true.

### 3.1 Scenario Set 1 — Normal/DataInjection boundary probes
| ID | Scenario | Targets hypothesis | Simulator config sketch |
|---|---|---|---|
| N-DI-01 | Legitimate ground-pass downlink burst, no injection, at 3 rate levels (baseline / 2x / 4x steady-state) | A-1, A-2 | Scripted-run: mode flag `ground_pass=True`, sweep `telemetry_rate_multiplier` |
| N-DI-02 | ADCS detumble maneuver telemetry burst, no injection | A-1, A-2 | Scripted-run: mode flag `adcs_maneuver=True` |
| N-DI-03 | Injection timed to coincide with N-DI-01/02 burst windows (attacker mimicry) | A-1 (evasion) | Overlay injection payload generator onto ground_pass/maneuver windows |
| N-DI-04 | Window-boundary onset capture — inject at t=0 of a fixed window vs. t=mid-window vs. t=late-window | A-3 | Stream mode with injection start-offset parameter |
| N-DI-05 | Elevated link-noise / CRC-fail rate, no injection, no burst | A-4 | Scripted-run: `link_noise_pct` sweep, isolate from other flags |
| N-DI-06 | Injected payload with entropy/rate matched to legitimate-burst statistical envelope (near-boundary mimicry) vs. injected payload at obviously anomalous rate (far-boundary control) | A-1, A-3 (evasion) | Two-arm test: `injection_profile=mimicry` vs `injection_profile=naive` |

### 3.2 Scenario Set 2 — CmdFlood/DataInjection boundary probes
| ID | Scenario | Targets hypothesis | Simulator config sketch |
|---|---|---|---|
| CF-DI-01 | Pure CmdFlood at varying opcode diversity (all-same-opcode vs. mixed-opcode flood) | B-2 | Scripted-run: `cmd_opcode_diversity` param |
| CF-DI-02 | Pure DataInjection at varying content diversity (replayed identical frames vs. varied synthetic frames) | B-2 | Scripted-run: `injection_content_diversity` param |
| CF-DI-03 | Rate-matched CmdFlood vs. DataInjection pair — same packet/sec, opposite direction, to isolate whether directionality is actually load-bearing in the model | B-1 | Paired scenario, uplink-only vs downlink-only at matched rate |
| CF-DI-04 | Combined CmdFlood + DataInjection (co-occurring, single dominant label) — tests whether "confusion" is actually correct blended-attack detection | B-4 | Scripted-run: both flags active simultaneously, log true blended ground truth separately from the single training label |
| CF-DI-05 | Benign stuck-script retransmission loop (legit command repeated due to simulated ground-station bug, no malicious intent) | B (unlucky-noise case) | Scripted-run: `benign_retransmit_loop=True` |
| CF-DI-06 | Near-threshold pacing sweep — attack rate stepped in small increments across whatever rate boundary currently separates the two classes in training data | B-3, B-1 | Fine-grained `attack_rate` sweep with small step size around known decision boundary (pull from ML Lead's threshold analysis) |

### 3.3 Scenario Set 3 — Cross-cutting: ambiguous windows & rapid switching
These stress the temporal/windowing logic directly rather than any single class boundary.

| ID | Scenario | Purpose |
|---|---|---|
| RX-01 | **Straddle windows** — attack transitions mid-window (Normal→DataInjection, CmdFlood→DataInjection, DataInjection→CmdFlood) at multiple offset points within the window (10%, 50%, 90% through) | Determine whether the model/windowing strategy has any graceful handling of mixed-label windows, or whether it always collapses to one class — informs whether smaller windows or overlapping windows are needed |
| RX-02 | **Rapid scenario switching** — alternate CmdFlood ↔ DataInjection ↔ Normal at increasingly short dwell times (30s, 10s, 3s, 1s per state) | Finds the minimum dwell time at which the model's temporal features (if any) break down; also stress-tests whether rapid switching itself becomes a novel unlabeled pattern the model mishandles |
| RX-03 | **Decoy-then-pivot** — sustained CmdFlood to consume analyst/SOC attention, then a short DataInjection burst embedded inside the tail of the flood | Realistic attacker tradecraft test — flood as cover for injection; checks whether the model's confusion here has operational consequences (does the injection get "hidden" in a CmdFlood-labeled window?) |
| RX-04 | **Silent gaps** — attack pauses briefly (simulating an attacker evading rate-based detection windows) between bursts of consistent short duration | Tests whether windowing has blind spots between windows that an attacker could time against |
| RX-05 | **Multi-class noise floor** — long baseline run mixing all legitimate operational modes (ground pass, maneuver, safe mode, science ops) with zero attacks, to establish the real false-positive rate under full operational diversity rather than the training set's likely narrower Normal distribution | Directly tests Failure Mode A hypothesis 2 (Normal under-representation) at scale |

### 3.4 Suggested build order
1. **N-DI-05 and CF-DI-01/02** first — cheapest to generate, isolate single-variable hypotheses (noise, diversity) without needing mimicry logic.
2. **RX-05** next — establishes a proper operational-diversity baseline, which the ML Lead will want before evaluating anything else.
3. **N-DI-01/02/03, CF-DI-03/06** — the mimicry/boundary-matching scenarios; these need the most careful parameterization since they're testing the actual decision boundary.
4. **RX-01/02** — windowing stress tests, informs whether the windowing strategy itself needs to change before further model tuning is even worthwhile.
5. **CF-DI-04, RX-03, RX-04** — realistic attacker tradecraft scenarios, best done last once the simpler isolations have narrowed down which hypotheses are actually true.

---

## 4. Immediate next step for ML Lead sync
Before building all of these, the fastest confirm/deny move is pulling SHAP or feature-importance values for a sample of the 1,786 and 1,254+451 misclassified rows — that alone should confirm or rule out hypotheses A-1/A-2 and B-1/B-2 without needing new simulator runs, and will tell us which scenario sets in 3.1–3.2 are worth prioritizing.
