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
BT_SERIAL_PORT = "/dev/cu.usbserial-10"
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
    '傳球': "FINGERS:80,65,50,45,40;VIBE:100,110,100,100,80,30,50,30,40,50,0,0,0,0,0,0,0,0,0,0",
    '接球': "FINGERS:70,60,55,50,45;VIBE:80,80,80,80,80,80,80,80,80,80,80,80,80,80,80,80,0,0,0,0",
    '運球': "FINGERS:80,65,50,45,40;VIBE:120,120,120,120,120,120,120,120,120,120,120,120,120,0,0,0,0,0,0,0",
    '投球': "FINGERS:100,90,80,60,50;VIBE:200,200,200,200,200,30,30,30,20,30,20,0,0,0,0,0,0,0,0,0"
}

# 動作別名
ACTION_ALIAS: Dict[str, str] = {
    "catch": "接球",
    "pass":  "傳球",
    "dribble": "運球",
    "shoot": "投球",
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

# ================== 串口操作 ==================
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
            serial_usb.write(payload)
            ok = True
        except Exception as e:
            print(f"[PORT] USB write error: {e}")
    if serial_bt is not None:
        try:
            serial_bt.write(payload)
            ok = True
        except Exception as e:
            print(f"[PORT] BT write error: {e}")
    print(f"[CMD] {cmd} -> {'OK' if ok else 'NO_CHANNEL'}")

# ================== 共用工具 ==================
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

# ================== 解析 ==================
Number = Union[int, float]
Row = Dict[str, Any]
Node = Dict[str, Any]

def to_seconds(x):
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip().replace(',', ''))
    if isinstance(x, (tuple,list)) and len(x)==2 and all(isinstance(v,(int,float)) for v in x):
        sec, sub = x
        scale = 1e-6 if sub >= 1000 else 1e-3
        return float(sec) + float(sub)*scale
    if isinstance(x, list) and len(x)==1:
        return to_seconds(x[0])
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
    for f in ("touch_time","time","t"):
        if f in r:
            return r[f]
    raise KeyError("missing touch_time/time/t")

def parse_rows_uniform(rows: List[Row], sport: str,
                       *, sort_by_time: bool = True,
                       dedup_same_second: bool = False,
                       drop_meta_events: bool = True) -> List[Node]:
    norm: List[Tuple[float, Row]] = []
    for i,r in enumerate(rows):
        action_raw = r.get("action") or r.get("act") or r.get("action_key")
        if action_raw is None:
            continue
        if drop_meta_events and str(action_raw).lower() in {"start","end","stop"}:
            continue
        try:
            t_sec = to_seconds(_pick_time_field(r))
        except Exception:
            continue
        norm.append((t_sec, {"_action_raw": action_raw, **r}))
    if not norm:
        return []
    if sort_by_time:
        norm.sort(key=lambda x: x[0])
    t0 = norm[0][0]
    timeline: List[Node] = []
    paused_state: Optional[Node] = None
    seen_sec: set = set()
    for t_sec, r in norm:
        try:
            action_key = normalize_action(r["_action_raw"])
        except Exception:
            continue
        cmd = CATALOG.get(action_key)
        if not cmd:
            continue
        sec = float(t_sec)
        if dedup_same_second and float(sec) in seen_sec:
            continue
        seen_sec.add(float(sec))
        node: Node = {
            "action_key": action_key,
            "cmd": cmd,
            "touch_time": float(t_sec),
            "sec": sec,
        }
        if action_key == "switch_off":
            paused_state = node
        elif action_key == "switch_on":
            if paused_state:
                resumed_node = {**paused_state, "action_key": paused_state["action_key"] + "_resumed", "sec": sec,
                                "touch_time": float(t_sec)}
                timeline.append(resumed_node)
                paused_state = None
            else:
                timeline.append(node)
        else:
            timeline.append(node)
    return timeline

