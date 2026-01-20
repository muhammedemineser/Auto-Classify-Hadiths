# ocr.py
import time
import threading
import mss
import numpy as np

CAPTURE_INTERVAL = 1.0


class OCRWatcher:
    def __init__(self, x1, y1, x2, y2, name="watcher"):
        self.rect = {
            "top": y1,
            "left": x1,
            "width": x2 - x1,
            "height": y2 - y1,
        }
        self.sequence = 0
        self.prev_img = None
        self.lock = threading.Lock()
        self.name = name

    def capture(self, sct):
        return np.array(sct.grab(self.rect), copy=False)

    def process_frame(self, curr_img):
        with self.lock:
            if self.prev_img is None:
                self.prev_img = curr_img
                self.sequence = 0
                return False

            if np.array_equal(curr_img, self.prev_img):
                self.sequence += 1
            else:
                self.prev_img = curr_img
                self.sequence = 0

            return self.sequence >= 5

    def run(self):
        with mss.mss() as sct:
            while True:
                start = time.time()

                curr_img = self.capture(sct)
                if self.process_frame(curr_img):
                    return True

                elapsed = time.time() - start
                time.sleep(max(0.0, CAPTURE_INTERVAL - elapsed))
