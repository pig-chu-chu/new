import numpy as np
import yaml
import json
from numpy.typing import NDArray
from yaml.loader import SafeLoader
from typing import List

from src.utilities.utils import BoundingBox
from .ball import BallSegmentor
from .vb_action import ActionDetector
from .players import PlayerSegmentor, PlayerDetector, PoseEstimator

class VolleyBallObjectDetector:
    def __init__(self, config: dict, video_name: str = None, use_player_detection=True):
        self.config = config
        court_dict = None

        # 嘗試讀取 court_json，並取得對應 video_name 的 court_dict
        court_json_path = self.config.get('court_json')
        if court_json_path and video_name is not None:
            try:
                with open(court_json_path, 'r', encoding='utf-8') as f:
                    court_json = json.load(f)
                court_dict = court_json.get(video_name, None)
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
                court_dict = None

        # 初始化 player_detector
        if use_player_detection:
            self.player_detector = PlayerDetector(self.config['yolo']['player_detection'], court_dict=court_dict)
        else:
            self.player_detector = PlayerSegmentor(self.config['yolo']['player_segmentation'], court_dict=court_dict)

        # 其他 detector 初始化（確保是實例化）
        # DEBUG: 強制檢查 action_detection6 config
        action_cfg = self.config.get('yolo', {}).get('action_detection6', {})
        if not action_cfg:
            raise ValueError("[ERROR] action_detection6 config is missing in self.config['yolo']")
        print("[DEBUG] ActionDetector init config:", action_cfg)
        self.action_detector = ActionDetector(action_cfg)
        print("[DEBUG] self.action_detector type:", type(self.action_detector))

        self.ball_detector = BallSegmentor(self.config['yolo']['ball_segmentation'])
        self.pose_estimator = PoseEstimator(self.config['yolo']['pose_estimation'])

    def detect_balls(self, inputs: NDArray | List[NDArray]):
        if isinstance(inputs, np.ndarray):
            return self.ball_detector.predict(inputs=inputs)
        return self.ball_detector.batch_predict(inputs=inputs)

    def detect_actions(self, inputs: NDArray | List[NDArray], exclude=None):
        if isinstance(inputs, np.ndarray):
            return self.action_detector.predict(inputs=inputs, exclude=exclude)
        return self.action_detector.batch_predict(inputs=inputs, exclude=exclude)

    def detect_keypoints(self, inputs: NDArray | List[NDArray]):
        if isinstance(inputs, np.ndarray):
            return self.pose_estimator.predict(inputs=inputs)
        return self.pose_estimator.batch_predict(inputs=inputs)

    def segment_players(self, inputs: NDArray | List[NDArray]):
        return self.player_detector.predict(frame=inputs)

    def extract_objects(self, bboxes: List[BoundingBox], item: str = 'ball'):
        return self.action_detector.extract_classes(bboxes=bboxes, item=item)

    def draw_bboxes(self, image, bboxes):
        print("[DEBUG] draw_bboxes: type(self.action_detector):", type(self.action_detector))
        print("[DEBUG] draw_bboxes: is instance:", isinstance(self.action_detector, ActionDetector))
        image = self.action_detector.draw(frame=image, items=bboxes)
        return image
