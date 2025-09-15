import os
import cv2
from tqdm import tqdm
from typing import List
from pathlib import Path
from ultralytics import YOLO
from numpy.typing import NDArray
import traceback
import sys

from src.utilities.utils import BoundingBox, Meta, KeyPointBox

class ActionDetector:
    def __init__(self, cfg):
        try:
            #print(f"[DEBUG][__init__][{__file__}:{sys._getframe().f_lineno}] cfg: {cfg}")
            self.model = YOLO(cfg['weight'])
            self.labels = cfg['labels']
            self.labels2ids = {v: k for k, v in self.labels.items()}
            #print(f"[DEBUG][__init__][{__file__}:{sys._getframe().f_lineno}] labels2ids: {self.labels2ids}")
        except Exception as e:
            #print(f"[ERROR][__init__][{__file__}:{sys._getframe().f_lineno}] {e}")
            traceback.print_exc()
            raise

    def predict(self, inputs: NDArray, verbose=False, exclude=()) -> dict[str, List[BoundingBox]]:
        try:
            #print(f"[DEBUG][predict][{__file__}:{sys._getframe().f_lineno}] Input type: {type(inputs)}, Shape: {getattr(inputs, 'shape', None)}")
            detect_ids = {k: v for k, v in self.labels2ids.items() if k not in exclude}
            outputs = self.model.predict(inputs, verbose=verbose, classes=list(detect_ids.values()))
            #print(f"[DEBUG][predict][{__file__}:{sys._getframe().f_lineno}] YOLO outputs: {outputs}")

            confs = outputs[0].boxes.conf.cpu().detach().numpy().tolist()
            boxes = outputs[0].boxes.xyxy.cpu().detach().numpy().tolist()
            classes = outputs[0].boxes.cls.cpu().detach().numpy().astype(int).tolist()
            temp = {v: [] for v in self.labels.values()}
            for box, conf, cl in zip(boxes, confs, classes):
                name = self.labels[cl]
                b = BoundingBox(box, name=name, conf=float(conf))
                try:
                    temp[name].append(b)
                except KeyError:
                    temp[name] = [b]
            #print(f"[DEBUG][predict][{__file__}:{sys._getframe().f_lineno}] result dict keys: {list(temp.keys())}")
            return temp
        except Exception as e:
            #print(f"[ERROR][predict][{__file__}:{sys._getframe().f_lineno}] {e}")
            traceback.print_exc()
            raise

    def batch_predict(self, inputs: List[NDArray], verbose=False, exclude=()) -> List[dict[str, List[BoundingBox]]]:
        try:
            #print(f"[DEBUG][batch_predict][{__file__}:{sys._getframe().f_lineno}] Input type: {type(inputs)}, Length: {len(inputs)}")
            detect_ids = {k: v for k, v in self.labels2ids.items() if k not in exclude}
            outputs = self.model.predict(inputs, verbose=verbose, classes=list(detect_ids.values()))

            results = []
            for output in outputs:
                confs = output.boxes.conf.cpu().detach().numpy().tolist()
                boxes = output.boxes.xyxy.cpu().detach().numpy().tolist()
                classes = output.boxes.cls.cpu().detach().numpy().astype(int).tolist()
                temp = {v: [] for v in self.labels.values()}
                for box, conf, cl in zip(boxes, confs, classes):
                    name = self.labels[cl]
                    b = BoundingBox(box, name=name, conf=float(conf))
                    try:
                        temp[name].append(b)
                    except KeyError:
                        temp[name] = [b]
                results.append(temp)
            #print(f"[DEBUG][batch_predict][{__file__}:{sys._getframe().f_lineno}] results count: {len(results)}")
            return results
        except Exception as e:
            #print(f"[ERROR][batch_predict][{__file__}:{sys._getframe().f_lineno}] {e}")
            traceback.print_exc()
            raise

    @staticmethod
    def extract_classes(bboxes: List[BoundingBox], item: str) -> List[BoundingBox]:
        try:
            #print(f"[DEBUG][extract_classes][{__file__}:{sys._getframe().f_lineno}] item: {item}, bboxes count: {len(bboxes)}")
            return [bbox for bbox in bboxes if bbox.name == item]
        except Exception as e:
            #print(f"[ERROR][extract_classes][{__file__}:{sys._getframe().f_lineno}] {e}")
            traceback.print_exc()
            raise

    def draw(self, frame: NDArray, items: List[BoundingBox | KeyPointBox]):
        try:
            #print(f"[DEBUG][draw][{__file__}:{sys._getframe().f_lineno}] type(self): {type(self)}, type(items): {type(items)}, items length: {len(items)}")
            for i, bb in enumerate(items):
                #print(f"  [DEBUG][draw][{__file__}:{sys._getframe().f_lineno}] Drawing item {i}: name={getattr(bb, 'name', None)}, type={type(bb)}")
                match bb.name:
                    case "spike":
                        frame = bb.supervision_plot(frame, color=Meta.bgr_orange, plot_type="box", use_label=True)
                    case "set":
                        frame = bb.supervision_plot(frame, color=Meta.bgr_aqua, plot_type="box", use_label=True)
                    case "receive":
                        frame = bb.supervision_plot(frame, color=Meta.green, plot_type="box", use_label=True)
                    case "block":
                        frame = bb.supervision_plot(frame, color=Meta.bgr_purple, plot_type="box", use_label=True)
                    case "serve":
                        frame = bb.supervision_plot(frame, color=Meta.bgr_brown, plot_type="box", use_label=True)
                    case "ball":
                        frame = bb.supervision_plot(frame, color=Meta.bgr_red, plot_type="box", use_label=True)
            return frame
        except Exception as e:
            #print(f"[ERROR][draw][{__file__}:{sys._getframe().f_lineno}] {e}")
            traceback.print_exc()
            raise

if __name__ == '__main__':
    video = 'data/raw/videos/test/videos/11_short.mp4'
    output = 'runs/inference/det'
    os.makedirs(output, exist_ok=True)
    cfg = {
        'weight': 'weights/vb_actions_6_class/model1/weights/best.pt',
        "labels": {0: 'spike', 1: 'block', 2: 'receive', 3: 'set'}
    }

    #print(f"[DEBUG][main][{__file__}:{sys._getframe().f_lineno}] Initializing ActionDetector...")
    action_detector = ActionDetector(cfg=cfg)
    cap = cv2.VideoCapture(video)
    assert cap.isOpened()

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_file = Path(output) / (Path(video).stem + '_output.mp4')
    writer = cv2.VideoWriter(output_file.as_posix(), fourcc, fps, (w, h))

    for fno in tqdm(range(n_frames)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
        status, frame = cap.read()
        if not status:
            #print(f"[DEBUG][main][{__file__}:{sys._getframe().f_lineno}] Frame {fno}: frame read failed!")
            continue
        try:
            pred_dict = action_detector.predict(frame)
            all_bboxes = []
            for v in pred_dict.values():
                all_bboxes.extend(v)
            #print(f"[DEBUG][main][{__file__}:{sys._getframe().f_lineno}] Frame {fno}: total bboxes to draw: {len(all_bboxes)}")
            frame = action_detector.draw(frame, all_bboxes)
            writer.write(frame)
        except Exception as e:
            #print(f"[ERROR][main][{__file__}:{sys._getframe().f_lineno}] Error at frame {fno}: {e}")
            traceback.print_exc()
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f'saved results in {output_file}')
