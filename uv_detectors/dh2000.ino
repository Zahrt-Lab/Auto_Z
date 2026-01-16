// ------------------------------------------------------------------------------
// Software: AUTO_ZAHRT
// Copyright: (C) 2025 by Professor Andrew Zahrt
// This software is the intellectual property of Professor Andrew Zahrt
// Contributions by graduate students Scott Laverty are acknowledged.
// All rights reserved.
// ------------------------------------------------------------------------------

// The purpose of this script is to control the TTL of the light box
// so we can turn the light source off on the UV detector
// this is template code before we incorporate it into the AutoZahrt_v3 general methods.

// This code will serve the following purposes
// 1) This will be used to calibrate instruments between runs to ensure accuracy between runs
// 2) Will be used as a fail/safe if the UV-detector is detecting unusual readings that aren't excepected it's likely an issue and the this will allow the equipment and light source to turn off
// 3) In experiments that initially need the UV-detector but during the run doesn't need the use of the UV-detector for 30 minutes

class DH2000Controller {
public:
  DH2000Controller(int pinShutter, int pinHalogenLamp, int pinDeuteriumLamp,
                 int ledRed, int ledYellow, int ledGreen,
                 unsigned long togglePulseMs = 100,
                 bool ledsEnabled = true)
    : _pinShutter(pinShutter),
      _pinHalogenLamp(pinHalogenLamp),
      _pinDeuteriumLamp(pinDeuteriumLamp),
      _ledRed(ledRed),
      _ledYellow(ledYellow),
      _ledGreen(ledGreen),
      _togglePulseMs(togglePulseMs),
      _ledsEnabled(ledsEnabled) {}

  void begin() {
    pinMode(_pinShutter, OUTPUT);
    pinMode(_pinHalogenLamp, OUTPUT);
    pinMode(_pinDeuteriumLamp, OUTPUT);

    if (_ledsEnabled) {
      pinMode(_ledRed, OUTPUT);
      pinMode(_ledYellow, OUTPUT);
      pinMode(_ledGreen, OUTPUT);
      digitalWrite(_ledRed, LOW);
      digitalWrite(_ledYellow, LOW);
      digitalWrite(_ledGreen, LOW);
    }

    digitalWrite(_pinShutter, LOW);
    digitalWrite(_pinHalogenLamp, LOW);
    digitalWrite(_pinDeuteriumLamp, LOW);

    _shutterIsOpen = false;
    _halogenOn = false;
    _deuteriumOn = false;
    updateStatusLEDs();
  }

  void shutterOpen()  {
    digitalWrite(_pinShutter, HIGH);
    _shutterIsOpen = true;
    updateStatusLEDs();
  }
  void shutterClose() {
    digitalWrite(_pinShutter, LOW);
    _shutterIsOpen = false;
    updateStatusLEDs();
  }
  void toggleHalogenLamp() {
    pulseToggle(_pinHalogenLamp);
    _halogenOn = !_halogenOn;
    updateStatusLEDs();
  }
  void toggleDeuteriumLamp() {
    pulseToggle(_pinDeuteriumLamp);
    _deuteriumOn = !_deuteriumOn;
    updateStatusLEDs();
  }
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
  void disableLeds() {
    _ledsEnabled = false;
    pinMode(_ledRed, OUTPUT);
    pinMode(_ledYellow, OUTPUT);
    pinMode(_ledGreen, OUTPUT);
    digitalWrite(_ledRed, LOW);
    digitalWrite(_ledYellow, LOW);
    digitalWrite(_ledGreen, LOW);
  }


private:
  int _pinShutter;
  int _pinHalogenLamp;
  int _pinDeuteriumLamp;
  int _ledRed;
  int _ledYellow;
  int _ledGreen;
  unsigned long _togglePulseMs;
  bool _shutterIsOpen = false;
  bool _halogenOn = false;
  bool _deuteriumOn = false;
  bool _ledsEnabled = true;
  void pulseToggle(int pin) {
    digitalWrite(pin, LOW);
    delay(10);
    digitalWrite(pin, HIGH);
    delay(_togglePulseMs);
    digitalWrite(pin, LOW);
    delay(10);
  }
  void setOnlyLed(int pinHigh) {
    if (!_ledsEnabled) return;
    digitalWrite(_ledRed,    (pinHigh == _ledRed) ? HIGH : LOW);
    digitalWrite(_ledYellow, (pinHigh == _ledYellow) ? HIGH : LOW);
    digitalWrite(_ledGreen,  (pinHigh == _ledGreen) ? HIGH : LOW);
  }
  void updateStatusLEDs() {
    bool anyLampOn = _halogenOn && _deuteriumOn;
    if (!anyLampOn && !_shutterIsOpen) {
      // Both lamps OFF and shutter OFF (closed) -> RED
      setOnlyLed(_ledRed);
    } else if (anyLampOn && !_shutterIsOpen) {
      // Lamp(s) ON and shutter OFF (closed) -> YELLOW
      setOnlyLed(_ledYellow);
    } else if (anyLampOn && _shutterIsOpen) {
      // Lamp(s) ON and shutter ON (open) -> GREEN
      setOnlyLed(_ledGreen);
    } else {
      // Shutter open but lamps off (not specified) -> choose a safe default
      setOnlyLed(_ledRed);
    }
  }
};
// ----- Instantiate the object (your Arduino pins) -----
// Control pins: shutter=3, halogen toggle=5, deuterium toggle=6
// Status LEDs: red=9, yellow=10, green=11
DH2000Controller dh2000(3, 5, 6, 9, 10, 11);
// ----- Arduino sketch entry points -----
void setup() {
  Serial.begin(115200);
  dh2000.begin();
  Serial.println("DH2000 controller ready. Commands: o/c/h/d/x");
}
void loop() {
  if (!Serial.available()) return;
  char cmd = Serial.read();
  if (cmd == 'o') dh2000.shutterOpen();
  if (cmd == 'c') dh2000.shutterClose();
  if (cmd == 'h') dh2000.toggleHalogenLamp();
  if (cmd == 'd') dh2000.toggleDeuteriumLamp();
  if (cmd == 'x') dh2000.calibrationCycle(2000, 1000);
  if (cmd == 'l') dh2000.disableLeds();
  Serial.println("OK");
}