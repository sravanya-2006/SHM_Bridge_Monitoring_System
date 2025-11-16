

# 🌉 Smart Bridge Monitoring System (IoT + DL + Firebase)

A real-time **structural health monitoring system** using **Raspberry Pi**, **AI-based crack detection**, and **Firebase** for web visualization. The system monitors **vibration**, **tilt**, and **cracks** in bridges and sends alerts when unsafe conditions are detected.

---

## 📁 Project Structure

| File                 | Device       | Purpose                                                                                                                             |
| :------------------- | :----------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| `testdone.py`        | Raspberry Pi | Reads MPU6050 & vibration sensors, publishes data to Firebase, sends email alerts, acts as TCP **server** for laptop communication. |
| `moderun.py`         | Laptop / PC  | Loads `crack_detection.h5` to run **crack detection**, acts as TCP **client** sending `DANGER`/`SAFE` messages to the Pi.           |
| `dashboard.html`     | Web Browser  | Real-time **dashboard** using Firebase Realtime Database & Chart.js to display tilt and vibration trends.                           |
| `crack_detection.h5` | Laptop / PC  | Pre-trained TensorFlow/Keras model for image classification (**Crack** vs **Safe**).                                                |

---

## ⚙️ Hardware & Connections

**Required:** Raspberry Pi, MPU6050 (I2C), Digital Vibration Sensor, Status LED

| Sensor               | Raspberry Pi Pin | GPIO (BCM) |
| :------------------- | :--------------- | :--------- |
| MPU6050 SDA          | I2C Data         | GPIO 2     |
| MPU6050 SCL          | I2C Clock        | GPIO 3     |
| Vibration Sensor Out | Digital Input    | GPIO 17    |
| Status LED           | Output           | GPIO 27    |

---

## 💻 Setup Instructions

### 1. Raspberry Pi Setup (`testdone.py`)

**Install dependencies:**

```bash
pip install RPi.GPIO firebase-admin smbus2
```

**Configuration:**

* Update **Firebase**: Provide path to service account JSON and `databaseURL`.
* Update **Email settings**: Add your email, app password, and recipient address in the email alert section.

---

### 2. Laptop Setup (`moderun.py`)

**Install dependencies:**

```bash
pip install opencv-python tensorflow numpy
```

**Configuration:**

* Update `RASPBERRY_PI_IP` with your Raspberry Pi’s IP address.

---

### 3. Web Dashboard Setup (`dashboard.html`)

* Replace placeholder values in the `firebaseConfig` object (`YOUR_API_KEY`, `YOUR_PROJECT_ID`, etc.) with your Firebase Web App settings.

---

## 🚀 Running the System

1. **Start the Raspberry Pi server:**

```bash
python3 testdone.py
```

* Enter **Y** when prompted to enable TCP network communication.

2. **Start the Laptop client (AI crack detection):**

```bash
python3 moderun.py
```

* Use the main menu to select video source (**Option 2**) and start predictions (**Option 1**).
* Sends `DANGER` or `SAFE` messages to the Pi based on AI output.

3. **Open the dashboard:**

* Launch `dashboard.html` in a web browser to monitor real-time tilt and vibration data.

---

## 🚨 Alerts

The Pi handles critical alerts based on **sensor readings** and **AI predictions**:

| Alert Type          | Trigger                                                    | Action                         |
| :------------------ | :--------------------------------------------------------- | :----------------------------- |
| **Vibration Alert** | Vibration sensor detects high vibration (`vibration == 1`) | LED ON (GPIO 27) & Email Alert |
| **Stability Alert** | Roll or pitch exceeds **30°**                              | LED ON & Email Alert           |
| **Crack Alert**     | Receives **`DANGER`** from Laptop over TCP                 | LED ON & Email Alert           |

---

## 🔧 Notes

* Ensure the Pi and Laptop are on the same network for TCP communication.
* Use **App Passwords** for email to avoid authentication issues.
* Adjust alert thresholds in `testdone.py` as per bridge safety requirements.

## Crack Detection 
The crack detection module in this project uses my custom InceptionV3 deep-learning model, which is implemented and trained in a separate repository linked here.
https://github.com/sravanya-2006/Crack_Detection_Modell.git
