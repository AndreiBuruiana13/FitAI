

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define I2C_SDA_PIN     6
#define I2C_SCL_PIN     7
#define OLED_I2C_ADDR   0x3C
#define LED_BUILTIN     8

Adafruit_SSD1306 display(128, 64, &Wire, -1);
bool i2cOK = false;

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);
  for (int i = 0; i < 9; i++) {
    digitalWrite(7, HIGH); delayMicroseconds(5);
    digitalWrite(7, LOW);  delayMicroseconds(5);
  }

  Wire.begin(6, 7);
  Wire.setClock(400000);
  delay(100);

  Serial.println("[BOOT] ESP32-C3 RISC-V initializing...");
  Serial.println("[I2C] Executing pre-flight line clearing...");

  byte deviceCount = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("[I2C] Target discovered at 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      deviceCount++;
    }
  }
  Serial.print("Total dispozitive gasite: ");
  Serial.println(deviceCount);

  if (deviceCount == 3) i2cOK = true;

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("[OLED] INIT FAILED - check wiring");
    pinMode(LED_BUILTIN, OUTPUT);
    while (true) {
      digitalWrite(LED_BUILTIN, HIGH); delay(250);
      digitalWrite(LED_BUILTIN, LOW);  delay(250);
    }
  }
  Serial.println("[OLED] Init OK");

  display.clearDisplay();
  display.display();

  display.clearDisplay();
  display.setTextColor(WHITE);

  display.setTextSize(2);
  display.setCursor(20, 0);
  display.println("FitAI");

  display.setTextSize(1);
  display.setCursor(10, 20);
  display.println("v1.0 - UTCB 2026");

  display.setCursor(4, 32);
  display.println("Sistem IoT Wearable");

  display.display();
  delay(2000);

  display.clearDisplay();
  display.display();
  Serial.println("[BOOT] Entering main loop...");
}

void loop() {
  static unsigned long lastOLED = 0;
  if (millis() - lastOLED >= 500) {
    lastOLED = millis();
    display.clearDisplay();
    display.setTextColor(WHITE);

    display.setTextSize(2);
    display.setCursor(0, 0);
    display.println("FitAI");

    display.setTextSize(1);
    display.setCursor(0, 18);
    display.print("Uptime: ");
    display.print(millis() / 1000);
    display.println("s");

    display.setCursor(0, 28);
    display.println(i2cOK ? "I2C: OK" : "I2C: ERR");

    display.setCursor(0, 38);
    display.print("Heap: ");
    display.print(ESP.getFreeHeap() / 1024);
    display.println("KB");

    display.display();
  }

  static unsigned long lastSerial = 0;
  if (millis() - lastSerial >= 2000) {
    lastSerial = millis();
    Serial.print("[STATUS] Uptime: ");
    Serial.print(millis() / 1000);
    Serial.print("s | Free heap: ");
    Serial.print(ESP.getFreeHeap());
    Serial.println(" bytes");
  }
}