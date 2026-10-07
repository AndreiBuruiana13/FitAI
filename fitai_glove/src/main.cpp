






















 
 
 
#ifndef WIFI_SSID
#define WIFI_SSID       "YOUR_WIFI_SSID"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD   "YOUR_WIFI_PASSWORD"
#endif
#ifndef BACKEND_IP
#define BACKEND_IP      "127.0.0.1"
#endif
#ifndef BACKEND_PORT
#define BACKEND_PORT    8000
#endif
#ifndef USER_EMAIL
#define USER_EMAIL      "demo@example.com"
#endif
#ifndef USER_PASSWORD
#define USER_PASSWORD   "YOUR_ACCOUNT_PASSWORD"
#endif
#ifndef DATA_COLLECTION_MODE
#define DATA_COLLECTION_MODE    0
#endif

 
 
 
#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_timer.h>
#include <esp_task_wdt.h>
#include <esp_sleep.h>

#include "MAX30105.h"
#include "heartRate.h"

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

 
 
 
#define I2C_SDA_PIN     6
#define I2C_SCL_PIN     7
#define LED_PIN         8        

#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64
#define OLED_RESET      -1
#define OLED_I2C_ADDR   0x3C

#define MPU6050_ADDR    0x68
#define MAX30102_ADDR   0x57

 
 
 
#define SAMPLE_RATE_HZ          100
#define TIMER_PERIOD_US         10000        
#define WINDOW_SIZE             100          

#define MAX30102_READ_MS        20           
#define MAX30102_AVG_SAMPLES    4            

#define TELEMETRY_POST_MS       1000         
#define HTTP_TIMEOUT_MS         10000
#define HTTP_CONNECT_TIMEOUT_MS 10000

#define CIRCULAR_BUF_SIZE       20           
#define WIFI_RETRY_MS           5000         

#define SERIAL_STATUS_MS        2000         
#define I2C_HEALTH_CHECK_MS     10000        
#define OLED_UPDATE_MS          500          

 
 
 
#define MPU6050_RA_ACCEL_XOUT_H 0x3B
#define MPU6050_RA_PWR_MGMT_1   0x6B
#define MPU6050_RA_CONFIG       0x1A
#define MPU6050_RA_GYRO_CONFIG  0x1B
#define MPU6050_RA_ACCEL_CONFIG 0x1C
#define MPU6050_RA_SMPLRT_DIV   0x19
#define MPU6050_RA_WHO_AM_I     0x75

 
 
 
RTC_DATA_ATTR static uint32_t rtcBootCount = 0;

 
 
 
static inline float round4(float v) { return roundf(v * 10000.0f) / 10000.0f; }
static inline float round1(float v) { return roundf(v * 10.0f) / 10.0f; }

 
 
 
static MAX30105          particleSensor;
static Adafruit_SSD1306  display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

 
 
 
static volatile bool     sampleReady     = false;
static volatile uint32_t overrunCount    = 0;
static esp_timer_handle_t timerHandle    = nullptr;

static float accelMag[WINDOW_SIZE];        
static float gyroMag[WINDOW_SIZE];         
static int   sampleIdx = 0;                

 
 
 
static uint32_t lastMaxReadMs = 0;
static long     lastBeatMs     = 0;
static float    hrSamples[MAX30102_AVG_SAMPLES] = {0};
static uint8_t  hrSampleCount = 0;
static float    heartBpm       = 0.0f;
static float    spo2Value      = 0.0f;
static bool     hrValid        = false;
static char     predictedLabel[16] = "UNKNOWN";   

 
 
 
static float    featAccelRms           = 0.0f;
static float    featAccelVariance      = 0.0f;
static float    featAccelMagnitudeMean = 0.0f;
static float    featGyroRms            = 0.0f;
static float    lastValidGyroRms       = 0.0f;   
static uint8_t  featMCR                = 0;
static float    featIQR                = 0.0f;

 
 
 
typedef struct {
    uint64_t timestamp_ms;
    float    accel_rms;
    float    accel_variance;
    float    accel_magnitude_mean;
    float    gyro_rms;
    uint8_t  mcr;
    float    iqr;
    float    heart_bpm;
    float    spo2;
    char     label[16];
    bool     hr_valid;                 
} TelemetryPacket;

