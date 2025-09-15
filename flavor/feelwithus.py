from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import threading, time, requests, serial

# 建立 Flask 應用實例並啟用 CORS
app = Flask(__name__)
CORS(app)

# ============ 全域狀態 ============
state = {
    'data_running': False,     # 資料抓取執行中狀態
    'data_source': None,       # 資料來源類型（籃球或排球）
    'video_name': None,        # 當前處理的影片名稱
    'data_ready': False,       # 資料整理完成可傳送
    'switch_enabled': False,   # 硬體開關狀態
    'ended': False,            # 動作序列播放結束旗標
}

# 全域緩存：raw_buffer 存放原始從 API 抓到的動作清單，
# organized_buffer 存放排序與去重後準備要播放的動作
raw_buffer = []
organized_buffer = []

# 執行排程用索引（目前未使用，可依需要擴充）
current_index = 0

# 動作冷卻時間（秒），避免動作間隔過短重覆觸發
COOLDOWN = 8

# 允許的動作集合
ALLOWED_ACTIONS = {"運球", "start", "end", "投球", "RECEIVE", "SET", "SERVE", "SPIKE", "BLOCK"}

# 前端接收結束通知的 API URL
FRONTEND_END_URL = "http://localhost:3000/api/end"

# 初始化 Arduino Serial 連線（COM3，鮑率 9600）
ser = serial.Serial('COM3', 9600, timeout=1)
print(f"[DEBUG] Serial port: {ser.port}, baudrate: {ser.baudrate}, open: {ser.is_open}")

def serial_reader():
    """
    在背景執行持續讀取 Arduino 傳回的序列資料，
    並印出 debug 訊息。
    """
    while True:
        try:
            line = ser.readline()
            if line:
                print(f"[ARDUINO] {line.decode().strip()}")
        except:
            pass

# 啟動序列埠讀取執行緒，daemon=True 隨主程式結束而結束
threading.Thread(target=serial_reader, daemon=True).start()

def pick_source_by_video(video_name: str) -> str:
    """
    根據影片名稱判斷資料來源，
    包含 'basket' 則視為籃球，否則視為排球。
    """
    return 'basketball' if 'basket' in video_name.lower() else 'volleyball'

