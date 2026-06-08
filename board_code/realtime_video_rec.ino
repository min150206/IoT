#include <Wire.h>
#include "soc/gpio_reg.h"



// --- GPIO PIN DEFINITIONS ---
#define PIN_SIOC   1
#define PIN_SIOD   2
#define PIN_VSYNC  3
#define PIN_WRST   4
#define PIN_WR     5
#define PIN_RCLK   6
#define PIN_RRST   7
#define PIN_OE     8



// Data pins must be sequential from GPIO 9 to 16 for hardware register optimization
#define D_START_PIN 9  // D0=9, D1=10, D2=11, D3=12, D4=13, D5=14, D6=15, D7=16


// OV7670 I2C (SCCB) Slave Address
#define OV7670_I2C_ADDR 0x21 


// Image resolution configured for VGA (640 x 480)
#define IMG_WIDTH  640
#define IMG_HEIGHT 480


// Function to write a byte to an OV7670 camera register via SCCB (I2C)
void writeRegister(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(OV7670_I2C_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
  delay(1);
}


// Function to initialize OV7670 internal registers for VGA YUV422 output
void initOV7670Registers() {
  writeRegister(0x12, 0x80); // COM7: Reset all registers to default
  delay(100);
  

  writeRegister(0x12, 0x00); // COM7: Select VGA mode and YUV422 output
  writeRegister(0x14, 0x1A); // COM10: Set PCLK, HREF, and automatic controls
  writeRegister(0x3C, 0x00); // COM12: Disable digital ripple filter
  writeRegister(0x11, 0x01); // CLKRC: Internal clock prescaler divider
  

  // Color matrix configuration for full range YUV
  writeRegister(0x40, 0xC0); // COM15: Set output range to 00-FF (Full Range)
  writeRegister(0x3D, 0x40); // COM13: Enable gamma and color matrix handling
}



void LED_off() { //Tắt cái LED dùm, đa tạ, thao tác với LED để từ từ tính
  rgbLedWrite(RGB_BUILTIN, 0, 0, 0);
}



void setup() {

  LED_off();

  Serial.begin(2000000); // 2Mbps because the image size is 640x480
  while (!Serial);
  Serial.println("\n--- Initializing OV7670 FIFO VGA Stream ---");

  // Configure FIFO control pins as OUTPUT
  pinMode(PIN_WRST, OUTPUT);
  pinMode(PIN_WR, OUTPUT);
  pinMode(PIN_RCLK, OUTPUT);
  pinMode(PIN_RRST, OUTPUT);
  pinMode(PIN_OE, OUTPUT);
  
  // Configure VSYNC as INPUT
  pinMode(PIN_VSYNC, INPUT);

  // Configure Data pins (GPIO 9 to 16) as INPUT
  for (int i = 0; i < 8; i++) {
    pinMode(D_START_PIN + i, INPUT);
  }

  // Set initial default logic states for FIFO control pins
  digitalWrite(PIN_WR, LOW);     // Disable writing to FIFO
  digitalWrite(PIN_OE, HIGH);    // Disable FIFO data outputs (High-Z mode)
  digitalWrite(PIN_RCLK, HIGH);  // Set clock idle state to HIGH
  digitalWrite(PIN_WRST, HIGH);
  digitalWrite(PIN_RRST, HIGH);

  // Initialize I2C interface for SCCB camera configuration
  Wire.begin(PIN_SIOD, PIN_SIOC, 100000); // SDA, SCL, 100kHz clock speed
  initOV7670Registers();
  
  Serial.println("Camera hardware configuration complete. Starting capture loop...");
}

void loop() {



  //Wait unitl the new frame boundary (VSYNC falling edge)
  while (digitalRead(PIN_VSYNC) == LOW);
  while (digitalRead(PIN_VSYNC) == HIGH);



  //Reset write pointer & enable FIFO write
  digitalWrite(PIN_WRST, LOW);
  digitalWrite(PIN_RCLK, LOW); digitalWrite(PIN_RCLK, HIGH); // Send dummy clock pulse to latch reset
  digitalWrite(PIN_WRST, HIGH);
  
  digitalWrite(PIN_WR, HIGH); // Open the write gate: Camera starts pushing pixel data into FIFO



  //Wait until the camera capture the full frame
  while (digitalRead(PIN_VSYNC) == LOW);
  
  digitalWrite(PIN_WR, LOW); // Instantly close the write gate to freeze data inside the FIFO



  //Prepare FIFO for read operation
  digitalWrite(PIN_RRST, LOW); // Reset FIFO read pointer to memory address 0
  digitalWrite(PIN_RCLK, LOW); digitalWrite(PIN_RCLK, HIGH); // Dummy clock pulse
  digitalWrite(PIN_RRST, HIGH);
  
  digitalWrite(PIN_OE, LOW); // Enable FIFO outputs to drive lines D0-D7

  Serial.println("--- START OF IMAGE ---");



//------------------------------------------------------------------------


  // High speed RCLK pixel read loop
  // In YUV422, each pixel consists of 2 sequential bytes. 
  // Byte 1 represents Y (Brightness/Grayscale). Byte 2 contains color components (U/V).
  // We extract Byte 1 for a fast grayscale matrix and discard Byte 2 to maximize performance.
  


  for (int y = 0; y < IMG_HEIGHT; y++) {
    for (int x = 0; x < IMG_WIDTH; x++) {
      
      // --- Read Byte 1: Grayscale Data (Y) ---
      digitalWrite(PIN_RCLK, LOW); // Pull RCLK low to prepare data on the bus
      
      // DIRECT REGISTER ACCESS: Read all 32 GPIO states at once instantly
      uint32_t gpio_reg_state = REG_READ(GPIO_IN_REG); 
      
      // Shift out the relevant bits (GPIO 9 to 16) and cast to a single byte
      uint8_t pixelByte = (uint8_t)((gpio_reg_state >> D_START_PIN) & 0xFF);
      
      digitalWrite(PIN_RCLK, HIGH); // Pull RCLK high to finalize first byte reading

      // --- Read Byte 2: Discard Chroma Data (U/V) to speed up frame processing ---
      digitalWrite(PIN_RCLK, LOW);
      // No register reading operation performed during this cycle to save clock cycles
      digitalWrite(PIN_RCLK, HIGH); // Pull RCLK high to finalize second byte reading

      // Print raw numerical byte stream to Serial
      Serial.print(pixelByte);
      if (x < IMG_WIDTH - 1) Serial.print(",");
    }
    Serial.println(); // Carriage return at the end of every row
  }

  Serial.println("--- END OF IMAGE ---");
  
  digitalWrite(PIN_OE, HIGH); // Put FIFO data lines back into safe High-Impedance mode

  delay(3000); // 3-second delay before processing the next VGA frame
}