static TelemetryPacket circBuf[CIRCULAR_BUF_SIZE];
static int  circHead = 0;              
static int  circCount = 0;             
static uint32_t overflowDropped = 0;

 
 
 
static uint32_t lastWifiAttemptMs = 0;
static uint32_t lastLoginRetryMs  = 0;
#define LOGIN_RETRY_MS 15000
static uint32_t lastTelemetryMs   = 0;
static uint32_t lastStatusMs      = 0;
static uint32_t lastI2cHealthMs   = 0;
static uint32_t lastOledUpdateMs  = 0;
static bool     wifiConnected     = false;
static String   authToken         = "";
static char     localIP[16]       = "---";
static uint32_t bootTimeMs        = 0;

 
static float    lastValidHeartBpm = 0.0f;

 
 
 
static char currentLabel[16] = "UNKNOWN";    
static uint32_t packetCount  = 0;

 
static bool mpuAvailable = false;

 
 
 
static void recoverI2CBus();
static void i2cQuickCheck();
static void i2cHealthCheck();
static bool initMPU6050();
static void readMPU6050Raw(float* ax, float* ay, float* az,
                            float* gx, float* gy, float* gz);
static void computeWindowFeatures();
static void enqueuePacket();
static void flushBuffer();
static bool postTelemetry(const TelemetryPacket* pkt);
static void updateOLED(const char* label, float heartBpm);
static bool connectWiFi();
static bool loginAndGetToken();
static void handleSerialInput();
static void blinkLED(int times, int delayMs);

 
 
 
 
 
static const char* labelToRomanianOLED(const char* label) {
    if (strcmp(label, "WALKING") == 0) return "MERS";
    if (strcmp(label, "RUNNING") == 0) return "ALERG";
    if (strcmp(label, "RESTING") == 0) return "REPAUS";
    if (strcmp(label, "TYPING") == 0) return "TASTARE";
    return "NECUNOSCUT";
}

 
 
 
static void updateOLED(const char* label, float heartBpm) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);

     
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print("FitAI");

     
    const char* displayLabel = labelToRomanianOLED(label);
    display.setTextSize(1);
    display.setCursor(0, 20);
    if (heartBpm > 0.0f) {
        display.printf("%s  Puls:%.0f", displayLabel, heartBpm);
    } else {
        display.printf("%s  Puls:--", displayLabel);
    }

     
    display.setCursor(0, 34);
    display.printf("RMS:%.2fg RTM:%d", featAccelRms, featMCR);

     
    display.setCursor(0, 48);
    if (WiFi.status() == WL_CONNECTED) {
        display.print(WiFi.localIP().toString());
    } else {
        display.print("Fara WiFi");
    }

    display.display();
}

 
 
 
static void recoverI2CBus() {
     
    digitalWrite(I2C_SCL_PIN, HIGH);
    digitalWrite(I2C_SDA_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(I2C_SDA_PIN, HIGH);
    delayMicroseconds(5);

     
    pinMode(I2C_SDA_PIN, INPUT_PULLUP);
    pinMode(I2C_SCL_PIN, INPUT_PULLUP);
    delay(100);

     
    int sdaAfter = digitalRead(I2C_SDA_PIN);
    int sclAfter = digitalRead(I2C_SCL_PIN);
    Serial.printf("[I2C-RECOV] SDA=%d SCL=%d after recovery\n", sdaAfter, sclAfter);
    Serial.flush();
}

 
 
 
static void i2cQuickCheck() {
     
    Serial.println("[I2C-SCAN] Scanning all addresses 0x01-0x7F...");
    int foundCount = 0;
    for (uint8_t addr = 1; addr < 0x7F; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission(true) == 0) {
            Serial.printf("[I2C-SCAN] Found device at 0x%02X\n", addr);
            foundCount++;
        }
    }
    if (foundCount == 0) {
        Serial.println("[I2C-SCAN] No devices found on bus!");
    }
    Serial.printf("[I2C-SCAN] Total devices found: %d\n", foundCount);
    Serial.flush();

     
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission(true) == 0) {
        Serial.println("[I2C-SCAN] MPU6050 at 0x68: FOUND");
    } else {
        Serial.println("[I2C-SCAN] MPU6050 at 0x68: MISSING");
    }
    Serial.flush();
}

 
 
 
 
