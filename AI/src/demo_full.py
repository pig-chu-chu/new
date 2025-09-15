import sys, cv2, yaml, torch, pytesseract, easyocr
import numpy as np
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm
from collections import defaultdict, deque
from PIL import Image
from ultralytics import YOLO
import mediapipe as mp
from math import hypot
import paramiko
import os
import mysql.connector
from flask import Flask, request, jsonify, send_file
import io
import warnings
from threading import Lock

warnings.filterwarnings("ignore", category=UserWarning)
torch.backends.cudnn.benchmark = True

# volleyball_analytics imports
from src.utilities.utils import ProjectLogger
from src.ml.video_mae.game_state.gamestate_detection import GameStateDetector
from src.ml.yolo.volleyball_object_detector import VolleyBallObjectDetector
from boxmot.trackers.strongsort.strongsort import StrongSort
sys.path.append(r"C:\\Users\\B310-25\\volleyball_analytics - 複製\\jersey-number-pipeline")
from strhub.data.module import SceneTextDataModule

reader = easyocr.Reader(['en'])
device = "cuda:0" if torch.cuda.is_available() else "cpu"
parseq_repo = r"C:\\Users\\B310-25\\volleyball_analytics - 複製\\jersey-number-pipeline\\parseq"
parseq = torch.hub.load(parseq_repo, "parseq", pretrained=True, source="local", trust_repo=True).eval().to(device)
img_transform = SceneTextDataModule.get_transform(parseq.hparams.img_size)
pose_detector = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=0)

ALPHA, BETA = 1.1, 8
MIN_BBOX_AREA = 400
CHECK_INTERVAL, FAIL_TOLERANCE = 5, 2
VOTE_WINDOW = 7
REID_THRESHOLD = 0.7
BALL_DIST = 50
TRUST_MAX = 10
TRUST_MIN = -5
distance_thresh = 120

app = Flask(__name__)

first_frame_bytes = None
current_roi = None
current_jersey = None
last_ocr_result = None
analysis_running = False
analysis_lock = Lock()
logger = ProjectLogger("logs.log")

video_path_global = "downloaded_segments/p3-1756316608.flv"
output_path_global = "runs/DEMO/output_DEMO.mp4"

def connect_db():
    return mysql.connector.connect(
        host="163.13.201.90",
        user="feelwithus_ai",
        password="Fws_ai0000",
        database="ai_iot",
        charset='utf8mb4'
    )

def ocr_number(crop):
    if crop is None or crop.size == 0:
        return None
    try:
        roi = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        inp = img_transform(roi).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = parseq(inp)
            lbl, _ = parseq.tokenizer.decode(logits.softmax(-1))
            if lbl and lbl.isdigit():
                return lbl
    except:
        pass
    res = reader.readtext(crop)
    for _, t, conf in res:
        if conf > 0.5 and t.strip().isdigit():
            return t.strip()
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    txt = pytesseract.image_to_string(
        gray, config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()
    return txt if txt.isdigit() else None

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    if interArea == 0:
        return 0.0
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return interArea / float(boxAArea + boxBArea - interArea)

def get_reid_feature(tracker, crop):
    if crop is None or crop.size == 0:
        return None
    im = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    im = cv2.resize(im, (128, 256))
    im = torch.from_numpy(im).permute(2, 0, 1).unsqueeze(0).float().to(device) / 255.0
    with torch.no_grad():
        if hasattr(tracker.model, "model"):
            feat = tracker.model.model(im)
        elif hasattr(tracker.model, "extract_features"):
            feat = tracker.model.extract_features(im)
        else:
            raise AttributeError("ReID model not found")
    return feat.cpu().numpy().flatten()

def format_time(ms):
    s = int(ms / 1000)
    return f"{s//60}:{s%60:02d}"

def enlarge_bbox_with_pose(frame, bbox, pose_detector):
    x1, y1, x2, y2 = bbox
    h_frame, w_frame = frame.shape[:2]
    x1 = max(0, min(w_frame - 1, x1))
    x2 = max(0, min(w_frame - 1, x2))
    y1 = max(0, min(h_frame - 1, y1))
    y2 = max(0, min(h_frame - 1, y2))
    if x2 <= x1 or y2 <= y1:
        return bbox
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return bbox
    rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    results = pose_detector.process(rgb_crop)
    if not results.pose_landmarks:
        return bbox
    h, w = crop.shape[:2]
    xs = [int(lm.x * w) for lm in results.pose_landmarks.landmark]
    ys = [int(lm.y * h) for lm in results.pose_landmarks.landmark]
    min_x = max(0, min(xs))
    max_x = min(w - 1, max(xs))
    min_y = max(0, min(ys))
    max_y = min(h - 1, max(ys))
    margin_x = int(0.5 * (max_x - min_x))
    margin_y = int(0.35 * (max_y - min_y))
    new_x1 = max(0, x1 + min_x - margin_x)
    new_y1 = max(0, y1 + min_y - margin_y)
    new_x2 = min(w_frame - 1, x1 + max_x + margin_x)
    new_y2 = min(h_frame - 1, y1 + max_y + margin_y)
    return (new_x1, new_y1, new_x2, new_y2)

def box_center(box):
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)

