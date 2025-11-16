# laptop_crack_detector.py
import cv2
import numpy as np
import tensorflow as tf
import socket
import time
import os

# ---------------- MODEL ----------------
# The model loading is kept outside the main loop since it only needs to be loaded once.
try:
    print("[INFO] Loading model...")
    model = tf.keras.models.load_model("crack_detection.h5")
    print("[INFO] Model loaded successfully.")
except Exception as e:
    print(f"[ERROR] Could not load model 'crack_detection.h5': {e}")
    exit()

# ---------------- CONNECTION CONFIG ----------------
RASPBERRY_PI_IP = "ENTER YOUR RASPBERRY PI IP"
PORT = 5000

# Global socket variable
client_socket = None

def connect_to_pi():
    """Establishes the socket connection to the Raspberry Pi."""
    global client_socket
    if client_socket:
        client_socket.close()
        client_socket = None
        
    print("[INFO] Connecting to Raspberry Pi...")
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((RASPBERRY_PI_IP, PORT))
        print("[INFO] Connected successfully!")
        return True
    except ConnectionRefusedError:
        print(f"❌ Connection Refused! Ensure the server on Pi is running at {RASPBERRY_PI_IP}:{PORT}")
        client_socket = None
        return False
    except socket.timeout:
        print(f"❌ Connection Timeout! Could not reach Pi at {RASPBERRY_PI_IP}:{PORT}")
        client_socket = None
        return False
    except Exception as e:
        print(f"❌ An error occurred during connection: {e}")
        client_socket = None
        return False

# Establish connection once at startup
connection_status = connect_to_pi()

# ---------------- PREDICTION FUNCTION ----------------
def process_frame(frame):
    """Preprocess frame, run prediction, display result, and send message."""
    
    # 1. Preprocessing and Prediction
    img = cv2.resize(frame, (227, 227))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img, verbose=0)[0][0]
    label = "Crack Detected" if pred > 0.5 else "Safe"
    color = (0, 0, 255) if pred > 0.5 else (0, 255, 0)

    # 2. Display Result
    cv2.putText(frame, f"{label} ({pred:.2f})", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    # 3. Send Message to Raspberry Pi (Only if connected)
    if client_socket and connection_status:
        message = "DANGER" if pred > 0.5 else "SAFE"
        try:
            client_socket.send(message.encode())
        except Exception as e:
            # Handle disconnection during runtime
            print("⚠ [Socket Error during send]", e)
            print("⚠ Lost connection to Raspberry Pi.")

    cv2.imshow("Crack Detection", frame)
    return label

# ---------------- INTERACTIVE MAIN LOOP ----------------

def run_prediction_session(source):
    """Handles the prediction for a single image, video, or webcam feed."""
    
    if isinstance(source, str) and os.path.isfile(source) and source.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        # --- Handle Single Image ---
        print(f"[INFO] Processing image file: {source}...")
        frame = cv2.imread(source)
        if frame is None:
            print(f"❌ Error: Could not load image file {source}.")
            return
            
        process_frame(frame)
        print("[INFO] Image processed. Close the window to continue.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    else:
        # --- Handle Video/Webcam Feed ---
        print(f"[INFO] Starting video/webcam feed ({source}). Press 'q' to quit.")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"❌ Could not open video source: {source}.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] End of video stream.")
                break

            process_frame(frame)
            
            # Use cv2.waitKey(1) for a video loop to be responsive
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] 'Q' pressed — stopping prediction...")
                break

            time.sleep(0.3)  # smooth processing

        cap.release()
        cv2.destroyAllWindows()

# --- Main Program Flow ---
if __name__ == "__main__":
    
    # Initial source, can be changed by the user
    current_source = "po.webp"  # Default

    try:
        while True:
            print("\n" + "="*40)
            print(f"Current Source: **{current_source}**")
            print(f"Pi Connection: **{'ACTIVE' if client_socket else 'INACTIVE'}**")
            print("--- Main Menu ---")
            print("1: Start Prediction (using current source)")
            print("2: Change Input Source (Image/Video/Webcam)")
            print("3: Reconnect to Raspberry Pi")
            print("4: Exit")
            print("="*40)

            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                # Start Prediction
                if current_source is not None:
                    run_prediction_session(current_source)
                else:
                    print("⚠ Please set an input source first (Option 2).")

            elif choice == '2':
                # Change Source
                new_source = input("Enter new path (e.g., video.mp4, image.jpg) or '0' for webcam: ").strip()
                try:
                    # Convert to integer 0 if applicable, otherwise keep as string path
                    current_source = int(new_source) if new_source == '0' else new_source
                    print(f"✅ Input source updated to: **{current_source}**")
                except ValueError:
                    print("❌ Invalid input. Source remains unchanged.")


            elif choice == '3':
                # Reconnect
                connection_status = connect_to_pi()

            elif choice == '4':
                # Exit
                print("[INFO] Exiting application.")
                break
            
            else:
                print("❌ Invalid choice. Please enter a number from 1 to 4.")

    except KeyboardInterrupt:
        print("\n[INFO] Program interrupted.")

    finally:
        # Cleanup
        if client_socket:
            client_socket.close()
        cv2.destroyAllWindows()

        print("[INFO] Cleanup complete. Goodbye!")
