# XIAO ESP32S3 IoT 대시보드

XIAO ESP32S3 보드의 센서값을 웹에서 보고 LED를 원격 제어하는 프로젝트.
보드·백엔드·대시보드가 모두 인터넷(HTTPS)으로 통신하므로 **보드와 대시보드가 다른 WiFi여도 제어됩니다.**

| 구성 | 기술 | 배포 |
|------|------|------|
| 백엔드 | FastAPI + Supabase (Auth, Postgres) | Render — https://xiao-iot-api-gdd0.onrender.com |
| 대시보드 | HTML/JS 단일 파일 | Vercel — https://xiao-iot-dashboard-alpha.vercel.app |
| 펌웨어 | Arduino (ESP32 core) | XIAO ESP32S3 |

## 동작 방식

```
[XIAO ESP32S3] --POST /device/readings (온도, RSSI)--> [Render FastAPI] <--> [Supabase]
               <------------ 응답: {"led": true} ------         ^
                                                                 | HTTPS (로그인 토큰)
                                                     [Vercel 대시보드 (브라우저)]
```

- 보드는 3초마다 센서값을 POST하고, **같은 응답으로 LED 상태를 받아** 반영합니다 (HTTP 폴링).
- 대시보드는 3초마다 센서값을 새로고침하고, LED 버튼은 `PUT /led`로 DB 상태를 바꿉니다.
- 센서: 외부 배선 없이 칩 내부 온도(`temperatureRead()`)와 WiFi 신호 세기(RSSI). LED: 내장 LED(GPIO21, LOW=켜짐).

## API

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| POST | `/auth/signup` | - | 회원가입 `{email, password}` (이메일 인증 없이 바로 사용) |
| POST | `/auth/login` | - | 로그인 → `access_token` |
| GET | `/readings?limit=50` | Bearer | 최근 센서값 |
| GET | `/led` | Bearer | LED 상태 |
| PUT | `/led` | Bearer | LED 켜기/끄기 `{on: true}` |
| POST | `/device/readings` | `X-Device-Key` | 보드 전용: 센서값 업로드, 응답으로 LED 상태 |
| GET | `/health` | - | 헬스체크 |

Swagger 문서: https://xiao-iot-api-gdd0.onrender.com/docs

## 처음부터 설정하기

### 1. Supabase
SQL Editor에서 [`supabase.sql`](supabase.sql) 실행. Project Settings > API Keys에서 URL과 secret(service_role) 키 확인.

### 2. 백엔드 (Render)
환경변수: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `DEVICE_KEY`(보드 인증용 랜덤 문자열)

```bash
render services create --name xiao-iot-api --type web_service \
  --repo https://github.com/<you>/xiao-iot-dashboard --branch main --root-directory backend \
  --runtime python --plan free --build-command "pip install -r requirements.txt" \
  --start-command 'uvicorn main:app --host 0.0.0.0 --port $PORT' --health-check-path /health \
  --env-var SUPABASE_URL=... --env-var SUPABASE_SERVICE_KEY=... --env-var DEVICE_KEY=... --confirm
```

로컬 실행: `backend/.env`에 위 3개를 넣고 `uvicorn main:app --reload --env-file .env`. 테스트: `pytest`

### 3. 대시보드 (Vercel)
`frontend/index.html`의 `const API`를 백엔드 주소로 바꾸고 `cd frontend && vercel deploy --prod`

### 4. 펌웨어
`firmware/xiao_iot/secrets.example.h`를 `secrets.h`로 복사해 WiFi, `API_URL`, `DEVICE_KEY` 입력 후:

```bash
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 firmware/xiao_iot
arduino-cli upload  --fqbn esp32:esp32:XIAO_ESP32S3 -p COMx firmware/xiao_iot
arduino-cli monitor -p COMx -c baudrate=115200
```

## 주의

- `secrets.h`, `.env`는 git에 올리지 않습니다. service_role 키는 백엔드(Render)에만 둡니다.
- Render 무료 플랜은 15분간 요청이 없으면 잠들고, 깨어나는 데 30초 정도 걸립니다 (보드가 계속 요청하면 깨어 있음).
- 보드는 서버 인증서 검증을 생략(`setInsecure`)합니다. 실습용 설정입니다.
- 보드 1대(`xiao-01`) 기준이며, 센서값은 3초마다 계속 쌓입니다.