static void i2cHealthCheck() {
     
    static uint8_t mpuConsecutiveFails = 0;
    static bool    whoamiUnreadableLogged = false;

    uint8_t who = 0x00;
    bool readOk = false;

    for (int retry = 0; retry < 3; retry++) {
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_WHO_AM_I);
        if (Wire.endTransmission(false) == 0) {
            Wire.requestFrom((uint16_t)MPU6050_ADDR, (uint8_t)1);
            who = Wire.available() >= 1 ? Wire.read() : 0x00;
             
            if (who == 0x68 || who == 0x70 || who == 0x72 || who == 0x98) {
                readOk = true;
                break;
            }
        }
        if (retry < 2) delay(10);
    }

    if (readOk) {
        mpuConsecutiveFails = 0;
        mpuAvailable = true;
        whoamiUnreadableLogged = false;
    } else {
        Serial.println("[I2C-HEALTH] WHO_AM_I unreadable this cycle (non-fatal)");
         
         
         
        if (mpuConsecutiveFails < 3) mpuConsecutiveFails++;
    }

     
    if (mpuAvailable) {
        float mag = featAccelMagnitudeMean;
        if (mag >= 0.5f && mag <= 20.0f) {
             
        } else {
            Serial.printf("[MPU-DATA] WARNING: accel out of range (magnitude=%.2fg)\n", mag);
        }
    }

     
    uint8_t partId = particleSensor.readPartID();
    if (partId == 0x15) {
        Serial.println("[I2C-HEALTH] MAX30102 PART_ID OK (0x15)");
    } else {
        Serial.printf("[I2C-HEALTH] MAX30102 PART_ID FAIL: got 0x%02X\n", partId);
    }
}

 
 
 
 
static bool initMPU6050() {
    for (int attempt = 1; attempt <= 3; attempt++) {
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_WHO_AM_I);
        if (Wire.endTransmission(false) != 0) {
            Serial.printf("[INIT] MPU6050 WHO_AM_I NACK (attempt %d/3)\n", attempt);
            if (attempt < 3) delay(500);
            continue;
        }
        Wire.requestFrom((uint16_t)MPU6050_ADDR, (uint8_t)1);
        if (Wire.available() >= 1) {
            uint8_t whoami = Wire.read();
             
            if (whoami != 0x68 && whoami != 0x70 && whoami != 0x72 && whoami != 0x98) {
                Serial.printf("[INIT] MPU6050 WHO_AM_I mismatch: 0x%02X (expected 0x68/0x70/0x72/0x98, attempt %d/3)\n",
                              whoami, attempt);
                if (attempt < 3) delay(500);
                continue;
            }
            Serial.printf("[INIT] MPU6050 WHO_AM_I verified: 0x%02X\n", whoami);
        } else {
            Serial.printf("[INIT] MPU6050 read timeout (attempt %d/3)\n", attempt);
            if (attempt < 3) delay(500);
            continue;
        }

         
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_PWR_MGMT_1);
        Wire.write(0x00);
        if (Wire.endTransmission() != 0) {
            Serial.printf("[INIT] MPU6050 wake failed (attempt %d/3)\n", attempt);
            if (attempt < 3) delay(500);
            continue;
        }
        delay(10);

         
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_SMPLRT_DIV);
        Wire.write(0x09);
        Wire.endTransmission();

         
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_CONFIG);
        Wire.write(0x02);
        Wire.endTransmission();

         
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_ACCEL_CONFIG);
        Wire.write(0x08);
        Wire.endTransmission();

         
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(MPU6050_RA_GYRO_CONFIG);
        Wire.write(0x08);
        Wire.endTransmission();

        mpuAvailable = true;
        Serial.println("[INIT] MPU6050 init OK.");
        return true;
    }

    Serial.println("[INIT] MPU6050 PERMANENT FAIL — using synthetic data");
    mpuAvailable = false;
    return false;
}

 
 
 
 
static void readMPU6050Raw(float* ax, float* ay, float* az,
                           float* gx, float* gy, float* gz) {
    if (!mpuAvailable) {
        *ax = 0.0f;
        *ay = 0.0f;
        *az = 1.0f;
        *gx = 0.0f;
        *gy = 0.0f;
        *gz = 0.0f;
        return;
    }

    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_RA_ACCEL_XOUT_H);
    if (Wire.endTransmission(false) != 0) {
        *ax = *ay = *az = *gx = *gy = *gz = 0.0f;
        return;
    }

    Wire.requestFrom((uint16_t)MPU6050_ADDR, (uint8_t)14);
    if (Wire.available() < 14) {
        *ax = *ay = *az = *gx = *gy = *gz = 0.0f;
        return;
    }

    int16_t ax_raw = (Wire.read() << 8) | Wire.read();
    int16_t ay_raw = (Wire.read() << 8) | Wire.read();
    int16_t az_raw = (Wire.read() << 8) | Wire.read();
    Wire.read(); Wire.read();   
    int16_t gx_raw = (Wire.read() << 8) | Wire.read();
    int16_t gy_raw = (Wire.read() << 8) | Wire.read();
    int16_t gz_raw = (Wire.read() << 8) | Wire.read();

    *ax = ax_raw / 8192.0f;
    *ay = ay_raw / 8192.0f;
    *az = az_raw / 8192.0f;
    *gx = gx_raw / 65.5f;
    *gy = gy_raw / 65.5f;
    *gz = gz_raw / 65.5f;
}

 
 
 
static void IRAM_ATTR onTimer(void* arg) {
    if (sampleReady) {
        overrunCount++;
    } else {
        sampleReady = true;
    }
}

 
 
 
static uint8_t computeMCR(const float* magBuffer, uint16_t count, float windowMean) {
    if (count < 2 || magBuffer == nullptr) return 0;
    uint8_t crossings = 0;
    const float hysteresis = 0.005f;
    bool aboveMean = (magBuffer[0] - windowMean) >= 0.0f;
    for (uint16_t i = 1; i < count; i++) {
        float val = magBuffer[i] - windowMean;
        if (aboveMean) {
            if (val < -hysteresis) { crossings++; aboveMean = false; }
        } else {
            if (val > hysteresis) { crossings++; aboveMean = true; }
        }
    }
    return crossings;
}

 
 
 
static uint16_t qs_partition(float* arr, uint16_t l, uint16_t r, uint16_t pi) {
    float pv = arr[pi];
    float t = arr[pi]; arr[pi] = arr[r]; arr[r] = t;
    uint16_t si = l;
    for (uint16_t i = l; i < r; i++) {
        if (arr[i] < pv) {
            t = arr[i]; arr[i] = arr[si]; arr[si] = t;
            si++;
        }
    }
    t = arr[si]; arr[si] = arr[r]; arr[r] = t;
    return si;
}

