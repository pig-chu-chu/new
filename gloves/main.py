# -*- coding: utf-8 -*-

import queue
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union

import requests
import serial
from flask import Flask, request, jsonify
from flask_cors import CORS
from requests.auth import HTTPBasicAuth

# ================== 基本設定 ==================
app = Flask(__name__)
CORS(app, resources={r"/run/*": {"origins": "*"}, r"/status": {"origins": "*"}})

# 排球來源（video DB）
VB_API_URL = "http://163.13.201.90/video/actionget.php"
VB_API_USER = "feelwithus_vr"
VB_API_PASS = "Fws_vr0000"

# 籃球來源（3D_video DB）
BB_API_URL = "http://163.13.201.90/3d_video/actionget.php"
BB_API_USER = "feelwithus_iot"
BB_API_PASS = "Fws_iot0000"

# 串口（依實際環境調整）
SERIAL_PORT = "/dev/cu.usbserial-110"
BT_SERIAL_PORT = "/dev/cu.GloveController"
BAUD_RATE = 115200

serial_usb: Optional[serial.Serial] = None
serial_bt: Optional[serial.Serial] = None

# 手套命令模板
CATALOG: Dict[str, Dict[str, str]] = {
    'block': "FINGERS:90,70,100,60,80;VIBE:180,180,180,180,180,180,180,180,180,180,180,180,120,120,120,120,120,120,0,0,0",
    'receive': "FINGERS:60,30,80,25,80;VIBE:0,0,0,0,0,0,0,0,0,0,0,0,0,30,30,30,180,180,180",
    'set': "FINGERS:80,60,70,40,60;VIBE:20,20,20,3,3,20,20,0,0,0,0,0,0,0,0,0,0,0,0,0",
    'spike': "FINGERS:130,150,180,80,70;VIBE:255,255,255,255,255,255,255,255,255,200,200,180,180,180,180,180,180,0,0,0",
    'serve': "FINGERS:80,60,70,40,60;VIBE:100,100,100,100,100,100,100,100,100,0,0,0,0,0,0,0,0,0,0",
    '傳球': "FINGERS:80,65,50,45,40;VIBE:120,0,120,0,120,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
    '接球': "FINGERS:70,60,55,50,45;VIBE:40,40,40,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
    '運球': "FINGERS:80,65,50,45,40;VIBE:120,0,120,0,120,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
    '投球': "FINGERS:100,90,80,60,50;VIBE:200,200,200,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"
}

ACTION_ALIAS: Dict[str, str] = {
    "catch": "接球",
    "pass":  "傳球",
    "dribble": "運球",
    "shoot": "投籃",
}

# 狀態管理
state = {
    "data_running": False,
    "data_source": None,
    "db_connected": False,
    "last_error": None,

    "sim_running": False,
    "sim_enabled": False,
    "sim_sport": None,
    "sim_start_epoch": None,
    "sim_sec": 0,
    "sim_progress_sec": 0,
    "current_video": None,
    "last_cmd": None,

    "timeline_cleaned": None,
    "timeline_sec_range": None,
}

# 事件隊列
event_queue: queue.Queue = queue.Queue()

# =============== 串口 ===============
def open_ports():
    global serial_usb, serial_bt
    try:
        if SERIAL_PORT:
            serial_usb = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"[PORT] USB ready {SERIAL_PORT}")
            time.sleep(2.0)
    except Exception as e:
        serial_usb = None
        print(f"[PORT] USB open failed: {e}")
    try:
        if BT_SERIAL_PORT:
            serial_bt = serial.Serial(BT_SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"[PORT] BT ready {BT_SERIAL_PORT}")
            time.sleep(2.0)
    except Exception as e:
        serial_bt = None
        print(f"[PORT] BT open failed: {e}")

def send_cmd(cmd: str):
    payload = (cmd + "\n").encode("utf-8")
    ok = False
    if serial_usb is not None:
        try:
            serial_usb.write(payload); ok = True
        except Exception as e:
            print(f"[PORT] USB write error: {e}")
    if serial_bt is not None:
        try:
            serial_bt.write(payload); ok = True
        except Exception as e:
            print(f"[PORT] BT write error: {e}")
    print(f"[CMD] {cmd} -> {'OK' if ok else 'NO_CHANNEL'}")

