#!/usr/bin/python

import math
import time
import socket
import smtplib
from email.message import EmailMessage
from datetime import datetime
import RPi.GPIO as GPIO

# -------------------- SMBUS AUTO-DETECT --------------------
try:
    import smbus
    print("[INFO] Using smbus")
except ImportError:
    try:
        import smbus2 as smbus
        print("[INFO] Using smbus2 as fallback")
    except ImportError:
        print("[ERROR] Neither smbus nor smbus2 found. Install using:")
        print("   sudo apt install python3-smbus")
        print("or in venv: pip install smbus2")
        exit()

# -------------------- FIREBASE SETUP --------------------
try:
    import firebase_admin
    from firebase_admin import credentials, db

    cred = cred = credentials.Certificate('PATH/TO/YOUR/SERVICE_ACCOUNT_KEY.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': '# ENTER THE FIRE BASE DATABASE URL'
    })
    ref = db.reference('bridge_data')
    FIREBASE_ENABLED = True
    print("[INFO] Firebase connected successfully.")
except Exception as e:
    print("[WARN] Firebase not initialized:", e)
    FIREBASE_ENABLED = False

# -------------------- EMAIL CONFIG --------------------
def email_alert(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg['subject'] = subject
    msg['to'] = to

    user = "# ADD YOUR EMAIL HERE"
    msg['from'] = user
    password = "# ADD YOUR APP PASSWORD"  # App password

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        print("[EMAIL] Alert sent successfully!")
    except Exception as e:
        print("[EMAIL ERROR]", e)

# -------------------- GPIO SETUP --------------------
LED_PIN = 27
VIBRATION_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(VIBRATION_PIN, GPIO.IN)
GPIO.output(LED_PIN, GPIO.LOW)

# -------------------- MPU6050 SETUP --------------------
bus = smbus.SMBus(1)
address = 0x69
PWR_MGMT_1 = 0x6b
bus.write_byte_data(address, PWR_MGMT_1, 0)
time.sleep(0.1)

ACCEL_XOUT_H = 0x3b
ACCEL_YOUT_H = 0x3d
ACCEL_ZOUT_H = 0x3f

def read_word(reg):
    high = bus.read_byte_data(address, reg)
    low = bus.read_byte_data(address, reg + 1)
    val = (high << 8) + low
    return val

def read_word_2c(reg):
    val = read_word(reg)
    if val >= 0x8000:
        return -((65535 - val) + 1)
    else:
        return val

def dist(a, b):
    return math.sqrt((a*a) + (b*b))

def get_x_rotation(x, y, z):
    radians = math.atan2(y, dist(x, z))
    return math.degrees(radians)

def get_y_rotation(x, y, z):
    radians = math.atan2(x, dist(y, z))
    return -math.degrees(radians)

# -------------------- ASK USER --------------------
def ask_for_connection():
    while True:
        response = input("Are you connecting the laptop? (Y/N): ").upper()
        if response in ('Y', 'YES'):
            return True
        elif response in ('N', 'NO'):
            return False
        else:
            print("Invalid input. Please enter Y or N.")

connect_laptop = ask_for_connection()
conn = None
server_socket = None

if connect_laptop:
    HOST = "0.0.0.0"
    PORT = 5000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print("[INFO] Waiting for connection from laptop...")
        conn, addr = server_socket.accept()
        print(f"[INFO] Connected to {addr}")
    except socket.error as e:
        print(f"[SOCKET ERROR] {e}")
        connect_laptop = False
        conn = None

# -------------------- MAIN LOOP --------------------
try:
    print("\nTimestamp | Vibration | Roll(°) | Pitch(°)")
    print("----------------------------------------------------")

    while True:
        vibration = GPIO.input(VIBRATION_PIN)  # 0=normal, 1=detected

        accel_xout = read_word_2c(ACCEL_XOUT_H)
        accel_yout = read_word_2c(ACCEL_YOUT_H)
        accel_zout = read_word_2c(ACCEL_ZOUT_H)

        accel_xout_scaled = accel_xout / 16384.0
        accel_yout_scaled = accel_yout / 16384.0
        accel_zout_scaled = accel_zout / 16384.0

        roll = get_x_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)
        pitch = get_y_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} | {vibration} | {roll:7.2f} | {pitch:7.2f}")

        alert_sent = False

        # --- Upload only SENSOR DATA to Firebase ---
        if FIREBASE_ENABLED:
            try:
                ref.push({
                    'time': timestamp,
                    'vibration': vibration,
                    'roll': round(roll, 2),
                    'pitch': round(pitch, 2)
                })
            except Exception as e:
                print("[FIREBASE ERROR]", e)

        # --- Alerts ---
        if vibration == 1:
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("⚠️  Vibration Detected! Sending alert...")
            email_alert("Bridge Vibration Alert ⚠️",
                        f"High vibration detected on bridge at {timestamp}.",
                        "#ENTER YOUR EMAIL THAT HAS TO RECEIVE MESSAGE")
            alert_sent = True
        elif abs(roll) > 30 or abs(pitch) > 30:
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("⚠️  Unusual tilt detected! Sending alert...")
            email_alert("Bridge Stability Alert ⚠️",
                        f"Unusual tilt detected!\nRoll: {roll:.2f}°\nPitch: {pitch:.2f}°",
                        "#ENTER YOUR EMAIL THAT HAS TO RECEIVE MESSAGE")
            alert_sent = True

        # --- Laptop communication ---
        if connect_laptop and conn:
            conn.settimeout(0.1)
            try:
                data = conn.recv(1024)
                if data:
                    msg = data.decode().strip()
                    print("[INFO] From laptop:", msg)

                    if msg == "DANGER":
                        GPIO.output(LED_PIN, GPIO.HIGH)
                        print("🚨 Crack Detected! Sending email...")
                        email_alert("Bridge Crack Alert 🚨",
                                    "A structural crack has been detected. Immediate attention required.",
                                    "#ENTER YOUR EMAIL THAT HAS TO RECEIVE MESSAGE")
                        alert_sent = True

                    elif msg == "SAFE":
                        GPIO.output(LED_PIN, GPIO.LOW)
                        print("✅ Safe state restored.")
                        alert_sent = False
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("[INFO] Laptop disconnected.")
                connect_laptop = False
                conn = None

        if not alert_sent:
            GPIO.output(LED_PIN, GPIO.LOW)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[INFO] Shutting down...")

finally:
    if conn:
        conn.close()
    if server_socket:
        server_socket.close()
    GPIO.cleanup()
    print("[INFO] Clean exit.")