def fetch_actions_from_db() -> list:
    """
    從遠端 API 抓取動作資料。
    根據 state['data_source'] 決定 URL 與認證。
    回傳 JSON 陣列或空列表。
    """
    if state['data_source'] == 'volleyball':
        url, auth = 'http://163.13.201.90/video/actionget.php', ('feelwithus_vr','Fws_vr0000')
    else:
        url, auth = 'http://163.13.201.90/3d_video/actionget.php', ('feelwithus_iot','Fws_iot0000')
    try:
        resp = requests.get(url, auth=auth, params={'file_name': state['video_name']}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[DEBUG] fetch error: {e}")
        return []

def remove_duplicate_touch_times(data_list):
    """
    移除重複的 touch_time 項目，保留第一次出現的動作。
    """
    seen = set()
    result = []
    for item in data_list:
        t = item.get('touch_time')
        if t not in seen:
            seen.add(t)
            result.append(item)
    return result

def organize_buffer():
    """
    將 raw_buffer 中允許的動作過濾、按時間排序後，
    填入 organized_buffer，並標記資料已就緒。
    """
    organized_buffer.clear()
    candidates = [
        (float(item['touch_time']), item['action'])
        for item in raw_buffer
        if item.get('action') in ALLOWED_ACTIONS and item.get('touch_time') is not None
    ]
    candidates.sort(key=lambda x: x[0])
    organized_buffer.extend(candidates)
    state['data_ready'] = True
    print("[DEBUG] Data ready for sending (sorted):", organized_buffer)

def data_worker():
    """
    背景執行緒：持續從資料庫抓動作，
    去重後檢查是否出現 'end' 動作，
    若有則整理緩存並啟動 scheduled_sender。
    """
    while state['data_running']:
        actions = fetch_actions_from_db()
        if actions:
            raw_buffer.clear()
            raw_buffer.extend(remove_duplicate_touch_times(actions))
            if any(item.get('action') == 'end' for item in actions):
                organize_buffer()
                threading.Thread(target=scheduled_sender, daemon=True).start()
                break
        time.sleep(1)

def notify_frontend_end_action():
    """
    播放結束後通知前端 /api/end。
    """
    try:
        requests.post(FRONTEND_END_URL, json={
            "success": True, "status": "ended", "message": "All actions have been executed."
        }, timeout=5)
    except:
        pass

def scheduled_sender():
    """
    根據 organized_buffer 建立執行清單 exec_list：
    - 同類動作在 COOLDOWN 時間內累計計數，
      達到 4 次才列入執行清單。
    - 非累計動作立即列入。
    然後依據觸發時間計算延遲並透過 Serial 發送指令給 Arduino，
    碰到 'end' 動作結束並通知前端。
    """
    global current_index

    # 等待硬體開關打開
    while not state['switch_enabled']:
        time.sleep(0.1)

    exec_list = []
    last_time = -COOLDOWN
    count = 0

    # 建構最終執行清單
    for t, act in organized_buffer:
        # 冷卻期間內只累計
        if t - last_time < COOLDOWN:
            if act in {'運球', 'RECEIVE', 'SET', 'SERVE', 'BLOCK'}:
                count += 1
            continue

        # 冷卻結束後
        if act in {'運球', 'RECEIVE', 'SET', 'SERVE', 'BLOCK'}:
            count += 1
            if count >= 4:
                exec_list.append((t, act))
                count = 0
                last_time = t
        else:
            exec_list.append((t, act))
            last_time = t

    if not exec_list:
        state['data_running'] = False
        return

    # 開始執行事件
    state['data_running'] = True
    start_time = time.monotonic()
    event_times = [start_time + t for t, _ in exec_list]

    for idx, (touch_time, action) in enumerate(exec_list):
        # 計算並等待對應延遲
        delay = event_times[idx] - time.monotonic()
        if delay > 0:
            time.sleep(delay)

        # 發送指令到 Arduino
        payload = f"{action}:{touch_time}\n".encode()
        ser.write(payload); ser.flush()
        print(f"[DEBUG] Sent {action} at {touch_time}s")

        # 如果是結束動作，更新狀態並通知前端
        if action == 'end':
            state['ended'] = True
            state['data_running'] = False
            threading.Thread(target=notify_frontend_end_action, daemon=True).start()
            break

# ============ Flask API 路由 ============

@app.route('/api/db_start', methods=['POST'])
def db_start():
    """
    接收前端 /api/db_start 請求啟動動作抓取：
    - 解析影片名稱
    - 若已在執行相同影片則回傳 idempotent 成功
    - 否則重置狀態，啟動 data_worker 執行緒，
      並回傳初始去重摘要
    """
    body = request.get_json(silent=True) or {}
    video_name = body.get('videoName')
    if not video_name:
        return jsonify(success=False, message="videoName required"), 400

    # 已在執行且相同影片 => 回傳已存在狀態
    if state['data_running'] and state['video_name'] == video_name:
        return jsonify({
            "success": True,
            "status": "ok",
            "data": {
                "source": state['data_source'],
                "videoName": video_name,
                "running": True,
                "already": True
            }
        }), 200

    # 重置全域狀態並啟動資料工作執行緒
    state.update({
        'data_running': True,
        'data_source': pick_source_by_video(video_name),
        'video_name': video_name,
        'data_ready': False,
        'switch_enabled': False,
        'ended': False,
    })
    raw_buffer.clear()
    organized_buffer.clear()
    global current_index
    current_index = 0

    threading.Thread(target=data_worker, daemon=True).start()

    # 非阻塞地抓一次初始摘要並去重
    initial = remove_duplicate_touch_times(fetch_actions_from_db())
    summary = [{'touch_time': i.get('touch_time'), 'action': i.get('action')} for i in initial]

    return jsonify({
        "success": True,
        "status": "ok",
        "data": {
            "source": state['data_source'],
            "videoName": video_name,
            "running": True,
            "already": False,
            "data_fetched": summary
        }
    }), 200

@app.route('/api/switch', methods=['POST'])
def switch():
    """
    接收前端 /api/switch 請求設定硬體開關：
    - 讀取 JSON 參數 enabled 布林值
    - 更新 state['switch_enabled']，並透過 Serial 傳送 SWITCH_ON/OFF
    """
    try:
        data = request.get_json(force=True)
    except:
        return make_response('{"success":false,"message":"Invalid JSON"}', 400, {'Content-Type':'application/json'})
    enabled = data if isinstance(data, bool) else bool(data.get('enabled', False))
    state['switch_enabled'] = enabled
    print(f"[DEBUG] SWITCH {'ON' if enabled else 'OFF'}")
    cmd = b"SWITCH_ON\n" if enabled else b"SWITCH_OFF\n"
    ser.write(cmd); ser.flush()
    return make_response(f'{{"success":true,"switch":{str(enabled).lower()}}}', 200, {'Content-Type':'application/json'})

@app.route('/api/db_stop', methods=['POST'])
def stop():
    """
    接收前端 /api/db_stop 請求停止資料抓取與執行，
    重置 data_running 與 switch_enabled。
    """
    state['data_running'] = False
    state['switch_enabled'] = False
    return make_response('{"success":true,"status":"stopped"}', 200, {'Content-Type':'application/json'})

@app.route('/api/status', methods=['GET'])
def status():
    """
    回傳當前是否仍在抓取或執行動作（布林值）。
    """
    return jsonify(state['data_running']), 200

@app.route('/api/end', methods=['GET'])
def end_notify():
    """
    前端查詢播放是否已結束：
    - 若 state['ended'] 為 True，則回傳成功並重置旗標
    - 否則回傳尚未結束
    """
    if state.get('ended'):
        state['ended'] = False
        return jsonify(success=True, status="ended", message="All actions have been executed."), 200
    else:
        return jsonify(success=False, status="not_ended", message="Actions still in progress."), 200

if __name__ == '__main__':
    # 啟動 Flask 監聽 0.0.0.0:5002
    app.run(host='0.0.0.0', port=5002)
