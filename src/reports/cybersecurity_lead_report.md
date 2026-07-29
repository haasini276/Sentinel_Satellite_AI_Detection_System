# 🛡️ Cybersecurity Lead Deliverable — Phase 1: Threat Model & Architecture
**Project**: CuCD-ID Spacecraft Intrusion Detection System  
**Author**: Cybersecurity Lead  

---

## Executive Summary

This document fulfills all **Cybersecurity Lead** requirements for **Phase 1 (Jul 15 – Jul 21)**. It provides:
1. Full mapping of all **5 CuCD-ID dataset attack classes** (including Normal) to the live **DoD SPARTA Matrix** ([aerospace.org/sparta](https://aerospace.org/sparta)) with paper citations, technique IDs, and technical nuances.
2. The complete **Initial Mitigation Policy Table** detailing autonomous actions across confidence bands.
3. Analysis of **3 real-world spacecraft cyber incident case studies** to ground the project threat model in operational space security history.

---

## 1. SPARTA Matrix Mapping & Nuance Analysis

The **CuCD-ID paper** (*Data in Brief*, Feb 2026) models telemetry anomalies from NASA core Flight System (cFS) satellite software. Below is the mapping against the live **Space Attack Research and Tactic Analysis (SPARTA)** matrix:

| Class ID | CuCD-ID Class | SPARTA Tactic ID & Name | SPARTA Technique ID & Name | Paper Citations | Verified SPARTA Live Matrix Alignment & Technical Nuances |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **0** | **Normal** | N/A (Baseline Ops) | `NORMAL` (Nominal Telemetry) | N/A | **Baseline Operations**: Satellite housekeeping telemetry cadence, memory allocation, and message IDs follow expected orbital profiles. No active threat. |
| **1** | **Storage Exhaustion** | **ST0009** (Impact) | `SV-MA-1` (Resource Exhaustion) / `EX-0014.03` (Memory Exhaustion) | `IMP-0003`, `EX-0014.03` | **Paper Nuance**: The paper simplifies cFS POSIX/VxWorks shared memory (`MemoryShmemMB`) and anonymous RAM (`MemoryAnonMB`) consumption as generic "storage exhaustion". In live flight software, this specifically starves active FSW tasks of memory buffers, causing application failure or watchdog resets. |
| **2** | **Command Flooding** | **ST0009** (Impact) & **ST0003** (Initial Access) | `SV-MA-1` (Resource Exhaustion / DoS via Command Queue Saturation) | `EX-0013.01`, `SV-MA-1` | **Paper Nuance**: High-rate unauthenticated CCSDS telecommand injection. In addition to saturating the command link, it overflows the flight software bus receiver queue, causing `SlidingWindowMaxIntervalSec` to drop near 0.0s and dropping legitimate ground commands. |
| **3** | **Data Injection** | **ST0009** (Impact) & **ST0008** (Exfiltration) | `SV-MA-2` (False Data Injection / Telemetry Spoofing) | `IMP-0003`, `SV-MA-2` | **Paper Nuance**: Adversary injects fabricated CCSDS telemetry packets (`UniqueMessageIDsInWindow` anomalies). Beyond misleading ground operators or triggering false ADCS maneuvers, telemetry injection can act as a mask for concurrent data exfiltration or lateral movement. |
| **4** | **Defence Impairment** | **ST0006** (Defense Evasion) | `DE-0001` (Onboard Security Monitor Impairment) | `DE-0001` | **Paper Nuance**: Targeted attack issuing unauthorized commands to disable, corrupt, or overload onboard anomaly detection or health monitoring FSW applications prior to launching primary impact payloads. |

---

## 2. Initial Mitigation Policy Table

The Mitigation Agent evaluates predicted attack labels against confidence guardrail bands (`CONFIDENCE_THRESHOLD = 0.70`) to select autonomous responses:

| Attack Class | Confidence Band | Mitigation Action | Autonomous Execution | Detailed Operational Procedure & Guardrail Rationale |
| :--- | :--- | :--- | :---: | :--- |
| **Normal (Label 0)** | All Bands | `log_only` | Yes | Continue nominal telemetry logging. No system mutation required. |
| **Storage Exhaustion (Label 1)** | $\ge 0.85$ (High) | `flush_command_queue` + App Restart | Yes | High confidence buffer exhaustion. Clear memory queues and soft-restart affected cFS app. |
| | $0.70 - 0.84$ (Med) | `flush_command_queue` | Yes | Medium confidence. Flush command receiver buffers to free volatile RAM. |
| | $< 0.70$ (Low) | `log_only` / Escalate | No | Below confidence threshold. Log telemetry anomaly and alert ground controllers. |
| **Command Flooding (Label 2)** | $\ge 0.85$ (High) | `flush_command_queue` + Rate Limit | Yes | Severe saturation. Flush FSW software bus queue and enforce rate-limiting on telecommand receiver. |
| | $0.70 - 0.84$ (Med) | `flush_command_queue` | Yes | Clear command queue to allow legitimate high-priority ground commands. |
| | $< 0.70$ (Low) | `log_only` / Escalate | No | Maintain current processing state; flag high packet rate in pass log. |
| **Data Injection (Label 3)** | $\ge 0.85$ (High) | `isolate_subsystem` | Yes | High confidence telemetry spoofing. Isolate payload telemetry bus. |
| | $0.70 - 0.84$ (Med) | `isolate_subsystem` + Ground Review | Yes | **Noise Guardrail**: Data Injection has high FP risk under channel noise. Isolate bus, await ground pass ACK. |
| | $< 0.70$ (Low) | `log_only` | No | Likely channel timing jitter. Log for post-pass ground review. |
| **Defence Impairment (Label 4)** | $\ge 0.70$ (Med/High) | `enable_safe_mode` | **Yes** | **CRITICAL SEVERITY**: Security monitor tampering detected. Immediately enter safe mode, power down non-essential payloads. |
| | $< 0.70$ (Low) | Escalate Urgent Alert | No | Dispatch high-priority emergency alert frame to ground station network. |

---

## 3. Real-World Spacecraft Cyber Incident Case Studies

To ground the CuCD-ID project threat model in operational space security history:

### 3.1 Viasat KA-SAT Satellite Network Cyberattack (February 2022)
* **Incident Description**: On February 24, 2022, coinciding with military operations in Ukraine, a destructive cyberattack struck the Viasat KA-SAT satellite network.
* **Attack Vector**: Adversaries exploited a misconfigured VPN device to breach the ground control network. They executed malicious wiper software ("AcidRain") that overwrote flash memory on tens of thousands of satellite user terminals across Europe.
* **SPARTA Mapping**:
  * **ST0003 Initial Access** (Ground Station Network Compromise)
  * **ST0006 Defense Evasion** (Disguised management commands)
  * **ST0009 Impact** (`SV-MA-1` Denial of Service via Terminal Flash Wipe)
* **Relevance to CuCD-ID**: Highlights how ground-segment compromise leads directly to destructive space segment outcomes, proving the necessity of on-board defense evasion detection (`DE-0001`).

---

### 3.2 ROSAT Spacecraft Attitude Control Compromise (1998)
* **Incident Description**: In 1998, a cyber intrusion into the NASA / DLR Munich ground control station gave unauthorized actors access to the ROSAT X-ray satellite command link.
* **Attack Vector**: Attackers transmitted unauthorized guidance commands that instructed the ROSAT satellite to turn its solar arrays directly at the Sun. This overloaded the spacecraft's sensor payload, causing irreparable hardware damage.
* **SPARTA Mapping**:
  * **ST0003 Initial Access** (Command Link Intrusions)
  * **ST0009 Impact** (`SV-MA-1` Resource Abuse / Destructive Command Execution)
* **Relevance to CuCD-ID**: Demonstrates that unauthorized command injection (`Command Flooding` / Label 2) can physically destroy spacecraft components, justifying automated intervention (`enable_safe_mode` / `flush_command_queue`).

---

### 3.3 U.S. Terra & Landsat-7 Satellite Uplink Intrusions (2007–2008)
* **Incident Description**: Documented in the US-China Economic and Security Review Commission 2011 report, unauthorized actors repeatedly compromised ground station antennas in Svalbard, Norway.
* **Attack Vector**: The intruders achieved full uplink access to the **Landsat-7** satellite (October 2007 for 12+ minutes) and the **Terra EOS** earth observation satellite (June and October 2008 for 2+ minutes), obtaining full command access without executing destructive payloads.
* **SPARTA Mapping**:
  * **ST0001 Reconnaissance** (Ground link eavesdropping)
  * **ST0003 Initial Access** (Uplink Hijacking)
  * **ST0004 Execution** (Command authorization achieved)
* **Relevance to CuCD-ID**: Proves that satellite command uplink hijacking is an established operational threat vector, necessitating on-board autonomous intrusion detection that operates independently of ground control validation.
