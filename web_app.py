"""
FastAPI Standalone Web Application and Multi-User Admin Portal.
Runs both locally and inside containerized Docker environments.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from db import (
    init_db, engine, User, AppConfig,
    hash_password, verify_password,
    create_access_token, decode_access_token,
    DATA_DIR
)
from analyzer import SOHAnalyzer
from chemistries import infer_pack_from_capacity, VEHICLE_CATALOG
from certificate import generate_certificate_html
from pdf_certificate import generate_certified_pdf
from crypto_signer import get_or_create_default_keypair, export_public_key_pem, ec
from verifier import verify_certificate_token

app = FastAPI(
    title="EV Battery SOH & Inspection Platform API",
    description="REST & OpenAPI 3.1 compliant endpoints for telemetric battery health evaluation, "
                "electrochemical forecasting, and cryptographically signed PDF certificates.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Startup event to ensure database is migrated and initialized
@app.on_event("startup")
def on_startup():
    init_db()


# Dependency to extract current authenticated user from cookie
def get_current_user(request: Request) -> Optional[User]:
    token = request.cookies.get("soh_auth_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    username = payload["sub"]
    with Session(engine) as session:
        return session.exec(select(User).where(User.username == username, User.is_active == True)).first()


def require_admin(request: Request) -> User:
    user = get_current_user(request)
    if not user or user.role != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin access required")
    return user


# -------------------------------------------------------------
# 1. PUBLIC ROUTES: INDEX & ANALYSIS
# -------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/analyze")
async def process_analysis(
    request: Request,
    file: UploadFile = File(...),
    vin: Optional[str] = Form(None),
    lang: str = Form("fr"),
    annual_km: Optional[float] = Form(None),
    forecast_years: int = Form(3)
):
    with Session(engine) as session:
        cfg = session.get(AppConfig, 1) or AppConfig()

    # Save uploaded CSV into a secure temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
        shutil.copyfileobj(file.file, tmp_csv)
        tmp_csv_path = Path(tmp_csv.name)

    try:
        analyzer = SOHAnalyzer(
            min_delta_soc=cfg.min_delta_soc,
            lang=lang,
            annual_km=annual_km,
            forecast_years=forecast_years,
            vin=vin.strip().upper() if vin else None
        )
        clean_df = analyzer.load_data(tmp_csv_path)
        result = analyzer.analyze(clean_df)

        # Generate HTML report
        out_report_dir = DATA_DIR / "reports"
        out_report_dir.mkdir(parents=True, exist_ok=True)
        report_file = out_report_dir / f"report_{result.analysis_date.strftime('%Y%m%d_%H%M%S')}.html"
        analyzer.generate_html_report(result, report_file)

        # Generate Certified PDF
        pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)
        v_info = {
            "make": pack_info.make,
            "model": f"{pack_info.model} {pack_info.variant}",
            "chemistry": pack_info.chemistry.name
        }

        out_pdf_dir = DATA_DIR / "certificates"
        out_pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_file = out_pdf_dir / f"certificat_{result.analysis_date.strftime('%Y%m%d_%H%M%S')}.pdf"

        pdf_info = generate_certified_pdf(
            result=result,
            csv_file=tmp_csv_path,
            output_pdf_path=pdf_file,
            vehicle_info=v_info,
            lang=lang,
            vin=result.vin
        )

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "result": result,
                "pdf_filename": pdf_file.name,
                "report_filename": report_file.name,
                "pdf_info": pdf_info,
                "pack_info": pack_info,
                "lang": lang
            }
        )

    finally:
        if tmp_csv_path.exists():
            tmp_csv_path.unlink()


@app.get("/download/pdf/{filename}")
def download_pdf(filename: str):
    file_path = DATA_DIR / "certificates" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@app.get("/download/report/{filename}")
def download_report(filename: str):
    file_path = DATA_DIR / "reports" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(file_path, media_type="text/html", filename=filename)


# -------------------------------------------------------------
# 2. REST API ENDPOINTS (OPENAPI COMPATIBLE)
# -------------------------------------------------------------

@app.post("/api/v1/analyze", summary="Analyze Battery Telemetry CSV", tags=["Battery Telemetry Analysis"])
async def api_analyze_battery(
    file: UploadFile = File(..., description="Charging telemetry CSV export"),
    vin: Optional[str] = Form(None, description="Optional 17-character VIN"),
    lang: str = Form("en", description="Language: 'en', 'fr', 'es'"),
    annual_km: Optional[float] = Form(None, description="Projected annual mileage in km"),
    forecast_years: int = Form(3, description="Degradation projection horizon in years")
):
    """
    Ingests charging logs, fits Gaussian LOWESS curves, and returns structured SOH metrics,
    margins of error (95% CI), and multi-scenario projections in JSON format.
    """
    with Session(engine) as session:
        cfg = session.get(AppConfig, 1) or AppConfig()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
        shutil.copyfileobj(file.file, tmp_csv)
        tmp_csv_path = Path(tmp_csv.name)

    try:
        analyzer = SOHAnalyzer(
            min_delta_soc=cfg.min_delta_soc,
            lang=lang,
            annual_km=annual_km,
            forecast_years=forecast_years,
            vin=vin.strip().upper() if vin else None
        )
        clean_df = analyzer.load_data(tmp_csv_path)
        result = analyzer.analyze(clean_df)
        pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)

        return {
            "status": "success",
            "vin": result.vin,
            "vehicle_pack": {
                "make": pack_info.make,
                "model": pack_info.model,
                "variant": pack_info.variant,
                "chemistry": pack_info.chemistry.code,
                "nominal_usable_kwh": pack_info.nominal_usable_kwh,
                "gross_kwh": pack_info.gross_kwh
            },
            "soh_evaluation": {
                "current_soh_pct": round(result.current_soh, 2),
                "soh_ci95_err_pct": round(result.current_soh_err, 2),
                "current_usable_kwh": round(result.current_capacity, 2),
                "usable_ci95_err_kwh": round(result.current_capacity_err, 2),
                "factory_baseline_kwh": round(result.initial_capacity, 2),
                "total_degradation_pct": round(result.total_degradation_pct, 2)
            },
            "telemetry_statistics": {
                "total_recorded_sessions": result.total_charges,
                "qualified_sessions": result.qualified_charges,
                "odometer_km": result.odometer_max,
                "annual_km_pace": round(result.annual_km, 0),
                "dc_fast_charge_pct": result.dc_energy_pct,
                "mean_temperature_celsius": result.mean_temperature
            },
            "forecast_scenarios": [
                {
                    "horizon": sm.horizon_label,
                    "target_date": sm.target_date.strftime("%Y-%m-%d"),
                    "projected_odometer_km": round(sm.projected_odometer, 0),
                    "soh_optimistic_pct": sm.soh_optimistic,
                    "soh_realistic_pct": sm.soh_realistic,
                    "soh_severe_pct": sm.soh_severe
                }
                for sm in result.scenario_milestones
            ]
        }
    finally:
        if tmp_csv_path.exists():
            tmp_csv_path.unlink()


@app.get("/api/v1/vehicles", summary="Get EV Pack & Chemistry Catalog", tags=["Vehicle Catalog"])
def api_get_vehicles():
    """
    Returns the comprehensive catalog of EV models, nominal pack capacities, and chemistry profiles.
    """
    return {
        key: {
            "make": p.make,
            "model": p.model,
            "variant": p.variant,
            "nominal_usable_kwh": p.nominal_usable_kwh,
            "gross_kwh": p.gross_kwh,
            "chemistry": p.chemistry.code,
            "typical_cycle_life": p.chemistry.typical_cycle_life_80,
            "wltp_range_km": p.wltp_range_km
        }
        for key, p in VEHICLE_CATALOG.items()
    }


@app.get("/api/v1/verify", summary="Verify Certificate Token", tags=["Certificate Verification"])
def api_verify_certificate(token: str):
    """
    Mathematically verifies the authenticity of a certificate URI or signature token.
    """
    return verify_certificate_token(token)


# -------------------------------------------------------------
# 3. ADMIN AUTHENTICATION & MANAGEMENT
# -------------------------------------------------------------

@app.get("/admin/login", response_class=HTMLResponse)
def login_view(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/admin/login")
def login_action(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Identifiants invalides."})

        # Issue secure cookie with JWT token
        token = create_access_token({"sub": user.username, "role": user.role})
        resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        resp.set_cookie(key="soh_auth_token", value=token, httponly=True, samesite="lax")
        return resp


@app.get("/admin/logout")
def logout_action():
    resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("soh_auth_token")
    return resp


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    with Session(engine) as session:
        config = session.get(AppConfig, 1) or AppConfig()
        users = session.exec(select(User)).all()

    # Active public key
    _, pub_key = get_or_create_default_keypair()
    pub_pem = export_public_key_pem(pub_key)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "current_user": user,
            "config": config,
            "users": users,
            "public_key_pem": pub_pem,
            "message": None
        }
    )


@app.post("/admin/config")
def update_config(
    request: Request,
    min_delta_soc: float = Form(40.0),
    calibration_100_weight: float = Form(2.5),
    default_forecast_years: int = Form(3),
    knee_point_enabled: Optional[bool] = Form(False)
):
    user = get_current_user(request)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    with Session(engine) as session:
        cfg = session.get(AppConfig, 1) or AppConfig()
        cfg.min_delta_soc = min_delta_soc
        cfg.calibration_100_weight = calibration_100_weight
        cfg.default_forecast_years = default_forecast_years
        cfg.knee_point_enabled = bool(knee_point_enabled)
        session.add(cfg)
        session.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/users/create")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("auditor")
):
    user = get_current_user(request)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        new_u = User(username=username, password_hash=hash_password(password), role=role)
        session.add(new_u)
        session.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/regen-keys")
def regenerate_keys(request: Request):
    user = get_current_user(request)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Generate fresh ECDSA P-256 pair
    from crypto_signer import DEFAULT_KEY_DIR
    new_priv = ec.generate_private_key(ec.SECP256R1())
    new_pub = new_priv.public_key()
    from cryptography.hazmat.primitives import serialization

    priv_pem = new_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_pem = new_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (DEFAULT_KEY_DIR / "soh_private_key.pem").write_bytes(priv_pem)
    (DEFAULT_KEY_DIR / "soh_public_key.pem").write_bytes(pub_pem)

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