@app.route('/start', methods=['POST'])
def start():
    global first_frame_bytes, current_roi, current_jersey, last_ocr_result
    cap = cv2.VideoCapture(video_path_global)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": "read video failed"}), 500
    _, jpeg = cv2.imencode('.jpg', frame)
    first_frame_bytes = jpeg.tobytes()
    current_roi = None
    current_jersey = None
    last_ocr_result = None
    return jsonify({"message": "started, first frame ready"})

@app.route('/get_first_frame', methods=['GET'])
def get_first_frame():
    if first_frame_bytes is None:
        return jsonify({"error": "frame not ready"}), 503
    return send_file(io.BytesIO(first_frame_bytes), mimetype='image/jpeg')

@app.route('/submit_roi', methods=['POST'])
def submit_roi():
    global current_roi, last_ocr_result
    data = request.json
    current_roi = data.get("roi")
    if not isinstance(current_roi, list) or len(current_roi) != 4:
        return jsonify({"error": "invalid ROI"}), 400
    cap = cv2.VideoCapture(video_path_global)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": "read video failed"}), 500
    x, y, w_roi, h_roi = map(int, current_roi)
    roi_crop = frame[y:y + h_roi, x:x + w_roi]
    ocr_res = ocr_number(roi_crop)
    last_ocr_result = ocr_res if ocr_res else None
    return jsonify({"message": "ROI received", "ocr": last_ocr_result})

@app.route('/submit_jersey', methods=['POST'])
def submit_jersey():
    global current_jersey
    data = request.json
    jersey = data.get("jersey")
    if not jersey:
        return jsonify({"error": "jersey required"}), 400
    current_jersey = str(jersey).strip()
    return jsonify({"message": "jersey confirmed"})

@app.route('/run_analysis', methods=['POST'])
def run_analysis():
    global analysis_running
    with analysis_lock:
        if analysis_running:
            return jsonify({"error": "Analysis already running"}), 409
        if current_roi is None or current_jersey is None:
            return jsonify({"error": "ROI and jersey must be submitted first"}), 400
        analysis_running = True

    try:
        start_analysis(video_path_global, output_path_global, current_roi, current_jersey)
    except Exception as e:
        with analysis_lock:
            analysis_running = False
        return jsonify({"error": f"analysis failed: {e}"}), 500

    with analysis_lock:
        analysis_running = False
    return jsonify({"message": "analysis complete"})

@app.route('/analysis_status', methods=['GET'])
def analysis_status():
    status = "running" if analysis_running else "idle"
    return jsonify({"status": status})

