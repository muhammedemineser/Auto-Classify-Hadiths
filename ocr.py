import time
import threading
from concurrent.futures import ThreadPoolExecutor
import mss
import numpy as np

CAPTURE_INTERVAL = 1.0
MAX_THREADS = 4


class OCRWatcher:
    def __init__(self, x1, y1, x2, y2):
        self.rect = {
            "top": y1,
            "left": x1,
            "width": x2 - x1,
            "height": y2 - y1,
        }
        self.sequence = 0
        self.prev_img = None
        self.lock = threading.Lock()

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

            return self.sequence >= 10

    def run(self):
        with mss.mss() as sct, ThreadPoolExecutor(max_workers=MAX_THREADS):
            while True:
                start = time.time()
                curr_img = self.capture(sct)
                self.process_frame(curr_img)
                elapsed = time.time() - start
                time.sleep(max(0.0, CAPTURE_INTERVAL - elapsed))


if __name__ == "__main__":
    watcher_a = OCRWatcher(17, 146, 712, 842)
    watcher_b = OCRWatcher(38, 2, 83, 35)
