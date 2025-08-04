
import cv2
import mediapipe as mp
import numpy as np
import math
import platform
import subprocess
import time

class HandVolumeControl:
    def __init__(self):
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize audio control based on OS
        self.setup_audio()
        
        # Volume control parameters
        self.min_distance = 30  # Minimum distance between thumb and index finger
        self.max_distance = 200  # Maximum distance between thumb and index finger
        
        # Smoothing parameters
        self.volume_smoothing = 0.8
        self.current_volume = 0.5
        self.last_volume_update = time.time()
        
        # Get current system info
        self.system = platform.system().lower()
        print(f"Detected OS: {self.system}")
        
    def setup_audio(self):
        """Setup audio control based on operating system"""
        self.system = platform.system().lower()
        
        if self.system == "windows":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume = cast(interface, POINTER(IAudioEndpointVolume))
                
                # Get volume range
                self.vol_range = self.volume.GetVolumeRange()
                self.min_vol = self.vol_range[0]
                self.max_vol = self.vol_range[1]
                
                print(f"Windows audio initialized. Volume range: {self.min_vol} to {self.max_vol}")
                self.audio_method = "windows"
            except Exception as e:
                print(f"Error initializing Windows audio: {e}")
                self.audio_method = "command"
        else:
            self.audio_method = "command"
            print(f"Using command-line audio control for {self.system}")
    
    def get_current_volume(self):
        """Get current system volume (0-100)"""
        try:
            if self.system == "linux":
                # Try PulseAudio first
                try:
                    result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'], 
                                          capture_output=True, text=True, check=True)
                    # Parse output like "Volume: front-left: 32768 /  50% / -18.06 dB"
                    volume_line = result.stdout.strip()
                    volume_percent = int(volume_line.split('/')[1].strip().replace('%', ''))
                    return volume_percent
                except:
                    # Fallback to ALSA
                    result = subprocess.run(['amixer', 'get', 'Master'], 
                                          capture_output=True, text=True, check=True)
                    # Parse ALSA output
                    for line in result.stdout.split('\n'):
                        if '[' in line and '%' in line:
                            start = line.find('[') + 1
                            end = line.find('%')
                            return int(line[start:end])
            
            elif self.system == "darwin":  # macOS
                result = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'], 
                                      capture_output=True, text=True, check=True)
                return int(result.stdout.strip())
            
            elif self.system == "windows":
                if hasattr(self, 'volume') and self.volume:
                    current_vol = self.volume.GetMasterVolumeLevel()
                    # Convert from dB to percentage
                    volume_percent = ((current_vol - self.min_vol) / (self.max_vol - self.min_vol)) * 100
                    return int(volume_percent)
        except Exception as e:
            print(f"Error getting volume: {e}")
        
        return 50  # Default fallback
    
    def set_system_volume(self, volume_level):
        """Set system volume (0-1 range)"""
        # Throttle volume updates to prevent system overload
        current_time = time.time()
        if current_time - self.last_volume_update < 0.1:  # Update max 10 times per second
            return
        
        self.last_volume_update = current_time
        volume_percent = int(volume_level * 100)
        
        try:
            if self.system == "linux":
                # Try PulseAudio first
                try:
                    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume_percent}%'], 
                                 check=True, capture_output=True)
                except:
                    # Fallback to ALSA
                    subprocess.run(['amixer', 'set', 'Master', f'{volume_percent}%'], 
                                 check=True, capture_output=True)
            
            elif self.system == "darwin":  # macOS
                subprocess.run(['osascript', '-e', f'set volume output volume {volume_percent}'], 
                             check=True, capture_output=True)
            
            elif self.system == "windows":
                if hasattr(self, 'volume') and self.volume:
                    # Map 0-1 to actual volume range
                    volume_db = self.min_vol + (volume_level * (self.max_vol - self.min_vol))
                    self.volume.SetMasterVolumeLevel(volume_db, None)
                else:
                    # Fallback for Windows without pycaw
                    subprocess.run(['nircmd.exe', 'setsysvolume', str(int(volume_level * 65535))], 
                                 check=False, capture_output=True)
        
        except Exception as e:
            print(f"Error setting volume: {e}")
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def map_distance_to_volume(self, distance):
        """Map finger distance to volume level (0-1)"""
        # Clamp distance to our defined range
        distance = max(self.min_distance, min(self.max_distance, distance))
        
        # Map to 0-1 range
        volume_level = (distance - self.min_distance) / (self.max_distance - self.min_distance)
        return volume_level
    
    def draw_volume_bar(self, img, volume_level, distance):
        """Draw volume visualization on the image"""
        # Volume bar dimensions
        bar_x, bar_y = 50, 50
        bar_width, bar_height = 300, 30
        
        # Draw background bar
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Draw volume level
        fill_width = int(bar_width * volume_level)
        color = (0, 255, 0) if volume_level > 0.3 else (0, 165, 255) if volume_level > 0.1 else (0, 0, 255)
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), color, -1)
        
        # Draw border
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
        
        # Add text
        volume_percent = int(volume_level * 100)
        cv2.putText(img, f'Volume: {volume_percent}%', (bar_x, bar_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add distance info
        cv2.putText(img, f'Distance: {int(distance)}px', (bar_x, bar_y + bar_height + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add OS info
        cv2.putText(img, f'OS: {self.system.title()}', (bar_x, bar_y + bar_height + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def draw_hand_landmarks(self, img, hand_landmarks):
        """Draw hand landmarks and connections"""
        # Draw all landmarks
        self.mp_draw.draw_landmarks(img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        
        # Get landmark positions
        h, w, c = img.shape
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        
        # Convert to pixel coordinates
        thumb_pos = (int(thumb_tip.x * w), int(thumb_tip.y * h))
        index_pos = (int(index_tip.x * w), int(index_tip.y * h))
        
        # Draw connection line between thumb and index finger
        cv2.line(img, thumb_pos, index_pos, (255, 0, 255), 3)
        
        # Draw circles on fingertips
        cv2.circle(img, thumb_pos, 10, (255, 0, 0), -1)  # Blue for thumb
        cv2.circle(img, index_pos, 10, (0, 255, 0), -1)  # Green for index
        
        return thumb_pos, index_pos
    
    def run(self):
        """Main application loop"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("Hand Volume Control Started!")
        print("Instructions:")
        print("- Show your hand to the camera")
        print("- Move thumb and index finger closer/farther to control volume")
        print("- Press 'q' to quit")
        print(f"- Audio method: {self.audio_method}")
        
        while True:
            success, img = cap.read()
            if not success:
                continue
            
            # Flip image horizontally for mirror effect
            img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Process hand landmarks
            results = self.hands.process(img_rgb)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw hand landmarks and get finger positions
                    thumb_pos, index_pos = self.draw_hand_landmarks(img, hand_landmarks)
                    
                    # Calculate distance between thumb and index finger
                    distance = self.calculate_distance(thumb_pos, index_pos)
                    
                    # Map distance to volume level
                    target_volume = self.map_distance_to_volume(distance)
                    
                    # Apply smoothing
                    self.current_volume = (self.volume_smoothing * self.current_volume + 
                                         (1 - self.volume_smoothing) * target_volume)
                    
                    # Set system volume
                    self.set_system_volume(self.current_volume)
                    
                    # Draw volume visualization
                    self.draw_volume_bar(img, self.current_volume, distance)
            else:
                # No hand detected
                cv2.putText(img, 'Show your hand to control volume', (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Add instructions
            cv2.putText(img, 'Press Q to quit', (50, img.shape[0] - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display the image
            cv2.imshow('Hand Volume Control', img)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    controller = HandVolumeControl()
    controller.run()
