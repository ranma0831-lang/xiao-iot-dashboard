import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client, create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]  # service_role: 서버에서만 사용, RLS 우회
DEVICE_KEY = os.environ["DEVICE_KEY"]
DEVICE_ID = "xiao-01"  # shortcut: 보드 1대 고정, 여러 대면 devices 테이블에 기기별 키를 둘 것

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="XIAO ESP32S3 IoT API")
# 토큰은 쿠키가 아닌 Authorization 헤더로 오므로 * 허용해도 CSRF 위험 없음
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer()


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=6)


class Reading(BaseModel):
    temperature: float
    rssi: int


class Led(BaseModel):
    on: bool


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return db.auth.get_user(cred.credentials).user
    except Exception:
        raise HTTPException(401, "invalid token")


def check_device(x_device_key: str = Header()):
    if not hmac.compare_digest(x_device_key, DEVICE_KEY):
        raise HTTPException(401, "invalid device key")


def led_state() -> bool:
    rows = db.table("devices").select("led").eq("id", DEVICE_ID).execute().data
    return bool(rows and rows[0]["led"])


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/signup", status_code=201)
def signup(c: Credentials):
    try:
        # admin API로 만들면 이메일 인증 없이 바로 로그인 가능
        db.auth.admin.create_user({"email": c.email, "password": c.password, "email_confirm": True})
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"email": c.email}


@app.post("/auth/login")
def login(c: Credentials):
    # 공유 클라이언트로 로그인하면 이후 DB 요청이 유저 권한으로 바뀌므로 매번 새 클라이언트 사용
    try:
        s = create_client(SUPABASE_URL, SUPABASE_KEY).auth.sign_in_with_password(
            {"email": c.email, "password": c.password}
        ).session
    except Exception:
        raise HTTPException(401, "wrong email or password")
    return {"access_token": s.access_token, "token_type": "bearer"}


@app.get("/readings")
def readings(limit: int = 50, user=Depends(current_user)):
    limit = max(1, min(limit, 500))
    return (
        db.table("sensor_readings").select("temperature,rssi,created_at")
        .eq("device_id", DEVICE_ID).order("created_at", desc=True).limit(limit).execute().data
    )


@app.get("/led")
def get_led(user=Depends(current_user)):
    return {"on": led_state()}


@app.put("/led")
def set_led(led: Led, user=Depends(current_user)):
    db.table("devices").upsert({"id": DEVICE_ID, "led": led.on}).execute()
    return {"on": led.on}


@app.post("/device/readings", dependencies=[Depends(check_device)])
def device_reading(r: Reading):
    # 보드는 센서값을 올리고 응답으로 LED 상태를 받음: 요청 1번으로 업로드+폴링 처리
    db.table("sensor_readings").insert({"device_id": DEVICE_ID, **r.model_dump()}).execute()
    return {"led": led_state()}