# =============== 共用工具 ===============
ALIASES_VB = {"dig":"receive","pass":"receive","setter":"set","attack":"spike","hit":"spike","service":"serve"}

def pick_source_by_video(video_name: str) -> str:
    n = (video_name or "").lower()
    return "basketball" if "basket" in n else "volleyball"

def source_login(sport: str) -> HTTPBasicAuth:
    if sport == "volleyball":
        return HTTPBasicAuth(VB_API_USER, VB_API_PASS)
    else:
        return HTTPBasicAuth(BB_API_USER, BB_API_PASS)

def source_url(sport: str) -> str:
    return VB_API_URL if sport == "volleyball" else BB_API_URL

def db_healthcheck(sport: str) -> bool:
    try:
        r = requests.get(source_url(sport), auth=source_login(sport), timeout=60)
        r.raise_for_status()
        return True
    except Exception:
        return False

# =============== 解析 ===============
Number = Union[int, float]
Row = Dict[str, Any]
Node = Dict[str, Any]

def to_seconds(x):
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip().replace(',', ''))
    if isinstance(x, tuple) and len(x) == 2 and all(isinstance(v,(int,float)) for v in x):
        sec, sub = x; scale = 1e-6 if sub >= 1000 else 1e-3
        return float(sec) + float(sub)*scale
    if isinstance(x, list):
        if len(x) == 2 and all(isinstance(v,(int,float)) for v in x):
            sec, sub = x; scale = 1e-6 if sub >= 1000 else 1e-3
            return float(sec) + float(sub)*scale
        if len(x) == 1 and isinstance(x, (int, float, str)):
            return to_seconds(x)
        raise ValueError(f"Unsupported list time: {x!r}")
    raise TypeError(f"Unsupported time type: {type(x)}: {x!r}")

def normalize_action(name: Any) -> str:
    if name is None:
        raise KeyError("action is None")
    raw = str(name).strip()
    low = raw.lower()
    if raw in CATALOG:
        return raw
    if low in CATALOG:
        return low
    alias = ACTION_ALIAS.get(low)
    if alias and alias in CATALOG:
        return alias
    raise KeyError(f"Unknown action: {raw!r}")

def _pick_time_field(r: Dict[str, Any]) -> Any:
    if "touch_time" in r:
        return r["touch_time"]
    if "time" in r:
        return r["time"]
    if "t" in r:
        return r["t"]
    raise KeyError("missing touch_time/time/t")