static float qs_select(float* arr, uint16_t n, uint16_t k) {
    uint16_t l = 0, r = n - 1;
    while (l <= r) {
        if (l == r) return arr[l];
        uint16_t pi = l + (r - l) / 2;
        pi = qs_partition(arr, l, r, pi);
        if (pi == k) return arr[pi];
        else if (pi < k) l = pi + 1;
        else r = pi - 1;
    }
    return 0.0f;
}

static float computeIQR(float* magBuffer, uint16_t count) {
    if (count < 4) return 0.0f;
    static float scratch[WINDOW_SIZE];
    if (count > WINDOW_SIZE) return 0.0f;
    memcpy(scratch, magBuffer, count * sizeof(float));
    uint16_t q1Idx = count / 4;
    uint16_t q3Idx = (3 * count) / 4;
    float q1 = qs_select(scratch, count, q1Idx);
    float q3 = qs_select(scratch, count, q3Idx);
    return q3 - q1;
}

 
 
 
 
static void computeWindowFeatures() {
    float sum = 0.0f, sumSq = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        sum += accelMag[i];
        sumSq += accelMag[i] * accelMag[i];
    }
    float mean = sum / WINDOW_SIZE;
    featAccelMagnitudeMean = mean;
    featAccelRms = sqrtf(sumSq / WINDOW_SIZE);
     
    float varSum = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        float dev = accelMag[i] - mean;
        varSum += dev * dev;
    }
    featAccelVariance = varSum / WINDOW_SIZE;

     
    float gyroSumSq = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        gyroSumSq += gyroMag[i] * gyroMag[i];
    }
    float gyroRmsCandidate = sqrtf(gyroSumSq / WINDOW_SIZE);
    if (gyroRmsCandidate > 0.0f) {
        featGyroRms = gyroRmsCandidate;
        lastValidGyroRms = gyroRmsCandidate;
    } else {
        featGyroRms = lastValidGyroRms;   
    }

    featMCR = computeMCR(accelMag, WINDOW_SIZE, mean);
    featIQR = computeIQR(accelMag, WINDOW_SIZE);
}

 
 
 
static void blinkLED(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        if (i < times - 1) delay(delayMs);
    }
}

 
 
 
 
