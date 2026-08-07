"""
Builds a persistent ChromaDB collection from the Cybersecurity Lead's SPARTA
mapping table + real-world incident case studies (cybersecurity_lead_complete_package.md).
Run once (or whenever that source file changes): python build_sparta_kb.py
"""

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from pathlib import Path
import chromadb

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DOCUMENTS = [
    # --- Section 1: SPARTA class -> tactic/technique mapping (one doc per class) ---
    {
        "id": "class_0_normal",
        "metadata": {"type": "class_mapping", "class_id": "0", "class_name": "Normal",
                     "tactic_id": "N/A", "technique_id": "NORMAL"},
        "text": (
            "Class 0: Normal. SPARTA Tactic: N/A (Baseline Ops). SPARTA Technique: NORMAL "
            "(Nominal Telemetry). Baseline Operations: Telemetry cadence, memory allocation, "
            "and CCSDS message IDs match nominal orbit parameters. Zero threat active. "
            "Deeper detail: nominal telemetry is a tight statistical band, not just 'no signal' "
            "— message IDs, command codes, and inter-arrival timings cluster close to their "
            "orbit-baseline mean with low variance. Some nominal features can still drift under "
            "realistic sensor/channel noise without any actual threat present, which is why a "
            "single-feature-deviation gate is unreliable and a multi-feature or recalibrated-"
            "baseline detection approach is needed."
        ),
    },
    {
        "id": "class_1_storage_exhaustion",
        "metadata": {"type": "class_mapping", "class_id": "1", "class_name": "Storage Exhaustion",
                     "tactic_id": "ST0009", "technique_id": "SV-MA-1 / EX-0014.03"},
        "text": (
            "Class 1: Storage Exhaustion. SPARTA Tactic: ST0009 (Impact). SPARTA Technique: "
            "SV-MA-1 (Resource Exhaustion) / EX-0014.03 (Memory Exhaustion). Paper citations: "
            "IMP-0003, EX-0014.03. In flight software, this specifically starves active FSW "
            "tasks of memory buffers (MemoryShmemMB, MemoryAnonMB), causing application failure "
            "or watchdog resets. Deeper detail: maps to the general software weakness CWE-400 "
            "(Uncontrolled Resource Consumption). cFS shared memory segments and anonymous RAM "
            "pools are typically fixed-size pools sized for worst-case nominal load, not elastic "
            "like a cloud VM; filling them starves every other FSW task sharing that pool, not "
            "just the targeted one, so failures can cascade into unrelated subsystems. Real-world "
            "terrestrial analog: memory-exhaustion DoS against an embedded RTOS with no OOM-"
            "killer safety net."
        ),
    },
    {
        "id": "class_2_command_flooding",
        "metadata": {"type": "class_mapping", "class_id": "2", "class_name": "Command Flooding",
                     "tactic_id": "ST0009 / ST0003", "technique_id": "SV-MA-1"},
        "text": (
            "Class 2: Command Flooding. SPARTA Tactic: ST0009 (Impact) and ST0003 (Initial "
            "Access). SPARTA Technique: SV-MA-1 (Resource Exhaustion / DoS via Command Queue "
            "Saturation). Paper citations: EX-0013.01, SV-MA-1. High-rate unauthenticated CCSDS "
            "telecommand injection overflows the flight software bus receiver queue, causing "
            "SlidingWindowMaxIntervalSec to drop near 0.0s and dropping legitimate ground "
            "commands. Deeper detail: maps to CWE-770 (Allocation of Resources Without Limits or "
            "Throttling). Many legacy CCSDS Telecommand (TC) Space Data Link Protocol "
            "implementations don't mandate per-command authentication or rate-limiting at the "
            "link layer, leaving the receiver's ingest queue exposed to raw-volume attacks — "
            "structurally the same problem class as a terrestrial SYN-flood, where defense means "
            "rate-limiting total ingest, not filtering by validity."
        ),
    },
    {
        "id": "class_3_data_injection",
        "metadata": {"type": "class_mapping", "class_id": "3", "class_name": "Data Injection",
                     "tactic_id": "ST0009 / ST0008", "technique_id": "SV-MA-2"},
        "text": (
            "Class 3: Data Injection. SPARTA Tactic: ST0009 (Impact) and ST0008 (Exfiltration). "
            "SPARTA Technique: SV-MA-2 (False Data Injection / Telemetry Spoofing). Paper "
            "citations: IMP-0003, SV-MA-2. Adversary injects fabricated CCSDS telemetry packets "
            "(UniqueMessageIDsInWindow anomalies); can mislead ground operators, trigger false "
            "ADCS maneuvers, or mask concurrent data exfiltration. Deeper detail: maps to CWE-290 "
            "(Authentication Bypass by Spoofing). Because CCSDS Telemetry (TM) packets are often "
            "transmitted without cryptographic integrity protection (no MAC/signature) on "
            "resource-constrained missions, a spoofed packet matching the expected format is "
            "indistinguishable from a genuine one at the protocol level — detection has to happen "
            "behaviorally, not cryptographically. This same behavioral ambiguity is why genuinely-"
            "Normal packets sometimes resemble injected ones, the project's confirmed "
            "Normal-to-Data-Injection confusion mode."
        ),
    },
    {
        "id": "class_4_defence_impairment",
        "metadata": {"type": "class_mapping", "class_id": "4", "class_name": "Defence Impairment",
                     "tactic_id": "ST0006", "technique_id": "DE-0001"},
        "text": (
            "Class 4: Defence Impairment. SPARTA Tactic: ST0006 (Defense Evasion). SPARTA "
            "Technique: DE-0001 (Onboard Security Monitor Impairment). Paper citation: DE-0001. "
            "Targeted attack issuing unauthorized commands to disable, corrupt, or overload "
            "onboard anomaly detection or health monitoring FSW applications prior to launching "
            "primary impact payloads. Considered critical severity. Deeper detail: directly "
            "analogous to MITRE ATT&CK Enterprise Technique T1562 (Impair Defenses). In FSW "
            "terms this typically means disabling or corrupting the watchdog timer process, the "
            "onboard anomaly-detection task, or the health-and-status monitoring application. It "
            "is usually a precursor move — an attacker blinds the system's own detection "
            "capability first, so a subsequent Storage Exhaustion, Command Flooding, or Data "
            "Injection attack goes unnoticed, which is why its autonomous-action confidence "
            "threshold is set lower (>=0.70) than the other attack classes (>=0.85)."
        ),
    },
    # --- Section 3: Real-world incident case studies ---
    {
        "id": "incident_viasat_kasat_2022",
        "metadata": {"type": "incident", "year": "2022", "name": "Viasat KA-SAT",
                     "tactic_id": "ST0003 / ST0006 / ST0009"},
        "text": (
            "Viasat KA-SAT Satellite Network Cyberattack (February 2022). On February 24, 2022, "
            "coinciding with military operations in Ukraine, a destructive cyberattack struck the "
            "Viasat KA-SAT satellite network. Adversaries exploited a misconfigured VPN device to "
            "breach the ground control network, then executed malicious wiper software (AcidRain) "
            "that overwrote flash memory on tens of thousands of satellite user terminals across "
            "Europe. SPARTA mapping: ST0003 Initial Access (ground station network compromise), "
            "ST0006 Defense Evasion (disguised management commands), ST0009 Impact (SV-MA-1 "
            "denial of service via terminal flash wipe)."
        ),
    },
    {
        "id": "incident_rosat_1998",
        "metadata": {"type": "incident", "year": "1998", "name": "ROSAT",
                     "tactic_id": "ST0003 / ST0009"},
        "text": (
            "ROSAT Spacecraft Attitude Control Compromise (1998). A cyber intrusion into the "
            "NASA / DLR Munich ground control station gave unauthorized actors access to the "
            "ROSAT X-ray satellite command link. Attackers transmitted unauthorized guidance "
            "commands instructing the satellite to turn its solar arrays directly at the Sun, "
            "overloading the sensor payload and causing irreparable hardware damage. SPARTA "
            "mapping: ST0003 Initial Access (command link intrusion), ST0009 Impact (SV-MA-1 "
            "resource abuse / destructive command execution)."
        ),
    },
    {
        "id": "incident_terra_landsat_2007_2008",
        "metadata": {"type": "incident", "year": "2007-2008", "name": "Terra & Landsat-7",
                     "tactic_id": "ST0001 / ST0003 / ST0004"},
        "text": (
            "U.S. Terra & Landsat-7 Satellite Uplink Intrusions (2007-2008). Documented in the "
            "US-China Economic and Security Review Commission 2011 report, unauthorized actors "
            "repeatedly compromised ground station antennas in Svalbard, Norway, achieving full "
            "uplink access to the Landsat-7 satellite (October 2007, 12+ minutes) and the Terra "
            "EOS earth observation satellite (June and October 2008, 2+ minutes), obtaining full "
            "command access without executing destructive payloads. SPARTA mapping: ST0001 "
            "Reconnaissance, ST0003 Initial Access, ST0004 Execution."
        ),
    },
    {
        "id": "incident_jpl_raspberry_pi_2018",
        "metadata": {"type": "incident", "year": "2018", "name": "NASA JPL breach",
                     "tactic_id": "ST0003 / ST0008"},
        "text": (
            "NASA JPL Network Breach via Unauthorized Raspberry Pi (2018). Documented in NASA "
            "Office of Inspector General Report IG-19-022. An attacker gained access to the Jet "
            "Propulsion Laboratory network in April 2018 through a Raspberry Pi connected without "
            "authorization or security review. The attacker moved laterally across JPL's shared "
            "network gateway for roughly 10 months undetected, exfiltrating about 500MB of data "
            "related to the Mars Science Laboratory mission. SPARTA mapping: ST0003 Initial "
            "Access (unauthorized ground-segment device), ST0008 Exfiltration (extended undetected "
            "data exfiltration)."
        ),
    },
    {
        "id": "incident_athena_fidus_2018",
        "metadata": {"type": "incident", "year": "2018", "name": "Athena-Fidus jamming",
                     "tactic_id": "ST0001"},
        "text": (
            "Athena-Fidus Military Satellite Signal Interference (2018). French Defence Minister "
            "Florence Parly publicly stated the Franco-Italian military communications satellite "
            "Athena-Fidus had its signal approached/intercepted in 2017 by a Russian intelligence "
            "vessel (the Yantar), in what she described as an attempted signal interception. "
            "Attribution is a public government statement, not an independently verified forensic "
            "finding. SPARTA mapping: ST0001 Reconnaissance (signal/communications interception "
            "attempt)."
        ),
    },
    {
        "id": "incident_nato_gps_jamming_2018",
        "metadata": {"type": "incident", "year": "2018", "name": "NATO Trident Juncture GPS jamming",
                     "tactic_id": "ST0009"},
        "text": (
            "NATO Trident Juncture Exercise GPS Interference (2018). During NATO's Trident "
            "Juncture exercise in Norway/Finland (Oct-Nov 2018), officials reported GPS signal "
            "disruptions affecting military and civilian aircraft and vessels, publicly attributed "
            "by Norway's government to Russia. Suspected GPS jamming/interference at the receiver "
            "end; a public attribution, not a court-adjudicated finding. SPARTA mapping: ST0009 "
            "Impact (denial of positioning/navigation service via signal-layer interference)."
        ),
    },
    {
        "id": "incident_c4ads_gps_spoofing_2019",
        "metadata": {"type": "incident", "year": "2019", "name": "C4ADS GPS spoofing report",
                     "tactic_id": "ST0009"},
        "text": (
            "Large-Scale GPS Spoofing Documented by C4ADS 'Above Us Only Stars' (2019). The "
            "nonprofit research group C4ADS published a 2019 report documenting thousands of GPS "
            "spoofing incidents affecting vessel and aircraft navigation, concentrated around the "
            "Black Sea, Russian ports, and Syria, identified via publicly available AIS data "
            "showing physically-impossible position jumps. Ground-based spoofing equipment "
            "broadcasts fabricated satellite navigation signals that overpower genuine GPS "
            "signals at the receiver. SPARTA mapping: ST0009 Impact (SV-MA-2-style false data "
            "injection applied to satellite navigation signals rather than telemetry). This is "
            "the clearest large-scale real-world precedent for the Data Injection threat "
            "category: fabricated signals designed to be accepted as genuine by an automated "
            "receiver."
        ),
    },
    {
        "id": "incident_turla_satellite_hijack_2015",
        "metadata": {"type": "incident", "year": "2015", "name": "Turla satellite-link C2 hijacking",
                     "tactic_id": "ST0006"},
        "text": (
            "Satellite-Internet-Link Hijacking for Anonymous C2, Turla APT (publicized 2015). "
            "Security researchers, notably Kaspersky's GReAT team, documented the Turla advanced "
            "persistent threat group hijacking unencrypted consumer satellite internet (DVB-S) "
            "downlink traffic to route command-and-control communications for its malware. "
            "Because satellite internet downlink broadcasts are receivable by anyone within the "
            "satellite's footprint and are frequently unencrypted, attackers listened for "
            "legitimate subscribers' IP addresses and sent spoofed C2 traffic appearing to "
            "originate from that satellite link, making the true origin untraceable. SPARTA "
            "mapping: ST0006 Defense Evasion (anonymizing/obscuring the true origin of malicious "
            "command traffic). Shows attackers exploiting the satellite communications medium "
            "itself as an evasion tool, not just attacking a specific onboard defense mechanism."
        ),
    },
]


def main():
    client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_sparta"))
    collection = client.get_or_create_collection("sparta_knowledge")

    collection.upsert(
        ids=[d["id"] for d in DOCUMENTS],
        documents=[d["text"] for d in DOCUMENTS],
        metadatas=[d["metadata"] for d in DOCUMENTS],
    )
    print(f"Indexed {len(DOCUMENTS)} documents into ./chroma_sparta (collection: sparta_knowledge)")


if __name__ == "__main__":
    main()
