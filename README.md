'''
Sentinel_Satellite_AI_Detection_System/
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
├── requirements.txt
│
├── docs/
│   ├── architecture.md                  # agent roster + data flow diagram
│   ├── planning/
│   │   ├── week1_foundations.md
│   │   ├── week2_baselines.md
│   │   ├── week3_core_build.md
│   │   ├── week4_integration.md
│   │   ├── week5_hardening.md
│   │   └── week6_polish_submit.md       # one file per phase deliverable + notes
│   ├── security/
│   │   ├── threat_model.md              # SPARTA mapping table
│   │   ├── mitigation_policy.md         # confidence-band → action table
│   │   ├── adversarial_test_log.md      # Phase 5 stress-test results
│   │   └── known_limitations.md         # honest failure-mode writeup
│   ├── resume_bullets.md
│   └── demo_video_script.md
│
├── data/
│   ├── raw/
│   │   └── consolidated_dataset_raw.csv
│   ├── noised/
│   │   └── noised_dataset.csv
│   └── README.md                        # schema notes, autocorrelation warning
│
├── notebooks/
│   ├── data_reconnaissance.ipynb
│   └── Satellite_Telemetry_AI_Pipeline.ipynb
│
├── src/
│   ├── ml/                              # ML Lead's domain
│   │   ├── train_baseline.py
│   │   ├── compute_baseline_stats.py
│   │   ├── baseline_xgb.json
│   │   ├── baseline_feature_order.json
│   │   ├── nominal_baseline_stats.json
│   │   └── models/                      # LSTM, Autoencoder go here (Week 3+)
│   │
│   ├── agents/                          # Agentic AI Lead's domain
│   │   ├── helloworldagent.py
│   │   ├── classifier_agent.py
│   │   ├── sparta_agent.py
│   │   ├── mitigation_agent.py
│   │   └── incident_reporter_agent.py   # add in Week 3
│   │
│   ├── tools/                           # CrewAI tools called by agents
│   │   ├── classifier_tool.py
│   │   ├── monitor_tool.py
│   │   ├── sparta_tool.py
│   │   └── mitigation_tool.py
│   │
│   ├── rag/
│   │   └── build_sparta_kb.py           # ChromaDB knowledge base builder
│   │
│   ├── simulator/                       # Software/Integration Lead's domain
│   │   ├── telemetry_simulator.py
│   │   ├── Telemetry_simulation_instructions.md
│   │   └── Telemetry_simulation_requirements.txt
│   │
│   ├── pipeline/
│   │   └── monitor_pipeline.py
│   │
│   ├── dashboard/
│   │   └── app.py
│   │
│   └── reports/
│       └── cybersecurity_lead_report.md
│
├── tests/
│   ├── test_monitor.py
│   └── test_mitigation_boundaries.py
│
└── deployment/
    ├── huggingface/                     # HF Spaces config, Week 5
    └── onnx/                            # stretch-goal quantization, Week 5
'''
---