static void enqueuePacket() {
    TelemetryPacket* pkt = &circBuf[circHead];
    pkt->timestamp_ms = (uint64_t)millis();   
    pkt->accel_rms = featAccelRms;
    pkt->accel_variance = featAccelVariance;
    pkt->accel_magnitude_mean = featAccelMagnitudeMean;
    pkt->gyro_rms = featGyroRms;
    pkt->mcr = featMCR;
    pkt->iqr = featIQR;
    pkt->heart_bpm = heartBpm;
    pkt->spo2 = spo2Value;
    pkt->hr_valid = hrValid;

     
    memset(pkt->label, 0, sizeof(pkt->label));
    if (DATA_COLLECTION_MODE == 1) {
        strncpy(pkt->label, currentLabel, sizeof(pkt->label) - 1);
    } else {
        strncpy(pkt->label, "UNKNOWN", sizeof(pkt->label) - 1);
    }

    circHead = (circHead + 1) % CIRCULAR_BUF_SIZE;
    if (circCount < CIRCULAR_BUF_SIZE) {
        circCount++;
    } else {
        overflowDropped++;
    }
}

 
 
 
static void flushBuffer() {
    while (circCount > 0) {
        esp_task_wdt_reset();   
        int idx = (circHead - circCount + CIRCULAR_BUF_SIZE) % CIRCULAR_BUF_SIZE;
        if (postTelemetry(&circBuf[idx])) {
            circCount--;
            packetCount++;
        } else {
            break;   
        }
    }
}

 
 
 
 
 
 
 
 
 
static bool postTelemetry(const TelemetryPacket* pkt) {
    if (!wifiConnected || authToken.length() == 0) return false;

    HTTPClient http;
    http.setConnectTimeout(HTTP_CONNECT_TIMEOUT_MS);
    http.setTimeout(HTTP_TIMEOUT_MS);

    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/ingest", BACKEND_IP, BACKEND_PORT);

     
    float hrToSend = pkt->heart_bpm;
    if (!pkt->hr_valid || pkt->heart_bpm < 30.0f || pkt->heart_bpm > 250.0f) {
        hrToSend = lastValidHeartBpm;   
    } else {
        lastValidHeartBpm = pkt->heart_bpm;   
    }

     
    StaticJsonDocument<512> doc;
    doc["timestamp"]            = pkt->timestamp_ms;
    doc["accel_rms"]            = round4(pkt->accel_rms);
    doc["accel_variance"]       = round4(pkt->accel_variance);
    doc["accel_magnitude_mean"] = round4(pkt->accel_magnitude_mean);
    doc["gyro_rms"]             = round4(pkt->gyro_rms);
    doc["mcr"]                  = pkt->mcr;
    doc["iqr"]                  = round4(pkt->iqr);
    doc["heart_bpm"]            = round1(hrToSend);
    doc["spo2"]                 = round1(pkt->spo2);
    doc["label"]                = (strlen(pkt->label) > 0) ? pkt->label : "UNKNOWN";
    doc["speed_mps"]            = 0.0;   

    String body;
    serializeJson(doc, body);

     
    Serial.printf("[HTTP] URL: %s\n", url);
    Serial.printf("[HTTP] Body: %s\n", body.c_str());
    Serial.printf("[HTTP] WiFi status: %d\n", WiFi.status());
    Serial.printf("[HTTP] Token length: %d\n", authToken.length());

     
    esp_task_wdt_reset();
    WiFiClient client;
    http.begin(client, url);
    esp_task_wdt_reset();
    http.setReuse(false);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", "Bearer " + authToken);
    esp_task_wdt_reset();
    int code = http.POST(body);
    esp_task_wdt_reset();
    String errorText = http.errorToString(code);    

     
    if (code >= 200 && code < 300) {
        String respBody = http.getString();
        StaticJsonDocument<128> respDoc;
        DeserializationError respErr = deserializeJson(respDoc, respBody);
        if (!respErr && respDoc.containsKey("activity_type")) {
            const char* pred = respDoc["activity_type"];
            memset(predictedLabel, 0, sizeof(predictedLabel));
            strncpy(predictedLabel, pred, sizeof(predictedLabel) - 1);
            Serial.printf("[HTTP] AI prediction: %s\n", predictedLabel);
        }
    }

    http.end();
    client.stop();
    esp_task_wdt_reset();

     
    if (code == 401) {
        Serial.println("[HTTP] 401 Unauthorized — re-authenticating...");
        if (loginAndGetToken()) {
            esp_task_wdt_reset();
            WiFiClient retryClient;
            http.begin(retryClient, url);
            esp_task_wdt_reset();
            http.addHeader("Content-Type", "application/json");
            http.addHeader("Authorization", "Bearer " + authToken);
            esp_task_wdt_reset();
            code = http.POST(body);
            esp_task_wdt_reset();
            errorText = http.errorToString(code);   
            http.end();
            retryClient.stop();
            esp_task_wdt_reset();
        }
    }

    bool ok = (code >= 200 && code < 300);

    if (ok) {
        Serial.println("[HTTP] Ingest payload transmitted successfully.");
    } else {
        Serial.printf("[HTTP] POST /ingest returned HTTP %d err=%s (body: %d bytes)\n",
                      code, errorText.c_str(), body.length());
    }

    return ok;
}


 
 
 
static bool connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return true;

    Serial.printf("[WIFI] Attempting connection to %s\n", WIFI_SSID);
    Serial.flush();

     
     
    WiFi.setTxPower(WIFI_POWER_8_5dBm);
    Serial.println("[WIFI] TX power set to 8.5dBm to avoid brownout");

     
    delay(500);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < 15000) {
        delay(500);
        Serial.print(".");
        esp_task_wdt_reset();
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        uint32_t elapsed = millis() - start;
        IPAddress ip = WiFi.localIP();
        snprintf(localIP, sizeof(localIP), "%s", ip.toString().c_str());
        Serial.printf("[WIFI] Connected in %lu ms. Local IP: %s\n", elapsed, localIP);
        Serial.flush();
        return true;
    }

    Serial.println("[WIFI] Connection failed (15 s timeout).");
    Serial.flush();
    return false;
}

 
 
 
static bool loginAndGetToken() {
    if (!wifiConnected) return false;

    HTTPClient http;
    http.setConnectTimeout(HTTP_CONNECT_TIMEOUT_MS);
    http.setTimeout(HTTP_TIMEOUT_MS);

    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/login", BACKEND_IP, BACKEND_PORT);
     
    esp_task_wdt_reset();
    WiFiClient loginClient;
    http.begin(loginClient, url);
    esp_task_wdt_reset();
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String body = "username=" + String(USER_EMAIL) + "&password=" + String(USER_PASSWORD);
    esp_task_wdt_reset();
    int code = http.POST(body);
    esp_task_wdt_reset();

    if (code == 200) {
        String resp = http.getString();
        StaticJsonDocument<256> doc;
        DeserializationError err = deserializeJson(doc, resp);
        if (!err && doc.containsKey("access_token")) {
            authToken = doc["access_token"].as<String>();
            Serial.println("[AUTH] Login successful, token cached.");
            http.end();
            loginClient.stop();
            return true;
        }
    }

    Serial.printf("[AUTH] Login failed, HTTP %d\n", code);
    http.end();
    loginClient.stop();
    return false;
}

 
 
 
 
 
static void handleSerialInput() {
    while (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        input.toUpperCase();

        if (input.length() == 0) continue;

        if (input == "WALKING" || input == "RESTING" ||
            input == "RUNNING"  || input == "TYPING") {
            memset(currentLabel, 0, sizeof(currentLabel));
            strncpy(currentLabel, input.c_str(), sizeof(currentLabel) - 1);
            blinkLED(3, 200);
            Serial.printf("[DATA] Label set to: %s\n", currentLabel);
            Serial.flush();
        } else {
            Serial.printf("[DATA] Unknown label: '%s'. Valid: WALKING, RESTING, RUNNING, TYPING\n",
                          input.c_str());
        }
    }
}

 
 
 
void setup() {
    Serial.begin(115200);
    delay(2000);   

    rtcBootCount++;
    bootTimeMs = millis();

     
    Serial.println("--------------------------------");
    Serial.println("BUILD VERIFICATION");
    Serial.println("--------------------------------");
    Serial.printf("Firmware build date: %s\n", __DATE__);
    Serial.printf("Firmware build time: %s\n", __TIME__);
    Serial.println("Git patch ID: FITAI_AUDIT_01");
    Serial.println("--------------------------------");
    Serial.flush();

     
    Serial.println("[BOOT] ESP32-C3 RISC-V initializing...");
    Serial.printf("[BOOT] Boot count (RTC): %u   Free heap: %u bytes\n",
                  rtcBootCount, ESP.getFreeHeap());
    if (rtcBootCount > 1) {
        Serial.printf("[BOOT] WARNING: RTC boot count = %u — possible brownout or reset detected!\n",
                      rtcBootCount);
    }
    Serial.flush();
    delay(100);

     
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

     
    Serial.println("[I2C] Executing pre-flight line clearing...");
    Serial.flush();
    recoverI2CBus();
    delay(50);

     
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    Wire.setClock(100000);   
    delay(200);

     
    Serial.println("[I2C] Full bus scan...");
    Serial.flush();
    i2cQuickCheck();
    delay(50);

     
    Serial.println("[INIT] OLED begin...");
    Serial.flush();
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
        Serial.println("[INIT] OLED init FAILED");
    } else {
        Serial.println("[INIT] OLED OK, drawing boot screen...");
        display.clearDisplay();
        display.setTextSize(2);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.print("FitAI");

         
        display.setTextSize(1);
        display.setCursor(0, 18);
        const char* bootLabel = (DATA_COLLECTION_MODE == 1) ? currentLabel : labelToRomanianOLED(predictedLabel);
        display.printf("%s  HR:--", bootLabel);
        display.setCursor(0, 30);
        display.print("RMS:-- MCR:--");
        display.setCursor(0, 42);
        display.print("Starting...");

        display.display();
    }
    Serial.flush();
    delay(100);

     
    Serial.println("[INIT] MPU6050 init...");
    Serial.flush();
    if (!initMPU6050()) {
        Serial.println("[INIT] MPU6050 init FAILED. Check wiring.");
    } else {
        Serial.println("[INIT] MPU6050 init OK.");
    }
    Serial.flush();
    delay(100);

     
    Serial.println("[INIT] MAX30102 begin...");
    Serial.flush();
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("[INIT] MAX30102 not found. HR/SpO2 disabled.");
    } else {
        uint8_t partId = particleSensor.readPartID();
        Serial.printf("[INIT] MAX30102 PART_ID verified: 0x%02X\n", partId);
        if (partId != 0x15) {
            Serial.printf("[INIT] WARNING: MAX30102 PART_ID expected 0x15, got 0x%02X\n", partId);
        }
        particleSensor.setup();
         
        particleSensor.setPulseAmplitudeRed(0x24);
        particleSensor.setPulseAmplitudeIR(0x24);
        particleSensor.setPulseAmplitudeGreen(0);
        Serial.println("[INIT] MAX30102 init OK (LED: Red=0x24, IR=0x24).");
    }
    Serial.flush();
    delay(100);

     
    Serial.println("[WIFI] Connecting...");
    Serial.flush();
    esp_task_wdt_reset();   
    wifiConnected = connectWiFi();
    esp_task_wdt_reset();   
    if (wifiConnected) {
        if (loginAndGetToken()) {
            Serial.println("[HTTP] Auth: Ready to send telemetry.");
        }
    }
    Serial.flush();
    delay(100);

     
    esp_timer_create_args_t timerArgs = {};
    timerArgs.callback = &onTimer;
    timerArgs.name = "sampleTimer";
    esp_timer_create(&timerArgs, &timerHandle);
    esp_timer_start_periodic(timerHandle, TIMER_PERIOD_US);

     
    esp_task_wdt_init(10, true);
    esp_task_wdt_add(NULL);

     
    if (DATA_COLLECTION_MODE == 1) {
        Serial.println("[DATA] DATA_COLLECTION_MODE=1 — send label via Serial.");
        Serial.println("[DATA] Valid labels: WALKING, RESTING, RUNNING, TYPING");
    } else {
        Serial.println("[DATA] DATA_COLLECTION_MODE=0 — label='UNKNOWN' for all packets.");
    }

    Serial.println("[INIT] Sampling started at 100 Hz.");
    Serial.flush();
}

 
 
 
 