def parse_rows_uniform(rows: List[Row], sport: str,
                       *, sort_by_time: bool = True,
                          dedup_same_second: bool = False,
                          drop_meta_events: bool = True) -> List[Node]:
    if not isinstance(rows, list):
        raise TypeError(f"rows must be list, got {type(rows)}")

    norm: List[Tuple[float, Row]] = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise TypeError(f"row[{i}] must be dict, got {type(r)}: {r!r}")

        action_raw = r.get("action") or r.get("act") or r.get("action_key")
        if action_raw is None:
            raise KeyError(f"row[{i}] missing action/action_key: {r!r}")

        if drop_meta_events and str(action_raw).lower() in {"start", "end", "stop"}:
            continue

        try:
            t_raw = _pick_time_field(r)
        except KeyError as e:
            raise KeyError(f"row[{i}] {e}: {r!r}")

        try:
            t_sec = to_seconds(t_raw)
        except Exception as e:
            raise ValueError(f"row[{i}] invalid time {t_raw!r}: {e}") from e

        norm.append((t_sec, {"_action_raw": action_raw, **r}))

    if not norm:
        return []

    if sort_by_time:
        norm.sort(key=lambda x: x[0])

    t0 = norm[0][0]

    timeline: List[Node] = []
    seen_sec: set = set()
    paused_state: Optional[Node] = None   # 用來記錄 switch_off 的狀態

    for t_sec, r in norm:
        try:
            action_key = normalize_action(r["_action_raw"])
        except Exception as e:
            raise KeyError(f"normalize_action failed at t={t_sec}: {e}") from e

        cmd = CATALOG.get(action_key)
        if not cmd:
            raise KeyError(f"No CATALOG entry for action {action_key!r}")

        sec = int(float(t_sec) - float(t0))
        if dedup_same_second:
            if sec in seen_sec:
                continue
            seen_sec.add(sec)

        node: Node = {
            "action_key": action_key,
            "cmd": cmd,
            "touch_time": float(t_sec),
            "sec": sec,
        }

        # === 新增 switch 處理邏輯 ===
        if action_key == "switch_off":
            # 記住當前狀態，不馬上加進 timeline
            paused_state = node

        elif action_key == "switch_on":
            if paused_state:
                # 從 paused_state 接續動作
                resumed_node = {
                    **paused_state,
                    "action_key": paused_state["action_key"] + "_resumed",
                    "sec": sec,  # 續接時間更新成當前 on 的時間
                    "touch_time": float(t_sec),
                }
                timeline.append(resumed_node)
                paused_state = None
            else:
                # 沒有對應 off，就正常加進 timeline
                timeline.append(node)

        else:
            # 一般動作，直接加進 timeline
            timeline.append(node)

    return timeline

def fetch_timeline_once(sport: str, file_name: Optional[str] = None) -> List[Dict[str, Any]]:
    url = source_url(sport)
    auth = source_login(sport)
    params = {"file_name": file_name} if file_name else {}
    try:
        r = requests.get(url, params=params, auth=auth, timeout=8)
        print(f"[URL] {r.url} status={r.status_code}")
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        state["last_error"] = f"fetch error: {e}"
        return []
    if not isinstance(data, list):
        if isinstance(data, dict):
            rows = [data]
        else:
            state["last_error"] = f"bad payload type: {type(data)}"
            return []
    else:
        rows = data
    return parse_rows_uniform(rows, sport)

# =============== 背景工作（Healthcheck） ===============
data_stop_flag = threading.Event()
def data_worker(sport: str):
    state["data_running"] = True
    state["data_source"] = sport
    state["last_error"] = None
    try:
        while not data_stop_flag.is_set():
            state["db_connected"] = db_healthcheck(sport)
            time.sleep(2.0)
    finally:
        state["data_running"] = False
        state["data_source"] = None

# =============== 使用「快取」的時間軸 worker（由 switch 啟動） ===============
timeline_stop_flag = threading.Event()

def timeline_worker_from_cache():
    """
    使用 db_start 緩存的 timeline_cleaned：
    - 以 switch(on) 當下為零時刻，用 monotonic 推進；
    - 到對應 sec 時，把該秒所有節點塞入 queue，glove_worker 負責實際送指令。
    """
    cleaned: List[Dict[str, Any]] = state.get("timeline_cleaned") or []
    if not cleaned:
        print("[TIMELINE] no cached data; stop")
        return

    try:
        state["sim_running"] = True
        due_map: Dict[int, List[Dict[str, Any]]] = {}
        for n in cleaned:
            due_map.setdefault(n["sec"], []).append(n)

        secs_sorted = sorted(due_map.keys())
        min_sec, max_sec = secs_sorted, secs_sorted[-1]
        print(f"[TIMELINE] cached n={len(cleaned)} sec_range=[{min_sec},{max_sec}]")

        start_mono = time.monotonic()
        fired_secs: set = set()
        lead = 0.15
        interval = 0.02

        while not timeline_stop_flag.is_set():
            elapsed = time.monotonic() - start_mono
            cur_sec = int(elapsed)
            state["sim_sec"] = cur_sec
            state["sim_progress_sec"] = cur_sec

            sec_to_fire = int(elapsed + lead)
            if sec_to_fire in due_map and sec_to_fire not in fired_secs:
                nodes = due_map[sec_to_fire]
                for node in nodes:
                    event = {"type": "node",
                             "sec": sec_to_fire,
                             "action_key": node["action_key"],
                             "cmd": node["cmd"],
                             "touch_time": node["touch_time"]}
                    try:
                        event_queue.put(event)
                        print(f"[TIMELINE FIRE] sec={sec_to_fire} action={node['action_key']} cmd={node['cmd']}")
                    except Exception as e:
                        print(f"[TIMELINE] queue put error: {e}")
                fired_secs.add(sec_to_fire)

                if sec_to_fire >= max_sec:
                    print("[TIMELINE] reached end of timeline")
                    try:
                        event_queue.put({"type": "end"})
                    except Exception:
                        pass
                    send_cmd("end")
                    break

            time.sleep(interval)

    except Exception as e:
        state["last_error"] = f"timeline_worker error: {e!r}"
        print(f"[TIMELINE ERROR] {e!r}")
    finally:
        state["sim_running"] = False
        state["sim_sport"] = None
        state["sim_start_epoch"] = None
        print("[TIMELINE] exit")

