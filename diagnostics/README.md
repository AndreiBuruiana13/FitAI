# Hardware diagnostics

These original standalone sketches support hardware bring-up and debugging.

- `i2c/i2c_diag.ino`: Arduino I2C scan and bus recovery on GPIO6/GPIO7; checks the MPU6050, MAX30102 and SSD1306 addresses. Upload as a separate sketch.
- `oled/`: standalone PlatformIO project for display initialization and validation. Run `pio run` from this directory after installing PlatformIO.

They do not modify or replace `fitai_glove/src/main.cpp`. Local serial ports are chosen automatically or configured on the reader's machine. Device logs and captured measurements are not included.
