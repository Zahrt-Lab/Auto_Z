// ================================
// DH-2000 Arduino Control Code
// ================================

// ---- Pin assignments ----
const uint8_t PIN_DEUTERIUM = 3;   // DB15 Pin 2
const uint8_t PIN_HALOGEN   = 5;   // DB15 Pin 3
const uint8_t PIN_SHUTTER_EN = 6;  // Transistor -> DB15 Pin 13

// ---- Timing ----
const unsigned int PULSE_MS = 20;  // ≥10 ms required, 20 ms is safe

// ================================
// Helper Functions
// ================================

// Toggle Deuterium or Halogen (edge-triggered)
void pulseToggle(uint8_t pin) {
  digitalWrite(pin, HIGH);
  delay(PULSE_MS);
  digitalWrite(pin, LOW);
}

// Shutter control (level-triggered via transistor)
void shutterOpen() {
  digitalWrite(PIN_SHUTTER_EN, HIGH);  // Enable 5V → shutter OPEN
}

void shutterClose() {
  digitalWrite(PIN_SHUTTER_EN, LOW);   // Disable 5V → shutter CLOSED
}

// ================================
// Setup
// ================================
void setup() {
  pinMode(PIN_DEUTERIUM, OUTPUT);
  pinMode(PIN_HALOGEN, OUTPUT);
  pinMode(PIN_SHUTTER_EN, OUTPUT);

  // Ensure known safe states
  digitalWrite(PIN_DEUTERIUM, LOW);
  digitalWrite(PIN_HALOGEN, LOW);
  digitalWrite(PIN_SHUTTER_EN, LOW);

  Serial.begin(9600);
  Serial.println("DH-2000 controller initialized");
}

// ================================
// Main Loop (Demo Sequence)
// ================================
void loop() {

  // ---- Open shutter ----
  Serial.println("Opening shutter");
  shutterOpen();
  delay(500);

  // ---- Toggle Deuterium ON ----
  Serial.println("Toggling Deuterium");
  pulseToggle(PIN_DEUTERIUM);
  delay(2000);   // allow warm-up logic to begin

  // ---- Toggle Halogen ON ----
  Serial.println("Toggling Halogen");
  pulseToggle(PIN_HALOGEN);
  delay(5000);

  // ---- Close shutter ----
  Serial.println("Closing shutter");
  shutterClose();
  delay(3000);

  // ---- Toggle Halogen OFF ----
  Serial.println("Toggling Halogen OFF");
  pulseToggle(PIN_HALOGEN);
  delay(1000);

  // ---- Toggle Deuterium OFF ----
  Serial.println("Toggling Deuterium OFF");
  pulseToggle(PIN_DEUTERIUM);
  delay(5000);
}
