from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd

# Initialize FastAPI App
app = FastAPI(
    title="Sentinel Satellite AI Anomaly Detection API",
    version="5.0",
    description="Real-time telemetry anomaly classification & risk scoring engine"
)

# Load Phase 4 Artifacts
scaler = joblib.load("telemetry_scaler.pkl")
model = joblib.load("xgb_phase4_model.pkl")

class TelemetryPacket(BaseModel):
    MsgLength: float
    CmdCode: float
    TimeRadians: float
    ApId: float
    MsgId: float

@app.get("/")
def health_check():
    return {"status": "ONLINE", "system": "Sentinel Satellite AI Detection System"}

@app.post("/predict")
def predict_anomaly(packet: TelemetryPacket):
    try:
        # Format input data
        data_raw = np.array([[
            packet.MsgLength, packet.CmdCode, 
            packet.TimeRadians, packet.ApId, packet.MsgId
        ]])
        
        # Scale features using saved Phase 4 scaler
        data_scaled = scaler.transform(data_raw)
        
        # Predict class & confidence
        prediction = int(model.predict(data_scaled)[0])
        probabilities = model.predict_proba(data_scaled)[0]
        confidence = float(np.max(probabilities))
        
        is_anomaly = bool(prediction != 0)
        
        return {
            "prediction_class": prediction,
            "is_anomaly": is_anomaly,
            "confidence_score": round(confidence, 4),
            "status": "ALERT: Anomaly Detected!" if is_anomaly else "NORMAL: Systems Nominal"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))