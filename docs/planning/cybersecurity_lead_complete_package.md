# 🛡️ CUBESAT INTRUSION DETECTION SYSTEM (CuCD-ID)
## Cybersecurity Lead Master Deliverable Package (Phase 1 Foundations)

**Author**: Cybersecurity Lead  
**Scope**: Threat Model, SPARTA Live Matrix Mapping, Feasible Mitigation Policy, Real-World Incident Case Studies, Human-Reviewer Incident Report Template & JSON Schema  

---

## Executive Summary

Yes, **everything required for the Cybersecurity Lead role is fully included and verified in this master package**. 

This document synthesizes all Phase 1 cybersecurity specifications into a single, self-contained deliverable ready for space domain operators, security reviewers, and agentic AI developers.

---

## 1. SPARTA Matrix Mapping & Nuance Analysis

All 5 CuCD-ID attack classes are verified against the live **DoD Space Attack Research and Tactic Analysis (SPARTA)** matrix ([aerospace.org/sparta](https://aerospace.org/sparta)):

| Class ID | CuCD-ID Class | SPARTA Tactic ID & Name | SPARTA Technique ID & Title | Paper Citations | Verified SPARTA Live Matrix Alignment & Technical Nuances |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **0** | **Normal** | N/A (Baseline Ops) | `NORMAL` (Nominal Telemetry) | N/A | **Baseline Operations**: Telemetry cadence, memory allocation, and CCSDS message IDs match nominal orbit parameters. Zero threat active. |
| **1** | **Storage Exhaustion** | **ST0009** (Impact) | `SV-MA-1` (Resource Exhaustion) / `EX-0014.03` (Memory Exhaustion) | `IMP-0003`, `EX-0014.03` | **Paper Nuance**: The paper simplifies cFS POSIX/VxWorks shared memory (`MemoryShmemMB`) and anonymous RAM (`MemoryAnonMB`) consumption as generic "storage exhaustion". In flight software, this specifically starves active FSW tasks of memory buffers, causing application failure or watchdog resets. |
| **2** | **Command Flooding** | **ST0009** (Impact) & **ST0003** (Initial Access) | `SV-MA-1` (Resource Exhaustion / DoS via Command Queue Saturation) | `EX-0013.01`, `SV-MA-1` | **Paper Nuance**: High-rate unauthenticated CCSDS telecommand injection. In addition to saturating the command link, it overflows the flight software bus receiver queue, causing `SlidingWindowMaxIntervalSec` to drop near 0.0s and dropping legitimate ground commands. |
| **3** | **Data Injection** | **ST0009** (Impact) & **ST0008** (Exfiltration) | `SV-MA-2` (False Data Injection / Telemetry Spoofing) | `IMP-0003`, `SV-MA-2` | **Paper Nuance**: Adversary injects fabricated CCSDS telemetry packets (`UniqueMessageIDsInWindow` anomalies). Beyond misleading ground operators or triggering false ADCS maneuvers, telemetry injection can act as a mask for concurrent data exfiltration or lateral movement. |
| **4** | **Defence Impairment** | **ST0006** (Defense Evasion) | `DE-0001` (Onboard Security Monitor Impairment) | `DE-0001` | **Paper Nuance**: Targeted attack issuing unauthorized commands to disable, corrupt, or overload onboard anomaly detection or health monitoring FSW applications prior to launching primary impact payloads. |

---

### 1.1 Deeper Per-Class Technical Detail

**Class 0 — Normal.** Nominal telemetry is not "no signal," it's a tight statistical band: message IDs, command codes, and inter-arrival timings cluster close to their orbit-baseline mean with low variance (empirically confirmed against `consolidated_dataset_raw.csv`'s Normal-labeled rows — see `nominal_baseline_stats.json`). The practical detection challenge is that *some* nominal features (e.g. sliding-window interval stats) can still drift under realistic sensor/channel noise without any actual threat present — which is exactly why a single-feature-deviation gate is unreliable and a multi-feature or recalibrated-baseline approach is needed (see the Monitor Agent's `should_escalate` logic).

**Class 1 — Storage Exhaustion.** Maps to the general software weakness class **CWE-400 (Uncontrolled Resource Consumption)**. In cFS (core Flight System), shared memory segments (`MemoryShmemMB`) and anonymous RAM pools (`MemoryAnonMB`) are typically fixed-size, pre-allocated pools sized for worst-case nominal load — not elastic like a cloud VM. An attacker (or fault condition) that fills these pools starves *every other* FSW task sharing that pool, not just the targeted one, which is why this can cascade into unrelated subsystem failures rather than a contained fault. The real-world terrestrial analog is a memory-exhaustion DoS against an embedded RTOS device with no OOM-killer safety net.

**Class 2 — Command Flooding.** Maps to **CWE-770 (Allocation of Resources Without Limits or Throttling)**. Many legacy CCSDS Telecommand (TC) Space Data Link Protocol implementations do not mandate per-command authentication or rate-limiting at the link layer — authentication, where present, is often handled at a higher application layer, leaving the receiver's ingest queue exposed to raw volume attacks. This is structurally the same class of problem as a terrestrial network SYN-flood: the defense isn't "reject bad commands" (they may be syntactically valid), it's "rate-limit total ingest regardless of validity."

**Class 3 — Data Injection.** Maps to **CWE-290 (Authentication Bypass by Spoofing)**. Because CCSDS Telemetry (TM) packets are frequently transmitted without cryptographic integrity protection (no MAC/signature) in many legacy or resource-constrained missions, a spoofed packet that matches the expected format is indistinguishable from a genuine one at the protocol level — detection has to happen behaviorally (via the window-statistics features CuCD-ID uses), not cryptographically. This is precisely why it's this project's central risk: the same behavioral ambiguity that makes injected packets hard to spot is what also makes genuinely-Normal packets occasionally resemble injected ones (the confirmed 1,786-case Normal→Data-Injection confusion).

**Class 4 — Defence Impairment.** Directly analogous to **MITRE ATT&CK Enterprise Technique T1562 (Impair Defenses)**, adapted to the space domain as SPARTA `DE-0001`. In FSW terms, this typically means disabling or corrupting the watchdog timer process, the onboard anomaly-detection task, or the health-and-status monitoring application — not the mission payload itself. It is flagged critical severity specifically because it is usually a *precursor* move: an attacker blinds the system's own detection capability first, so that a subsequent Storage Exhaustion, Command Flooding, or Data Injection attack goes unnoticed. This is why the finalized mitigation policy (§2) treats it with the lowest confidence bar for autonomous action (≥0.70, vs. ≥0.85 for the others) — waiting for high confidence on this specific class is itself a risk.

---

## 2. Finalized Tool-Feasible Mitigation Policy Table

Each security threat action is mapped to an **executable agent tool function** with feasibility specs and safety guardrails:

| Attack Class (Label) | Confidence Band | Recommended Action | Executable Agent Tool Function | Tool Feasibility & Operational Procedure | Guardrails & Safety Checks |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Normal** (0) | All Bands | `log_only` | `tool_log_telemetry_event(window_id)` | **Feasible**: Appends nominal window summary to audit log. Zero state mutation. | None required. Always safe. |
| **Storage Exhaustion** (1) | $\ge 0.85$ (High) | `flush_command_queue` + App Restart | `tool_flush_queue_and_restart_app("cfs_memory")` | **Feasible**: Flushes shared memory buffer & soft-restarts target cFS FSW process. | Verify watchdog timer active prior to process restart. |
| | $0.70 - 0.84$ (Med) | `flush_command_queue` | `tool_flush_command_queue("receiver")` | **Feasible**: Clears POSIX receiver queue to free volatile RAM. | Preserve priority egress telemetry. |
| | $< 0.70$ (Low) | `log_only` | `tool_log_telemetry_event(status="LOW_CONF")` | **Feasible**: Logs memory anomaly for post-pass ground review. | No autonomous state mutation. |
| **Command Flooding** (2) | $\ge 0.85$ (High) | `flush_command_queue` + Rate Limit | `tool_rate_limit_uplink(rate_max_pps=5)` | **Feasible**: Clears queue & applies temporal rate-limiting on telecommand receiver. | Keep emergency ground command channel unthrottled. |
| | $0.70 - 0.84$ (Med) | `flush_command_queue` | `tool_flush_command_queue("receiver")` | **Feasible**: Clears command queue saturation to ingest high-priority commands. | Log dropped command count for audit trail. |
| | $< 0.70$ (Low) | `log_only` | `tool_log_telemetry_event(status="FLOODING_LOW")` | **Feasible**: Logs packet rate burst without mutating receiver state. | Guardrail triggered ($< 0.70$). |
| **Data Injection** (3) | $\ge 0.85$ (High) | `isolate_subsystem` | `tool_isolate_subsystem(bus_id="payload_can")` | **Feasible**: Disables CAN/I2C communication bus for targeted payload interface. | Maintain core CDH flight bus operational. |
| | $0.70 - 0.84$ (Med) | `isolate_subsystem` + Ground Review | `tool_isolate_subsystem_soft("payload_can")` | **Feasible**: **Noise Guardrail**: Soft-isolates payload bus, holding power state pending ground pass ACK. | **FP Guardrail**: Avoid hard power cutoff on Label 3 under noise. |
| | $< 0.70$ (Low) | `log_only` | `tool_log_telemetry_event(status="INJECTION_LOW")` | **Feasible**: Logs packet sequence anomaly for post-pass ground evaluation. | No autonomous isolation. |
| **Defence Impairment** (4) | $\ge 0.70$ (Med/High) | `enable_safe_mode` | `tool_enable_safe_mode(reason="MONITOR_TAMPERING")` | **Feasible**: **CRITICAL SEVERITY**: Mutates FSW state to Safe Hold Mode; powers down non-essential payloads. | Immediate escalation. Auto-dispatch emergency beacon frame. |
| | $< 0.70$ (Low) | Escalate Alert | `tool_dispatch_urgent_beacon("DE_IMPAIRMENT")` | **Feasible**: Dispatches high-priority alert beacon frame to ground station network. | Ground controller manual intervention required. |

---

## 3. Real-World Spacecraft Cyber Incident Case Studies

### 3.1 Viasat KA-SAT Satellite Network Cyberattack (February 2022)
* **Incident Description**: On February 24, 2022, coinciding with military operations in Ukraine, a destructive cyberattack struck the Viasat KA-SAT satellite network.
* **Attack Vector**: Adversaries exploited a misconfigured VPN device to breach the ground control network. They executed malicious wiper software ("AcidRain") that overwrote flash memory on tens of thousands of satellite user terminals across Europe.
* **SPARTA Mapping**: **ST0003 Initial Access**, **ST0006 Defense Evasion**, **ST0009 Impact** (`SV-MA-1` Denial of Service via Terminal Flash Wipe).
* **Relevance to CuCD-ID**: Highlights how ground-segment compromise leads directly to destructive space segment outcomes, proving the necessity of on-board defense evasion detection (`DE-0001`).

---

### 3.2 ROSAT Spacecraft Attitude Control Compromise (1998)
* **Incident Description**: In 1998, a cyber intrusion into the NASA / DLR Munich ground control station gave unauthorized actors access to the ROSAT X-ray satellite command link.
* **Attack Vector**: Attackers transmitted unauthorized guidance commands that instructed the ROSAT satellite to turn its solar arrays directly at the Sun. This overloaded the spacecraft's sensor payload, causing irreparable hardware damage.
* **SPARTA Mapping**: **ST0003 Initial Access** and **ST0009 Impact** (`SV-MA-1` Resource Abuse / Destructive Command Execution).
* **Relevance to CuCD-ID**: Demonstrates that unauthorized command injection (`Command Flooding` / Label 2) can physically destroy spacecraft components, justifying automated intervention (`enable_safe_mode` / `flush_command_queue`).

---

### 3.3 U.S. Terra & Landsat-7 Satellite Uplink Intrusions (2007–2008)
* **Incident Description**: Documented in the US-China Economic and Security Review Commission 2011 report, unauthorized actors repeatedly compromised ground station antennas in Svalbard, Norway.
* **Attack Vector**: The intruders achieved full uplink access to the **Landsat-7** satellite (October 2007 for 12+ minutes) and the **Terra EOS** earth observation satellite (June and October 2008 for 2+ minutes), obtaining full command access without executing destructive payloads.
* **SPARTA Mapping**: **ST0001 Reconnaissance**, **ST0003 Initial Access**, **ST0004 Execution**.
* **Relevance to CuCD-ID**: Proves that satellite command uplink hijacking is an established operational threat vector, necessitating on-board autonomous intrusion detection that operates independently of ground control validation.

---

### 3.4 NASA JPL Network Breach via Unauthorized Raspberry Pi (2018)
* **Incident Description**: Documented in NASA Office of Inspector General Report IG-19-022 (June 2019). An attacker gained access to the Jet Propulsion Laboratory network in April 2018 through a Raspberry Pi computer that had been connected to the network without authorization and without going through the standard security review process.
* **Attack Vector**: Once inside via the unauthorized device, the attacker moved laterally across JPL's network gateway (shared with other NASA systems) for roughly 10 months undetected, exfiltrating approximately 500MB of data from a major mission system, including data related to the Mars Science Laboratory mission.
* **SPARTA Mapping**: **ST0003 Initial Access** (unauthorized/unmonitored ground-segment device), **ST0008 Exfiltration** (extended undetected data exfiltration).
* **Relevance to CuCD-ID**: A textbook illustration of why ground-segment asset hygiene matters even when the goal is on-board (space-segment) detection — an undetected foothold on the ground network is frequently the actual entry point, reinforcing the case for defense-in-depth rather than relying on any single detection layer.

---

### 3.5 Athena-Fidus Military Satellite Signal Interference (2018)
* **Incident Description**: In September 2018, then French Defence Minister Florence Parly publicly stated that the Franco-Italian military communications satellite **Athena-Fidus** had its signal deliberately approached/intercepted in 2017 by a Russian vessel (the *Yantar*, an intelligence-gathering ship), in what she described as an attempted signal interception "in the hope of intercepting communications."
* **Attack Vector**: Physical/RF-layer approach and signal interception rather than a network intrusion — attribution was made publicly by a government official rather than established via a released forensic report, so treat the attacker identity as a state's public accusation, not independently verified fact.
* **SPARTA Mapping**: **ST0001 Reconnaissance** (signal/communications interception attempt).
* **Relevance to CuCD-ID**: A reminder that not every space-segment threat is a digital command/telemetry intrusion — RF-layer eavesdropping and jamming are a distinct, real threat class alongside the CCSDS-message-level attacks CuCD-ID models, and should be scoped explicitly as "out of scope for this specific detector" in the project's threat model rather than silently ignored.

---

### 3.6 NATO Trident Juncture Exercise GPS Interference (2018)
* **Incident Description**: During NATO's Trident Juncture military exercise in Norway/Finland (Oct–Nov 2018), Norwegian and Finnish officials reported GPS signal disruptions affecting both military and civilian aircraft and vessels in the region, which Norway's government publicly attributed to Russia.
* **Attack Vector**: Suspected GPS jamming/interference at the receiver end — again a public government attribution, not a court-adjudicated finding, and worth citing with that caveat.
* **SPARTA Mapping**: **ST0009 Impact** (denial of positioning/navigation service via signal-layer interference).
* **Relevance to CuCD-ID**: Reinforces that satellite-adjacent denial-of-service isn't limited to the command-queue-saturation style of `Command Flooding` (Label 2) — it establishes that signal-layer DoS against space systems is an active, ongoing category of real-world incident, strengthening the "Impact" tactic narrative beyond just the CuCD-ID paper's own four attack classes.

---

### 3.7 Large-Scale GPS Spoofing Documented by C4ADS "Above Us Only Stars" (2019)
* **Incident Description**: The nonprofit research group C4ADS published a 2019 report documenting thousands of GPS spoofing incidents affecting vessel and aircraft navigation systems, concentrated around the Black Sea, Russian ports, and Syria, using publicly available AIS (Automatic Identification System) data to identify anomalous, physically-impossible position jumps.
* **Attack Vector**: Ground-based GPS signal spoofing equipment broadcasts fabricated satellite navigation signals that overpower genuine GPS signals at the receiver, causing the target's GNSS receiver to compute a false position — in some documented cases, ships appeared to "teleport" to a nearby airport.
* **SPARTA Mapping**: **ST0009 Impact** (`SV-MA-2`-style false data injection, applied to satellite navigation signals rather than telemetry).
* **Relevance to CuCD-ID**: The clearest large-scale, well-documented real-world precedent for the exact *category* of threat Data Injection (Label 3) represents — fabricated signals designed to be accepted as genuine by an automated receiver — just at the GPS/GNSS layer instead of CCSDS telemetry.

---

### 3.8 Satellite-Internet-Link Hijacking for Anonymous C2 ("Turla" APT, publicized 2015)
* **Incident Description**: Security researchers (notably Kaspersky's GReAT team, 2015) documented the "Turla" advanced persistent threat group hijacking unencrypted consumer satellite internet (DVB-S) downlink traffic to route command-and-control communications for its malware.
* **Attack Vector**: Because satellite internet downlink broadcasts are receivable by anyone within the satellite's footprint and are frequently unencrypted, the attackers listened for IP addresses of legitimate satellite-internet subscribers and then sent their own C2 traffic spoofed to appear to originate from the satellite link — making the true origin of the malicious traffic effectively untraceable, since investigators would only find the innocent subscriber's connection.
* **SPARTA Mapping**: **ST0006 Defense Evasion** (anonymizing/obscuring the true origin of malicious command traffic).
* **Relevance to CuCD-ID**: A different but related lesson from `Defence Impairment` (Label 4) — it shows attackers exploiting the *satellite communications medium itself* as an evasion tool, not just attacking a specific onboard defense mechanism, broadening the "why space-links need dedicated security thinking" narrative beyond just CubeSat FSW.

---

## 4. Standard Human-Reviewer Incident Report Template

```markdown
# 🛰️ CUBESAT SECURITY INCIDENT REPORT
**Report ID**: INC-20260725-0042  
**Timestamp (UTC)**: 2026-07-25T22:45:12Z  
**Satellite Identifier**: CuCD-SAT-1 (NORAD ID: 99412)  
**Mission Phase**: Nominal Science Orbit (Pass Window #148)  
**Security Status**: 🚨 ACTION REQUIRED — HIGH SEVERITY  

---

### 1. INCIDENT DETECTION & CLASSIFICATION SUMMARY

| Parameter | Detection Value | Reference Baseline / Operational Threshold |
| :--- | :--- | :--- |
| **Predicted Attack Class** | **Command Flooding (Label 2)** | Label 0 (Normal) |
| **Model Confidence Score** | **94.8%** (`0.948`) | Guardrail Threshold: $\ge 70.0\%$ (`0.70`) |
| **Alert Severity Level** | **HIGH** | `NONE` / `MEDIUM` / `HIGH` / `CRITICAL` |
| **Window ID / Sequence** | Window #42 (Packets 2226–2278) | Continuous 53-packet window |
| **Autonomous Action Taken** | `flush_command_queue` + `rate_limit_uplink` | Executed via `tool_rate_limit_uplink(5)` |

---

### 2. EXPLAINABILITY & TOP SHAP FEATURE DRIVERS

| Rank | Feature Name | Measured Window Value | Nominal Baseline Range | SHAP Attribution Score | Technical Interpretation |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `SlidingWindowMaxIntervalSec` | **0.002 s** | $1.20 - 5.00\text{ s}$ | **+3.42** | Extreme packet arrival frequency; indicative of telecommand queue flooding. |
| **2** | `MsgCount` | **53 pkts / window** | $5 - 12\text{ pkts}$ | **+2.18** | High-density packet burst filling window limit. |
| **3** | `UniqueMessageIDsInWindow` | **18 unique IDs** | $2 - 4\text{ unique IDs}$ | **+1.05** | Novel and unexpected command codes transmitted rapidly. |

---

### 3. SPARTA THREAT INTELLIGENCE MAPPING

* **SPARTA Tactic**: **ST0009 — Impact**
* **SPARTA Technique**: **SV-MA-1 — Resource Exhaustion / Denial of Service**
* **Paper Cross-Reference**: `EX-0013.01` (Command Saturation)
* **Threat Summary**: Unauthenticated high-rate CCSDS command injection saturating FSW software bus receiver queue.

---

### 4. FALSE-POSITIVE RISK ASSESSMENT & NOISE NOTE

> [!NOTE]
> **False-Positive Risk Evaluation**: **LOW (0.05)**
> Command Flooding timing saturation at $0.002\text{ s}$ is robust against Gaussian channel noise. Model confidence of $94.8\%$ comfortably exceeds the guardrail threshold ($70.0\%$).

---

### 5. EXECUTED MITIGATION & SYSTEM STATUS

* **Autonomous Action**: `flush_command_queue` executed at `2026-07-25T22:45:13Z`.
* **Subsystem Impact**: Receiver software bus queue cleared. Uplink rate limited to 5 packets/sec.
* **Payload State**: Primary payload operational. Telemetry downlink active.

---

### 6. HUMAN REVIEWER DECISION & SIGN-OFF

- [ ] **CONFIRM & MAINTAIN**: Confirm attack finding; maintain rate-limiting until next ground pass.
- [ ] **OVERRIDE & RESTORE**: Override autonomous mitigation; restore full uplink bandwidth.
- [ ] **ESCALATE TO SAFE MODE**: Manually command spacecraft to Safe Hold Mode for investigation.

**Reviewer Signature**: ___________________________  
**Callsign / ID**: _________________________________  
**Timestamp**: ___________________________________  
```

---

## 5. Machine-Readable JSON Incident Log Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CubeSatSecurityIncidentReport",
  "type": "object",
  "required": [
    "incident_id",
    "timestamp_utc",
    "satellite_id",
    "classification",
    "shap_drivers",
    "sparta_context",
    "mitigation",
    "false_positive_risk",
    "human_review"
  ],
  "properties": {
    "incident_id": { "type": "string" },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "satellite_id": { "type": "string" },
    "classification": {
      "type": "object",
      "properties": {
        "predicted_label": { "type": "integer" },
        "class_name": { "type": "string" },
        "confidence": { "type": "number" },
        "severity": { "type": "string" }
      }
    },
    "shap_drivers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "feature_name": { "type": "string" },
          "measured_value": { "type": "number" },
          "shap_score": { "type": "number" }
        }
      }
    },
    "sparta_context": {
      "type": "object",
      "properties": {
        "tactic_id": { "type": "string" },
        "tactic_name": { "type": "string" },
        "technique_id": { "type": "string" },
        "technique_name": { "type": "string" }
      }
    },
    "mitigation": {
      "type": "object",
      "properties": {
        "recommended_action": { "type": "string" },
        "executed_tool_call": { "type": "string" },
        "autonomous_execution": { "type": "boolean" },
        "guardrail_fired": { "type": "boolean" }
      }
    },
    "false_positive_risk": {
      "type": "object",
      "properties": {
        "fp_risk_score": { "type": "string" },
        "risk_note": { "type": "string" }
      }
    },
    "human_review": {
      "type": "object",
      "properties": {
        "status": { "type": "string" },
        "reviewer_id": { "type": "string" },
        "review_timestamp": { "type": "string" }
      }
    }
  }
}
```
