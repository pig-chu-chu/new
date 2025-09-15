import numpy as np
def get_jersey_roi(img, keypoints, scale_w=1.6, scale_h=1.4):
    """
    Extract jersey ROI given keypoints (ViTPose: 5左肩,6右肩,11左髖,12右髖)
    """
    xs = [keypoints[5][0], keypoints[6][0], keypoints[11][0], keypoints[12][0]]
    ys = [keypoints[5][1], keypoints[6][1], keypoints[11][1], keypoints[12][1]]
    x_c = int(np.mean(xs))
    y_c = int(np.mean(ys))
    box_w = int((max(xs)-min(xs)) * scale_w)
    box_h = int((max(ys)-min(ys)) * scale_h)
    x1 = max(0, x_c - box_w // 2)
    x2 = min(img.shape[1], x_c + box_w // 2)
    y1 = max(0, y_c - box_h // 2)
    y2 = min(img.shape[0], y_c + box_h // 2)
    return img[y1:y2, x1:x2]