# glove_worker：常駐 thread，只有在 state['sim_enabled'] == True 時才會執行命令
glove_stop_flag = threading.Event()
def glove_worker():
    print("[GLOVE] worker started")
    while not glove_stop_flag.is_set():
        if not state.get("sim_enabled", False):
            time.sleep(0.05)
            continue
        try:
            event = event_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            if not isinstance(event, dict):
                continue
            if event.get("type") == "node":
                cmd = event.get("cmd")
                if cmd:
                    send_cmd(cmd)
                    state["last_cmd"] = cmd
                time.sleep(0.01)
            elif event.get("type") == "end":
                print("[GLOVE] received end event")
            else:
                print(f"[GLOVE] unknown event: {event}")
        finally:
            try:
                event_queue.task_done()
            except Exception:
                pass

    print("[GLOVE] worker stopped")

# ================= 路由 =================
# db_start (POST): 只抓資料，整理後快取，不啟動播放
@app.route("/api/db_start", methods=["POST"])
def run_db_start():
    global event_queue

    body = request.get_json(silent=True) or {}
    video_name = body.get("db_start") or body.get("videoName")
    if not video_name:
        return jsonify({"success": False, "status": "error", "code": "BAD_PARAMS",
                        "message": "db_start(video name) is required"}), 400

    sport = pick_source_by_video(video_name)
    state["current_video"] = video_name
    state["last_error"] = None

    rows = fetch_timeline_once(sport, video_name)
    if not rows:
        return jsonify({"success": False,"status":"error","code":"EMPTY_TIMELINE"}), 502

    cleaned: List[Dict[str, Any]] = []
    for i, n in enumerate(rows):
        a = n.get("action_key"); c = n.get("cmd"); t = n.get("touch_time"); s = n.get("sec")
        if a is None or c is None or t is None or s is None:
            continue
        cleaned.append({"action_key": str(a), "cmd": str(c), "touch_time": float(t), "sec": int(s)})

    if not cleaned:
        return jsonify({"success": False,"status":"error","code":"CLEAN_EMPTY"}), 502

    cleaned.sort(key=lambda x: (x["sec"], x["action_key"]))
    secs = [n["sec"] for n in cleaned]
    state["timeline_cleaned"] = cleaned
    state["timeline_sec_range"] = (min(secs), max(secs))

    # 啟動/維持健康檢查（可選）
    if not state.get("data_running"):
        data_stop_flag.clear()
        threading.Thread(target=data_worker, args=(sport,), daemon=True).start()

    # 清空舊 queue（避免殘留）
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
            event_queue.task_done()
        except Exception:
            break

    return jsonify({"success": True,"status": "ok",
                    "data": {
                        "source": sport,
                        "videoName": video_name,
                        "events": len(cleaned),
                        "sec_range": state["timeline_sec_range"]
                    }}), 200