def fetch_timeline_once(sport: str, file_name: Optional[str] = None) -> List[Node]:
    url = source_url(sport)
    auth = source_login(sport)
    params = {"file_name": file_name} if file_name else {}
    try:
        r = requests.get(url, params=params, auth=auth, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        state["last_error"] = f"fetch error: {e}"
        return []
    if isinstance(data, dict):
        rows=[data]
    elif isinstance(data,list):
        rows=data
    else:
        return []
    return parse_rows_uniform(rows,sport)

# ================== 背景健康檢查 ==================
data_stop_flag = threading.Event()
def data_worker(sport: str):
    state["data_running"]=True
    state["data_source"]=sport
    try:
        while not data_stop_flag.is_set():
            state["db_connected"] = db_healthcheck(sport)
            time.sleep(2.0)
    finally:
        state["data_running"]=False
        state["data_source"]=None

# ================== Timeline Worker ==================
timeline_stop_flag = threading.Event()
def timeline_worker_from_cache():
    cleaned: List[Node] = state.get("timeline_cleaned") or []
    if not cleaned:
        return
    try:
        state["sim_running"] = True
        cleaned.sort(key=lambda x: x["sec"])
        fired_nodes: set = set()
        start_epoch = state.get("sim_start_epoch")  # switch on 設定的開始時間
        if not start_epoch:
            start_epoch = time.monotonic()
            state["sim_start_epoch"] = start_epoch

        lead = 0.02
        interval = 0.005

        while not timeline_stop_flag.is_set():
            cur_time = time.monotonic() - start_epoch
            state["sim_sec"] = cur_time
            state["sim_progress_sec"] = cur_time

            for idx, node in enumerate(cleaned):
                if idx in fired_nodes:
                    continue
                if node["sec"] <= cur_time + lead:
                    print(f"[{node['sec']:.2f}s] Action={node['action_key']}, Cmd={node['cmd']}")
                    event = {
                        "type": "node",
                        "sec": node["sec"],
                        "action_key": node["action_key"],
                        "cmd": node["cmd"],
                        "touch_time": node["touch_time"]
                    }
                    try:
                        event_queue.put(event)
                    except:
                        pass
                    fired_nodes.add(idx)

            if len(fired_nodes) >= len(cleaned):
                try:
                    event_queue.put({"type": "end"})
                    send_cmd("end")
                except:
                    pass
                break
            time.sleep(interval)
    finally:
        state["sim_running"] = False
        state["sim_sport"] = None
        state["sim_start_epoch"] = None
# ================== Glove Worker ==================
glove_stop_flag = threading.Event()
def glove_worker():
    while not glove_stop_flag.is_set():
        if not state.get("sim_enabled",False):
            time.sleep(0.05)
            continue
        try:
            event=event_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type")=="node":
            cmd=event.get("cmd")
            if cmd:
                send_cmd(cmd)
                state["last_cmd"]=cmd
                time.sleep(0.01)
        elif event.get("type")=="end":
            pass
        event_queue.task_done()

# ================== Flask 路由 ==================
@app.route("/api/db_start",methods=["POST"])
def run_db_start():
    body=request.get_json(silent=True) or {}
    video_name=body.get("db_start") or body.get("videoName")
    if not video_name:
        return jsonify({"success":False,"status":"error","code":"BAD_PARAMS"}),400
    sport=pick_source_by_video(video_name)
    state["current_video"]=video_name
    rows=fetch_timeline_once(sport,video_name)
    cleaned=[{"action_key":str(n["action_key"]),"cmd":str(n["cmd"]),"touch_time":float(n["touch_time"]),"sec":int(n["sec"])} for n in rows]
    if not cleaned:
        return jsonify({"success":False,"status":"error","code":"EMPTY_TIMELINE"}),502
    cleaned.sort(key=lambda x:(x["sec"],x["action_key"]))
    secs=[n["sec"] for n in cleaned]
    state["timeline_cleaned"]=cleaned
    state["timeline_sec_range"]=(min(secs),max(secs))
    if not state.get("data_running"):
        data_stop_flag.clear()
        threading.Thread(target=data_worker,args=(sport,),daemon=True).start()
    while not event_queue.empty():
        try: event_queue.get_nowait(); event_queue.task_done()
        except: break
    return jsonify({"success":True,"status":"ok","data":{"source":sport,"videoName":video_name,"events":len(cleaned),"sec_range":state["timeline_sec_range"]}}),200

@app.route("/api/switch", methods=["POST"])
def run_switch():
    body = request.get_json(silent=True)
    if isinstance(body, bool):
        body = {"Switch": body, "videoName": state.get("current_video")}
    elif not isinstance(body, dict):
        body = {}
    sw = body.get("Switch")
    if not isinstance(sw, bool):
        return jsonify({"success": False, "status": "error", "code": "BAD_PARAMS"}), 400

    if sw:
        if not state.get("timeline_cleaned"):
            return jsonify({"success": False, "status": "error", "code": "NO_CACHE"}), 409
        timeline_stop_flag.set()
        time.sleep(0.05)
        timeline_stop_flag.clear()

        state["sim_enabled"] = True
        state["sim_start_epoch"] = time.monotonic()  # 這裡設定開始計時點
        threading.Thread(target=timeline_worker_from_cache, daemon=True).start()
        return jsonify({"success": True, "status": "ok",
                        "data": {"sim_enabled": True, "mode": "from_cache"}}), 200
    else:
        state["sim_enabled"] = False
        timeline_stop_flag.set()
        state["sim_progress_sec"] = state.get("sim_sec", state.get("sim_progress_sec", 0))
        last = state.get("last_cmd")
        return jsonify({"success": True, "status": "ok",
                        "data": {"sim_enabled": False,
                                 "progress_sec": state["sim_progress_sec"],
                                 "last_cmd": last}}), 200
@app.route("/api/db_stop",methods=["POST"])
def run_db_stop():
    body=request.get_json(silent=True) or {}
    reason=body.get("db_stop") or "end"
    if state.get("data_running"): data_stop_flag.set()
    timeline_stop_flag.set(); glove_stop_flag.set()
    return jsonify({"success":True,"status":"ok","data":{"stopped":"all","reason":reason,"sim_running":bool(state.get("sim_running")),"data_running":bool(state.get("data_running")),"last_error":state.get("last_error")}}),200

MOBILE_API_URL = "http://27.53.147.112/endpoint"  # 改成你的手機端 API URL
MOBILE_API_TIMEOUT = 5  # 秒

@app.route("/api/end", methods=["GET"])
def run_end():
    reason = request.args.get("end") or "passive_end"
    if state["data_running"]:
        data_stop_flag.set()
    timeline_stop_flag.set()
    glove_stop_flag.set()
    return jsonify({"success": True,"status":"ok","data":{"stopped":"all","reason":reason}}), 200

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

    #================== 啟動服務 ==================
if __name__ == "__main__":
        try:
            if SERIAL_PORT or BT_SERIAL_PORT:
                open_ports()
        except Exception as e:
            print(f"[PORT] init skipped: {e}")
        t_glove = threading.Thread(target=glove_worker, name="glove_worker_thread", daemon=True)
        t_glove.start()
        app.run(host="0.0.0.0", port=5001)

