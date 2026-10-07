

#include <Wire.h>

#define SDA_PIN 6
#define SCL_PIN 7

void recoverI2CBus() {
    pinMode(SCL_PIN, OUTPUT);
    pinMode(SDA_PIN, INPUT_PULLUP);
    delay(10);
    Serial.println("[DIAG] Starting I2C bus recovery (bit-bang)...");
    for (int i = 0; i < 9; i++) {
        digitalWrite(SCL_PIN, LOW);
        delayMicroseconds(5);
        digitalWrite(SCL_PIN, HIGH);
        delayMicroseconds(5);
    }
    pinMode(SDA_PIN, OUTPUT);
    digitalWrite(SDA_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(SCL_PIN, HIGH);
    delayMicroseconds(5);
    digitalWrite(SDA_PIN, HIGH);
    delayMicroseconds(5);
    pinMode(SDA_PIN, INPUT);
    pinMode(SCL_PIN, INPUT);
    Serial.println("[DIAG] Bus recovery complete");
}

void setup() {
    Serial.begin(115200);
    delay(2000);  

    Serial.println("\n=== I2C DIAGNOSTIC ===");
    Serial.printf("SDA=GPIO%d, SCL=GPIO%d\n", SDA_PIN, SCL_PIN);

    
    recoverI2CBus();

    
    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(400000);
    Serial.println("[DIAG] Wire.begin() done at 400kHz");

    
    Serial.println("[DIAG] Scanning I2C bus...");
    int found = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        uint8_t error = Wire.endTransmission();
        if (error == 0) {
            Serial.printf("[DIAG] FOUND at 0x%02X\n", addr);
            found++;
        } else if (error == 2) {
            Serial.printf("[DIAG] NACK at 0x%02X (address received, device NACKed)\n", addr);
        }
        delay(5);
    }
    Serial.printf("[DIAG] Scan complete – %d device(s) found\n", found);

    
    Serial.println("[DIAG] Testing known addresses...");
    Wire.beginTransmission(0x68);
    if (Wire.endTransmission() == 0) {
        Serial.println("[DIAG] MPU6050 (0x68) RESPONDING!");
    } else {
        Serial.println("[DIAG] MPU6050 (0x68) NOT FOUND");
    }

    Wire.beginTransmission(0x57);
    if (Wire.endTransmission() == 0) {
        Serial.println("[DIAG] MAX30102 (0x57) RESPONDING!");
    } else {
        Serial.println("[DIAG] MAX30102 (0x57) NOT FOUND");
    }

    Wire.beginTransmission(0x3C);
    if (Wire.endTransmission() == 0) {
        Serial.println("[DIAG] SSD1306 (0x3C) RESPONDING!");
    } else {
        Serial.println("[DIAG] SSD1306 (0x3C) NOT FOUND");
    }

    Serial.println("[DIAG] Done. Check wiring and restart.");
}

void loop() {
    delay(10000);
    Serial.println("[DIAG] Still alive...");
}