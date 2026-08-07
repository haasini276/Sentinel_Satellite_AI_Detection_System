# Resume Bullets

## Agentic AI Lead

Architected and shipped a 5-agent CrewAI pipeline (Monitor, Classifier, SPARTA Analyst, Mitigation, Incident Reporter) served by Groq-hosted Llama 3.3, wiring a deterministic cost-aware escalation gate (2.8% false-escalation rate on nominal telemetry, ~96-100% attack catch rate) in front of the LLM layer so only anomalous windows ever reach a paid API call.

Built a ChromaDB RAG knowledge base grounding threat explanations in the SPARTA framework and 8 real-world spacecraft security incidents, catching and fixing a semantic-search retrieval regression (pure embedding similarity misrouted an exact-match query once the knowledge base grew) by adding deterministic metadata-filtered lookup for the safety-critical path.

Implemented a rule+LLM hybrid Mitigation Agent enforcing a confidence-banded autonomous-action policy — verified correct at all 14 threshold boundaries — where the LLM narrates justification but never overrides the deterministic policy decision.

Hardened the full pipeline against two real production failure modes surfaced during testing (not simulated): Groq's tokens-per-minute rate limit and malformed LLM tool-call output — both now resolve to a graceful flagged-for-review state instead of crashing — and shipped a cached, rate-limit-safe demo mode so reviewers can evaluate the system with zero API cost and no Groq key of their own.

---
*Draft — tighten with final project-wide metrics (overall accuracy, latency-to-detection) once the ML Lead's final ensemble model and the team's end-to-end integration numbers are finalized.*
