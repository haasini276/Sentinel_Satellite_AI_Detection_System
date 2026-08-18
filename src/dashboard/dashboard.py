import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="Sentinel AI Ground Control", layout="wide")

st.title("🛰️ Sentinel Satellite Real-Time Telemetry Monitor")
st.markdown("### Phase 5: Live Anomaly Detection & SHAP Diagnostic Console")

# Sidebar Controls
st.sidebar.header("Telemetry Stream Controls")
stream_speed = st.sidebar.slider("Stream Refresh Interval (s)", 0.5, 3.0, 1.0)
api_url = st.sidebar.text_input("API Endpoint", "http://127.0.0.1:8000/predict")

# Status Indicators
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Satellite Status", value="ORBITAL - NOMINAL")
with col2:
    st.metric(label="Active Model", value="XGBoost Phase 4")
with col3:
    st.metric(label="Latency", value="< 12 ms")

st.divider()

# Interactive Manual Injection Form
st.subheader("Manual Telemetry Injection Test")
with st.form("telemetry_form"):
    c1, c2, c3, c4, c5 = st.columns(5)
    msg_length = c1.number_input("MsgLength", value=128.0)
    cmd_code = c2.number_input("CmdCode", value=4.0)
    time_rad = c3.number_input("TimeRadians", value=1.57)
    apid = c4.number_input("ApId", value=102.0)
    msg_id = c5.number_input("MsgId", value=50.0)
    
    submit = st.form_submit_button("Send Payload to AI API")

if submit:
    payload = {
        "MsgLength": msg_length,
        "CmdCode": cmd_code,
        "TimeRadians": time_rad,
        "ApId": apid,
        "MsgId": msg_id
    }
    try:
        response = requests.post(api_url, json=payload).json()
        if response.get("is_anomaly"):
            st.error(f"🚨 {response['status']} (Class: {response['prediction_class']} | Confidence: {response['confidence_score']*100:.1f}%)")
        else:
            st.success(f"✅ {response['status']} (Confidence: {response['confidence_score']*100:.1f}%)")
    except Exception as e:
        st.warning("Ensure FastAPI server is running (`uvicorn app:app --reload`)")