# switch (POST): on=以快取資料啟動播放；off=停止播放並回報進度
@app.route("/api/switch", methods=["POST"])
def run_switch():
    body = request.get_json(silent=True)

    if isinstance(body, bool):
        body = {"Switch": body, "videoName": state.get("current_video")}
    elif not isinstance(body, dict):
        body = {}

    sw = body.get("Switch")
    if not isinstance(sw, bool):
        return jsonify({"success": False,"status":"error","code":"BAD_PARAMS","message":"Switch must be boolean"}), 400

    if sw:
        if not state.get("timeline_cleaned"):
            return jsonify({"success": False,"status":"error","code":"NO_CACHE","message":"call db_start first"}), 409
        # 清理舊 timeline 執行
        timeline_stop_flag.set(); time.sleep(0.05); timeline_stop_flag.clear()
        # 啟用播放
        state["sim_enabled"] = True
        threading.Thread(target=timeline_worker_from_cache, daemon=True).start()
        return jsonify({"success": True,"status":"ok","data":{"sim_enabled": True,"mode":"from_cache"}}), 200
    else:
        state["sim_enabled"] = False
        timeline_stop_flag.set()
        state["sim_progress_sec"] = state.get("sim_sec", state.get("sim_progress_sec", 0))
        last = state.get("last_cmd")
        return jsonify({"success": True,"status":"ok",
                        "data":{"sim_enabled": False,"progress_sec": state["sim_progress_sec"], "last_cmd": last}}), 200

# db_stop (POST): 使用者主動停止全部（包含停止接收伺服器）
@app.route("/api/db_stop", methods=["POST"])
def run_db_stop():
    body = request.get_json(silent=True)
    if isinstance(body, str):
        body = {"db_stop": body}
    elif body is None:
        body = {}
    elif not isinstance(body, dict):
        body = {}

    reason = body.get("db_stop") or "end"

    # 停止 background workers
    if state.get("data_running"):
        data_stop_flag.set()
    timeline_stop_flag.set()
    glove_stop_flag.set()

    resp = {
        "stopped": "all",
        "reason": reason,
        "sim_running": bool(state.get("sim_running")),
        "data_running": bool(state.get("data_running")),
        "last_error": state.get("last_error"),
    }
    return jsonify({"success": True, "status": "ok", "data": resp}), 200

# end (GET): 被動停止（影片結束/裝置結束）
@app.route("/api/end", methods=["GET"])
def run_end():
    reason = request.args.get("end") or "passive_end"
    if state["data_running"]:
        data_stop_flag.set()
    timeline_stop_flag.set()
    glove_stop_flag.set()
    return jsonify({"success": True,"status":"ok","data":{"stopped":"all","reason":reason}}), 200

# status (GET): 健康與進度
@app.route("/api/status", methods=["GET"])
def run_status():
    sport = state.get("data_source")
    if not sport:
        vn = (state.get("current_video") or "").lower()
        sport = "basketball" if "basket" in vn else "volleyball"

    ok = False
    try:
        ok = db_healthcheck(sport)
    except Exception as e:
        ok = False
        state["last_error"] = f"healthcheck error: {e!r}"

    state["db_connected"] = ok
    payload = {
        "ok": bool(ok),
        "last_error": state.get("last_error"),
        "data_running": bool(state.get("data_running")),
        "sim_running": bool(state.get("sim_running")),
        "sim_enabled": bool(state.get("sim_enabled")),
        "current_video": state.get("current_video"),
        "sec_range": state.get("timeline_sec_range"),
        "sim_sec": state.get("sim_sec", 0),
    }
    return jsonify(payload), (200 if ok else 404)

# ================== 啟動服務 ==================
if __name__ == "__main__":
    try:
        if SERIAL_PORT or BT_SERIAL_PORT:
            open_ports()
    except Exception as e:
        print(f"[PORT] init skipped: {e}")
    # 啟動 glove worker 一次（常駐），會等待 sim_enabled = True 來處理事件
    t_glove = threading.Thread(target=glove_worker, name="glove_worker_thread", daemon=True)
    t_glove.start()
    app.run(host="0.0.0.0", port=5001)