void loop() {
    uint32_t now = millis();
    esp_task_wdt_reset();

     
    if (DATA_COLLECTION_MODE == 1) {
        handleSerialInput();
    }

     
    if (!wifiConnected && (now - lastWifiAttemptMs >= WIFI_RETRY_MS)) {
        lastWifiAttemptMs = now;
        wifiConnected = connectWiFi();
        if (wifiConnected) {
            esp_task_wdt_reset();   
            loginAndGetToken();
            esp_task_wdt_reset();
            if (circCount > 0) {
                Serial.printf("[WIFI] Reconnected — flushing %d buffered packets\n", circCount);
                flushBuffer();
                esp_task_wdt_reset();
            }
        }
    } else if (wifiConnected && WiFi.status() != WL_CONNECTED) {
        wifiConnected = false;
        strncpy(localIP, "---", sizeof(localIP));
        Serial.println("[WIFI] Disconnected. Buffering packets...");
    }

     
    if (wifiConnected && authToken.length() == 0 &&
        (now - lastLoginRetryMs >= LOGIN_RETRY_MS)) {
        lastLoginRetryMs = now;
        Serial.println("[AUTH] Token missing — retrying login...");
        esp_task_wdt_reset();   
        loginAndGetToken();
        esp_task_wdt_reset();
        if (authToken.length() > 0 && circCount > 0) {
            Serial.printf("[AUTH] Login succeeded — flushing %d buffered packets\n", circCount);
            flushBuffer();
            esp_task_wdt_reset();
        }
    }

     
    if (sampleReady) {
        sampleReady = false;

        float ax, ay, az, gx, gy, gz;
        readMPU6050Raw(&ax, &ay, &az, &gx, &gy, &gz);

         
        float mag = sqrtf(ax * ax + ay * ay + az * az);
        accelMag[sampleIdx] = mag;

         
        float gyroMagVal = sqrtf(gx * gx + gy * gy + gz * gz);
        gyroMag[sampleIdx] = gyroMagVal;

         
        static float lastRawAx = 0.0f, lastRawAy = 0.0f, lastRawAz = 0.0f;
        static float lastRawMag = 0.0f;
        lastRawAx = ax;
        lastRawAy = ay;
        lastRawAz = az;
        lastRawMag = mag;

        sampleIdx++;

        if (sampleIdx >= WINDOW_SIZE) {
            sampleIdx = 0;
            computeWindowFeatures();
            enqueuePacket();
        }
    }

     
    {
        static uint32_t lastRawDiag = 0;
        if (now - lastRawDiag >= 5000) {
            lastRawDiag = now;
             
            Wire.beginTransmission(0x68);
            Wire.write(0x3B);
            if (Wire.endTransmission(false) == 0 && Wire.requestFrom((uint8_t)0x68, (uint8_t)6) == 6) {
                int16_t rax = (Wire.read() << 8) | Wire.read();
                int16_t ray = (Wire.read() << 8) | Wire.read();
                int16_t raz = (Wire.read() << 8) | Wire.read();
                float fax = rax / 8192.0f, fay = ray / 8192.0f, faz = raz / 8192.0f;
                float mag = sqrtf(fax*fax + fay*fay + faz*faz);
                Serial.printf("[MPU-RAW] AX=%d AY=%d AZ=%d MAG=%.2fg\n", rax, ray, raz, mag);
                if (mag < 0.3f) Serial.println("[MPU-RAW] INVALID ACCEL DATA");
            } else {
                Serial.println("[MPU-RAW] I2C READ FAILED");
            }
        }
    }

     
    if (now - lastMaxReadMs >= MAX30102_READ_MS) {
        lastMaxReadMs = now;

        particleSensor.check();
        long irValue = 0;
        bool beatFound = false;
        float bpmInstant = 0.0f;

        while (particleSensor.available()) {
            irValue = particleSensor.getFIFOIR();
            if (irValue > 50000) {
                if (checkForBeat(irValue)) {
                    beatFound = true;
                    uint32_t beatNow = millis();
                    long delta = beatNow - lastBeatMs;
                    lastBeatMs = beatNow;
                    bpmInstant = 60.0f / (delta / 1000.0f);
                    if (bpmInstant > 40.0f && bpmInstant < 220.0f) {
                        hrSamples[hrSampleCount % MAX30102_AVG_SAMPLES] = bpmInstant;
                        hrSampleCount++;
                        if (hrSampleCount >= MAX30102_AVG_SAMPLES) {
                            float sum = 0.0f;
                            for (int i = 0; i < MAX30102_AVG_SAMPLES; i++) sum += hrSamples[i];
                            heartBpm = sum / MAX30102_AVG_SAMPLES;
                            hrValid = true;
                        }
                    }
                }
            }
            particleSensor.nextSample();
        }

        if (irValue <= 50000) {
             
            if (now - lastBeatMs > 3000) {
                hrValid = false;
                heartBpm = 0.0f;
                hrSampleCount = 0;
            }
        }

         
        static uint32_t lastHrDiag = 0;
        if (millis() - lastHrDiag > 1000) {
            Serial.printf(
                "[HR-DIAG] IR=%ld HR=%.1f Beat=%d BPMinst=%.1f hrValid=%d\n",
                irValue,
                heartBpm,
                beatFound ? 1 : 0,
                bpmInstant,
                hrValid ? 1 : 0
            );
            lastHrDiag = millis();
        }
    }

     
    if (now - lastTelemetryMs >= TELEMETRY_POST_MS) {
        lastTelemetryMs = now;
        Serial.printf("[AUTH] tokenLen=%d wifi=%d\n", authToken.length(), wifiConnected ? 1 : 0);
        if (wifiConnected && authToken.length() > 0) {
            flushBuffer();
        }
    }

     
    if (now - lastOledUpdateMs >= OLED_UPDATE_MS) {
        lastOledUpdateMs = now;
        const char* dispLabel = (DATA_COLLECTION_MODE == 1) ? currentLabel : predictedLabel;
        updateOLED(dispLabel, heartBpm);
    }

     
    if (now - lastI2cHealthMs >= I2C_HEALTH_CHECK_MS) {
        lastI2cHealthMs = now;
        i2cHealthCheck();
    }

     
    if (now - lastStatusMs >= SERIAL_STATUS_MS) {
        lastStatusMs = now;
        Serial.printf("[STAT] Uptime=%lu min  Pkts=%u  Buf=%d/%d  Over=%u  WiFi=%d  HR=%.1f  Label=%s\n",
            (now - bootTimeMs) / 60000,
            packetCount,
            circCount, CIRCULAR_BUF_SIZE,
            overflowDropped,
            wifiConnected ? 1 : 0,
            heartBpm,
            (DATA_COLLECTION_MODE == 1) ? currentLabel : "UNKNOWN");
    }
}