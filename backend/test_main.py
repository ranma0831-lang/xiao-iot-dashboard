import os
from unittest.mock import MagicMock

os.environ.update(SUPABASE_URL="https://x.supabase.co", SUPABASE_SERVICE_KEY="k", DEVICE_KEY="dev-secret")
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

main.db = MagicMock()
client = TestClient(main.app)


def test_device_key_and_led_reply():
    body = {"temperature": 31.2, "rssi": -60}
    assert client.post("/device/readings", json=body, headers={"X-Device-Key": "wrong"}).status_code == 401
    main.db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"led": True}]
    r = client.post("/device/readings", json=body, headers={"X-Device-Key": "dev-secret"})
    assert r.json() == {"led": True}


def test_user_routes_need_token():
    assert client.get("/readings").status_code in (401, 403)
    main.db.auth.get_user.side_effect = Exception("bad")
    assert client.put("/led", json={"on": True}, headers={"Authorization": "Bearer x"}).status_code == 401
