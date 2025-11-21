from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SureCheck AI",
    summary="Intelligent Medical Claims Processing Platform",
    description="**SureCheck AI** is an advanced, AI-powered backend system that revolutionizes medical insurance claim processing. Our platform automates the entire claims adjudication workflow—from document ingestion and classification to structured data extraction, cross-validation, and final decision making.",
    version="0.1.0",
)

# Middlewares
app.add_middleware(CORSMiddleware)


@app.get(
    path="/",
    name="root",
    summary="Root endpoint",
    description="Returns the status of the SureCheck API service to confirm it is running properly",
)
def root_route():
    return {"status": "ok", "message": "SureCheck AI is live and running 💉", "version": "0.1.0"}
