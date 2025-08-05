import cv2
import mediapipe as mp
import math
import os
import subprocess

# Set environment
os.environ['QT_QPA_PLATFORM'] = 'xcb'

def change_volume(vol):
    """Change system volume"""
    try:
        subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{vol}%'], 
                      capture_output=True, timeout=1)
    except:
        pass

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hand_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Initialize camera
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Cannot open camera")
    exit()

# Variables
volume_level = 50
locked_state = False
lock_counter = 0
volume_list = []

print("Minimal Hand Volume Control Started!")
print("- Volume: Thumb-Index distance")
print("- Lock: Touch Index-Middle fingers")
print("- Press 'q' to quit")

while True:
    success, image = camera.read()
    if not success:
        break
    
    # Flip image
    image = cv2.flip(image, 1)
    height, width, channels = image.shape
    
    # Convert to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    hand_results = hand_detector.process(rgb_image)
    
    if hand_results.multi_hand_landmarks:
        for hand_marks in hand_results.multi_hand_landmarks:
            # Draw hand
            mp_draw.draw_landmarks(image, hand_marks, mp_hands.HAND_CONNECTIONS)
            
            # Get finger positions
            thumb_point = hand_marks.landmark[4]  # THUMB_TIP
            index_point = hand_marks.landmark[8]  # INDEX_TIP
            middle_point = hand_marks.landmark[12]  # MIDDLE_TIP
            
            # Convert to pixels
            thumb_px = int(thumb_point.x * width)
            thumb_py = int(thumb_point.y * height)
            index_px = int(index_point.x * width)
            index_py = int(index_point.y * height)
            middle_px = int(middle_point.x * width)
            middle_py = int(middle_point.y * height)
            
            # Calculate distances
            thumb_index_distance = math.sqrt((thumb_px - index_px)**2 + (thumb_py - index_py)**2)
            index_middle_distance = math.sqrt((index_point.x - middle_point.x)**2 + (index_point.y - middle_point.y)**2)
            
            # Check if fingers are close (lock detection)
            fingers_close = index_middle_distance < 0.04
            
            # Update lock state
            if fingers_close:
                lock_counter += 1
            else:
                lock_counter = max(0, lock_counter - 1)
            
            locked_state = lock_counter > 3
            
            # Calculate volume if not locked
            if not locked_state:
                # Map distance to volume (30-200 pixels -> 0-100%)
                if thumb_index_distance < 30:
                    target_vol = 0
                elif thumb_index_distance > 200:
                    target_vol = 100
                else:
                    target_vol = int(((thumb_index_distance - 30) / 170) * 100)
                
                # Smooth volume
                volume_list.append(target_vol)
                if len(volume_list) > 3:
                    volume_list.pop(0)
                
                volume_level = int(sum(volume_list) / len(volume_list))
                change_volume(volume_level)
            
            # Draw circles
            cv2.circle(image, (thumb_px, thumb_py), 15, (255, 0, 0), -1)  # Blue thumb
            cv2.circle(image, (index_px, index_py), 15, (0, 0, 255) if locked_state else (0, 255, 0), -1)
            cv2.circle(image, (middle_px, middle_py), 12, (255, 0, 0) if fingers_close else (255, 255, 255), -1)
            
            # Draw lines
            cv2.line(image, (thumb_px, thumb_py), (index_px, index_py), 
                    (0, 0, 255) if locked_state else (0, 255, 0), 4)
            cv2.line(image, (index_px, index_py), (middle_px, middle_py), 
                    (255, 0, 0) if fingers_close else (200, 200, 200), 2)
            
            # Labels
            cv2.putText(image, "T", (thumb_px-8, thumb_py-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.putText(image, "I", (index_px-8, index_py-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.putText(image, "M", (middle_px-8, middle_py-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
    
    # Draw volume bar
    bar_x = width - 320
    bar_y = 50
    bar_width = 300
    bar_height = 25
    
    # Background
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (60, 60, 60), -1)
    
    # Volume fill
    fill_width = int((volume_level / 100) * bar_width)
    bar_color = (0, 0, 255) if locked_state else (0, 255, 0)
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), bar_color, -1)
    
    # Text
    lock_text = " [LOCKED]" if locked_state else ""
    cv2.putText(image, f"Volume: {volume_level}%{lock_text}", (bar_x, bar_y-10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Status
    status_text = "LOCKED" if locked_state else "ACTIVE"
    status_color = (0, 0, 255) if locked_state else (0, 255, 0)
    cv2.putText(image, f"Status: {status_text}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    
    # Instructions
    cv2.putText(image, "Volume: Thumb-Index | Lock: Index-Middle touch", 
               (20, height-50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(image, "Press 'q' to quit", (20, height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Show image
    cv2.imshow('Minimal Hand Volume Control', image)
    
    # Check for quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
camera.release()
cv2.destroyAllWindows()
print("Hand Volume Control stopped")