def start_analysis(video_path, output_path, baseline_roi=None, baseline_jersey=None):
    parser = ArgumentParser()
    parser.add_argument("--model_cfg", default="conf/ml_models.yaml")
    parser.add_argument("--setup_cfg", default="conf/setup.yaml")
    parser.add_argument("--reid_weights", default="weights/osnet_x0_25_msmt17.pt")
    parser.add_argument("--jersey_numbers", nargs="+", type=int, required=False, default=[])
    args = parser.parse_args([])

    logger = ProjectLogger("logs.log")

    with open(args.model_cfg) as f:
        model_cfg = yaml.safe_load(f)
    with open(args.setup_cfg) as f:
        setup_cfg_data = yaml.safe_load(f)
    model_cfg.update(setup_cfg_data)

    gs_detector = GameStateDetector(cfg=model_cfg["video_mae"]["game_state_3"])
    vb_detector = VolleyBallObjectDetector(model_cfg, use_player_detection=True, video_name=Path(video_path).name)
    yolo_person = YOLO(model_cfg["yolo"]["player_detection"]["weight"])
    tracker = StrongSort(Path(args.reid_weights), device=device, half=False)

    cap = cv2.VideoCapture(str(video_path))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps, nf = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    pbar = tqdm(total=nf, disable=False)

    ret, ff = cap.read()
    ff = cv2.convertScaleAbs(ff, alpha=ALPHA, beta=BETA)

    if baseline_roi is None or baseline_jersey is None:
        raise RuntimeError("Require baseline ROI and jersey for analysis")

    x, y, w_roi, h_roi = map(int, baseline_roi)
    crop = ff[y:y + h_roi, x:x + w_roi]
    baseline_jersey_val = baseline_jersey
    logger.info(f"Baseline Jersey: {baseline_jersey_val}")

    db_conn = connect_db()
    db_cursor = db_conn.cursor()
    sql = "INSERT INTO messages (jersey_number, content) VALUES (%s, %s)"
    db_cursor.execute(sql, (-1, Path(video_path).name))
    db_conn.commit()

    baseline_feat = get_reid_feature(tracker, crop)
    opencv_tracker = cv2.TrackerCSRT_create()
    opencv_tracker.init(ff, (x, y, w_roi, h_roi))

    frame_idx = 0
    mismatch = 0
    votes = defaultdict(lambda: deque(maxlen=VOTE_WINDOW))
    trust_score = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            frame = cv2.convertScaleAbs(frame, alpha=ALPHA, beta=BETA)

            g = gs_detector.predict([frame])
            cv2.putText(frame, f"GameState:{gs_detector.state2label[g]}", (40, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            ok, bbox = opencv_tracker.update(frame)

            if ok:
                x, y, w_box, h_box = map(int, bbox)
                normal_player_box = (x, y, x + w_box, y + h_box)
                player_box = enlarge_bbox_with_pose(frame, normal_player_box, pose_detector)
                cv2.rectangle(frame, (player_box[0], player_box[1]), (player_box[2], player_box[3]), (0, 0, 255), 2)

                if frame_idx % CHECK_INTERVAL == 0:
                    crop = frame[player_box[1]:player_box[3], player_box[0]:player_box[2]]
                    num = ocr_number(crop)
                    reid_feat = get_reid_feature(tracker, crop) if crop is not None else None
                    dist = np.linalg.norm(reid_feat - baseline_feat) if reid_feat is not None else 999

                    if num == baseline_jersey_val:
                        trust_score = min(TRUST_MAX, trust_score + 2)
                        mismatch = 0
                        if reid_feat is not None:
                            baseline_feat = 0.9 * baseline_feat + 0.1 * reid_feat
                    elif num is None:
                        if dist < REID_THRESHOLD:
                            trust_score = min(TRUST_MAX, trust_score + 1)
                            mismatch = 0
                        else:
                            trust_score -= 1
                            mismatch += 1
                    else:
                        if dist < REID_THRESHOLD:
                            trust_score -= 1
                        else:
                            trust_score -= 2
                            mismatch += 1

                    if trust_score < TRUST_MIN or mismatch >= FAIL_TOLERANCE:
                        ok = False
                        mismatch = 0
                        trust_score = 0

            if not ok:
                det = yolo_person.predict(frame, conf=0.25, iou=0.5, classes=0, verbose=False)[0]
                bb = []
                for (x1, y1, x2, y2), conf in zip(det.boxes.xyxy.cpu().numpy(), det.boxes.conf.cpu().numpy()):
                    if (x2 - x1) * (y2 - y1) < MIN_BBOX_AREA:
                        continue
                    bb.append([int(x1), int(y1), int(x2), int(y2), float(conf), 0])
                tracks = tracker.update(np.array(bb), frame)
                best = None
                method = None
                best_score = 999
                for t in tracks:
                    x1, y1, x2, y2, tid = map(int, t[:5])
                    crop = frame[y1:y2, x1:x2]
                    num = ocr_number(crop)
                    votes[tid].append(num if num else "-")
                    hist = list(votes[tid])
                    most = max(set(hist), key=hist.count) if hist else "-"
                    if most == baseline_jersey_val:
                        best = (x1, y1, x2, y2)
                        method = "OCR-vote"
                        break
                    if num == baseline_jersey_val:
                        best = (x1, y1, x2, y2)
                        method = "OCR-exact"
                        break
                    if baseline_feat is not None and crop.size != 0:
                        feat = get_reid_feature(tracker, crop)
                        if feat is not None:
                            dist = np.linalg.norm(feat - baseline_feat)
                            if dist < best_score:
                                best_score = dist
                                best = (x1, y1, x2, y2)
                                method = "ReID"

                if best and (method.startswith("OCR") or best_score < REID_THRESHOLD):
                    opencv_tracker = cv2.TrackerCSRT_create()
                    opencv_tracker.init(frame, (best[0], best[1], best[2] - best[0], best[3] - best[1]))
                    ok = True
                    trust_score = 5

            best_act = None
            if ok:
                bx1, by1, bx2, by2 = player_box
                vb_objects_by_action = vb_detector.detect_actions(frame, exclude=("ball",))
                all_action_objs = []
                for act_label, acts in vb_objects_by_action.items():
                    acts = acts if isinstance(acts, list) else [acts]
                    for act in acts:
                        act.label = act_label
                        all_action_objs.append(act)
                balls = vb_detector.detect_balls(frame)
                ball_ok = False
                for bl in balls:
                    bx_ball, by_ball = (bl.x1 + bl.x2) / 2, (bl.y1 + bl.y2) / 2
                    if (bx1 - BALL_DIST) < bx_ball < (bx2 + BALL_DIST) and (by1 - BALL_DIST) < by_ball < (by2 + BALL_DIST):
                        ball_ok = True
                        break
                ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                time_str = format_time(ms)
                for act_obj in all_action_objs:
                    act_box = (int(act_obj.x1), int(act_obj.y1), int(act_obj.x2), int(act_obj.y2))
                    iou_val = iou(player_box, act_box)
                    conf = getattr(act_obj, "conf", 1.0)
                    skeleton_ok = False
                    p_cx, p_cy = box_center(player_box)
                    a_cx, a_cy = box_center(act_box)
                    center_dist = hypot(p_cx - a_cx, p_cy - a_cy)
                    assign = False
                    reason = []
                    if conf > 0.15 and (iou_val > 0.15 or center_dist < distance_thresh):
                        if iou_val > 0.03:
                            reason.append("IoU")
                        else:
                            reason.append("BOX_CENTER")
                        if skeleton_ok:
                            reason.append("Skeleton")
                        if ball_ok:
                            reason.append("Ball")
                        assign = True
                    # 這行印出逐幀動作判斷資訊
                    print(f"[Frame {frame_idx} | {time_str}] cand={act_obj.label.upper()} "
                          f"IoU={iou_val:.2f} conf={conf:.2f} dist={center_dist:.1f} "
                          f"skeleton={skeleton_ok} ball={ball_ok} assign={assign} reason={reason}")
                    if assign:
                        best_act = act_obj.label.upper()
                        sec = int(ms / 1000)
                        sql = "INSERT INTO messages (jersey_number, content) VALUES (%s, %s)"
                        db_cursor.execute(sql, (str(sec), best_act))
                        db_conn.commit()
                        break
                label = f"#{baseline_jersey_val}"
                if best_act:
                    label += f" {best_act}"
                cv2.putText(frame, label, (bx1, max(by1 - 20, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3, cv2.LINE_AA)
            writer.write(frame)
            pbar.update(1)

    finally:
        sql = "INSERT INTO messages (jersey_number, content) VALUES (%s, %s)"
        db_cursor.execute(sql, (-1, "辨識完成"))
        db_conn.commit()
        cap.release()
        writer.release()
        pbar.close()
        db_cursor.close()
        db_conn.close()

if __name__ == '__main__':
    print("API service started on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
