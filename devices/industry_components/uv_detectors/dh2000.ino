// ------------------------------------------------------------------------------
// Software: Auto_Z
// Copyright (c) 2026 Zahrt Research Group
//
// Contributions by Scott Laverty are acknowledged.
//
// Licensed under the MIT License. See the LICENSE file in the repository root.
// ------------------------------------------------------------------------------

// wiring for DH-2000 lamp controller (DB15 connector):
//   Arduino D3  -> DB15 Pin 13  (Shutter, LEVEL: HIGH=OPEN, LOW=CLOSE)
//   Arduino D5  -> DB15 Pin 3   (Halogen toggle, EDGE pulse)
//   Arduino D6  -> DB15 Pin 2   (Deuterium toggle, EDGE pulse)
//   Arduino GND -> DB15 Pin 10  (Shutter ground)
//   Arduino GND -> DB15 Pin 4   (Signal ground)

// Notes:
// - Halogen/Deuterium inputs are RISING-EDGE toggles (pulse HIGH then return LOW).
// - Shutter is a LEVEL input (hold HIGH to keep open).
// - LEDs are removed, so all LED logic is stripped.

// References:
// https://www.oceanoptics.com/wp-content/uploads/2024/05/dh-2000-installation-and-operation-manual.pdf

class DH2000Controller {
public:
  DH2000Controller(uint8_t pinShutterLevel,
                   uint8_t pinHalogenToggle,
                   uint8_t pinDeuteriumToggle,
                   unsigned long togglePulseMs = 20)
    : _pinShutter(pinShutterLevel),
      _pinHalogenLamp(pinHalogenToggle),
      _pinDeuteriumLamp(pinDeuteriumToggle),
      _togglePulseMs(togglePulseMs) {}

  void begin() {
    pinMode(_pinShutter, OUTPUT);
    pinMode(_pinHalogenLamp, OUTPUT);
    pinMode(_pinDeuteriumLamp, OUTPUT);

    // Known-safe startup states
    digitalWrite(_pinShutter, LOW);        // shutter CLOSED
    digitalWrite(_pinHalogenLamp, LOW);    // no pulses
    digitalWrite(_pinDeuteriumLamp, LOW);  // no pulses

    _shutterIsOpen = false;
    _halogenOn = false;     // "logical" state (we assume pulses work)
    _deuteriumOn = false;
  }

  // Shutter is LEVEL-controlled: HIGH=open, LOW=closed
  void shutterOpen()  {
    digitalWrite(_pinShutter, HIGH);
    _shutterIsOpen = true;
  }

  void shutterClose() {
    digitalWrite(_pinShutter, LOW);
    _shutterIsOpen = false;
  }

  // Lamps are EDGE-triggered toggles: send a clean rising pulse
  void toggleHalogenLamp() {
    pulseToggle(_pinHalogenLamp);
    _halogenOn = !_halogenOn;
  }

  void toggleDeuteriumLamp() {
    pulseToggle(_pinDeuteriumLamp);
    _deuteriumOn = !_deuteriumOn;
  }

  // Convenience helpers (optional)
  bool shutterIsOpen()   const { return _shutterIsOpen; }
  bool halogenIsOn()     const { return _halogenOn; }
  bool deuteriumIsOn()   const { return _deuteriumOn; }

  // Example calibration cycle (same behavior as before, no LEDs)
  void calibrationCycle(unsigned long warmupMs = 2000,
                        unsigned long measureMs = 1000) {
    shutterClose();
    delay(200);

    toggleHalogenLamp();
    delay(warmupMs);

    toggleDeuteriumLamp();
    delay(warmupMs);

    shutterOpen();
    delay(measureMs);

    shutterClose();
  }

private:
  uint8_t _pinShutter;
  uint8_t _pinHalogenLamp;
  uint8_t _pinDeuteriumLamp;

  unsigned long _togglePulseMs;

  bool _shutterIsOpen = false;
  bool _halogenOn = false;
  bool _deuteriumOn = false;

  // Send a single pulse: LOW -> HIGH -> LOW (rising edge triggers toggle)
  void pulseToggle(uint8_t pin) {
    digitalWrite(pin, LOW);
    delay(5);
    digitalWrite(pin, HIGH);
    delay(_togglePulseMs);  // 20ms default (safe)
    digitalWrite(pin, LOW);
    delay(5);
  }
};

// ----- Instantiate with your NEW wiring pins -----
// Shutter = D3, Halogen toggle = D5, Deuterium toggle = D6
DH2000Controller dh2000(3, 5, 6);

// ----- Arduino entry points -----
void setup() {
  Serial.begin(9600);
  dh2000.begin();
  Serial.println("DH2000 controller ready. Commands:");
  Serial.println("  o = shutter open");
  Serial.println("  c = shutter close");
  Serial.println("  h = toggle halogen");
  Serial.println("  d = toggle deuterium");
  Serial.println("  x = calibration cycle");
  Serial.println("  s = status");
}

void loop() {
  if (!Serial.available()) return;
  char cmd = Serial.read();

  if (cmd == 'o') dh2000.shutterOpen();
  else if (cmd == 'c') dh2000.shutterClose();
  else if (cmd == 'h') dh2000.toggleHalogenLamp();
  else if (cmd == 'd') dh2000.toggleDeuteriumLamp();
  else if (cmd == 'x') dh2000.calibrationCycle(2000, 1000);
  else if (cmd == 's') {
    Serial.print("Shutter: ");   Serial.println(dh2000.shutterIsOpen() ? "OPEN" : "CLOSED");
    Serial.print("Halogen: ");   Serial.println(dh2000.halogenIsOn() ? "ON" : "OFF");
    Serial.print("Deuterium: "); Serial.println(dh2000.deuteriumIsOn() ? "ON" : "OFF");
    return; // don't print OK twice
  }

  Serial.println("OK");
}