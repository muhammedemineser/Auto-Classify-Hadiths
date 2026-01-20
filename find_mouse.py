import pyautogui
import time

print("Bewege deine Maus zum Ziel. In 5 Sekunden wird die Position gespeichert...")
time.sleep(5)
x, y = pyautogui.position()
print(f"Position gefunden: x={x}, y={y}")
