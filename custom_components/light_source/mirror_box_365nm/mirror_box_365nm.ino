// ------------------------------------------------------------------------------
// Software: AUTO_ZAHRT
// Copyright: (C) 2026 by Professor Andrew Zahrt
// This software is the intellectual property of Professor Andrew Zahrt
// Contributions by graduate students Scott Laverty and Joao are acknowledged.
// Acknowledgments for the original Arduino sketch this is based on go to: Ari B
// All rights reserved.
// ------------------------------------------------------------------------------
//
// wiring for mirror box 365 nm lamp controller:
// Peltier SSR control       -> Arduino D2
// Light relay #1 control    -> Arduino D13
// Light relay #2 control    -> Arduino D12
// Dimmer PWM control        -> Arduino D5
// Thermocouple amp outputs  -> Arduino A0, A1, A2, A3
// Common GND                -> Arduino GND
//
// Notes:
// - Thermocouple amps assumed AD8495 style: 1.25V offset @ 0°C, 5mV/°C slope
// - Keeps original "-10" temperature offset as TEMP_OFFSET_C
// - Relay polarity varies by module. Default here assumes HIGH=ON, LOW=OFF.
//   If your relay module is active-LOW, flip RELAY_ON_LEVEL and RELAY_OFF_LEVEL.

#include <Arduino.h>

class MirrorBox365nmController {
public:
  MirrorBox365nmController(uint8_t pinPeltierRelay,
                           uint8_t pinLightRelay1,
                           uint8_t pinLightRelay2,
                           uint8_t pinDimmerPWM,
                           uint8_t pinThermocouple1,
                           uint8_t pinThermocouple2,
                           uint8_t pinThermocouple3,
                           uint8_t pinThermocouple4)
    : _pinPeltierRelay(pinPeltierRelay),
      _pinLightRelay1(pinLightRelay1),
      _pinLightRelay2(pinLightRelay2),
      _pinDimmerPWM(pinDimmerPWM)
  {
    _tcPins[0] = pinThermocouple1; // TC1: peltier cold side
    _tcPins[1] = pinThermocouple2; // TC2: peltier hot side
    _tcPins[2] = pinThermocouple3; // TC3: light 1 temp
    _tcPins[3] = pinThermocouple4; // TC4: light 2 temp
  }

  void begin(unsigned long samplePeriodMs = 1000) {
    _samplePeriodMs = samplePeriodMs;

    // Set pin modes for relays and dimmer
    pinMode(_pinPeltierRelay, OUTPUT);
    pinMode(_pinLightRelay1, OUTPUT);
    pinMode(_pinLightRelay2, OUTPUT);
    pinMode(_pinDimmerPWM, OUTPUT);

    // Known-safe startup: everything OFF, dimmest
    relayWrite(_pinPeltierRelay, false);
    relayWrite(_pinLightRelay1, false);
    relayWrite(_pinLightRelay2, false);
    setDimmer(255);

    // Returns the amount of time that has passed since the program started, in milliseconds.
    _lastSampleMs = millis();

    Serial.println(F("Temp1,Temp2,Temp3,Temp4"));
  }

  void update() {
    // Handle any incoming serial commands, expects s, off, or dim <0-255>
    handleSerialCommands();

    // Check current time against last sample time to enforce sample period to check if any updates are needed. 
    const unsigned long now = millis();
    if (now - _lastSampleMs < _samplePeriodMs) return; // not time yet
    _lastSampleMs = now;

    // Read te,perature value of the peltiers cold side, hot side, light 1, and light 2, in that order. 
    readAllTemperaturesC();
    printTemperaturesCsv();
    enforceSafetyLogic();
  }

  // Sets the dimmer value (0-255) for the light source. 0 is brightest, 255 is dimmest.
  void setDimmer(uint8_t value) {
    _dimmerValue = value;
    analogWrite(_pinDimmerPWM, _dimmerValue);
  }

  // Forces all outputs OFF (safety command)
  void turnOff() {
    relayWrite(_pinPeltierRelay, false);
    relayWrite(_pinLightRelay1, false);
    relayWrite(_pinLightRelay2, false);
    setDimmer(255);
  }

  // Prints the current status of all outputs and temperatures to the serial monitor.
  void printStatus() const {
    Serial.print(F("Peltier: ")); Serial.print(relayIsOn(_pinPeltierRelay) ? F("ON") : F("OFF"));
    Serial.print(F(" | Light1: ")); Serial.print(relayIsOn(_pinLightRelay1) ? F("ON") : F("OFF"));
    Serial.print(F(" | Light2: ")); Serial.print(relayIsOn(_pinLightRelay2) ? F("ON") : F("OFF"));
    Serial.print(F(" | DimmerPWM: ")); Serial.println(_dimmerValue);

    Serial.print(F("Temps(C): "));
    Serial.print(_tempC[0]); Serial.print('\t');
    Serial.print(_tempC[1]); Serial.print('\t');
    Serial.print(_tempC[2]); Serial.print('\t');
    Serial.println(_tempC[3]);
  }

private:
  // ----------------------------
  // Hardware pins
  // ----------------------------
  uint8_t _pinPeltierRelay;
  uint8_t _pinLightRelay1;
  uint8_t _pinLightRelay2;
  uint8_t _pinDimmerPWM;
  uint8_t _tcPins[4];

  // ----------------------------
  // Timing
  // ----------------------------
  // Sample period checks temperature every 1 second by default for updates
  unsigned long _samplePeriodMs = 1000;
  unsigned long _lastSampleMs = 0;

  // ----------------------------
  // State
  // ----------------------------
  // Temperatures in °C for TemperatureController1, TemperatureController2, TemperatureController3, TemperatureController4
  float _tempC[4] = {0, 0, 0, 0};
  uint8_t _dimmerValue = 255;

  // ----------------------------
  // Thresholds + hysteresis
  // ----------------------------
  // The too cold and hot thresholds for the the peltier module to operate at safe temperature ranges
  const float _peltMinColdC = 3.0f;
  const float _peltMaxHotC  = 56.0f;
  // The maximum safe temperature for the light sources, above which they will be turned off until they cool down
  const float _lightMaxHotC = 57.0f;

  // Hysteresis margins to prevent rapid on/off cycling around thresholds
  // For example, if the light max hot threshold is 57°C with a hysteresis of 3°C, the light will turn off after exceeding 57°C, but will not turn back on until it cools down below 54°C.
  const float _lightHysteresisC = 3.0f;
  const float _peltColdHysteresisC = 3.0f;
  const float _peltHotResetMarginC = 15.0f;

  // ----------------------------
  // ADC / conversion constants
  // ----------------------------
  static constexpr float ADC_REF_V = 5.0f;
  static constexpr int   ADC_MAX   = 1023;          // 10-bit AVR ADC
  static constexpr float ADC_TO_V  = ADC_REF_V / (float)ADC_MAX;

  static constexpr float TC_OFFSET_V = 1.25f;       // AD8495 offset
  static constexpr float TC_SLOPE_V_PER_C = 0.005f; // 5mV/°C
  static constexpr float TEMP_OFFSET_C = -10.0f;    // preserve your old "-10"

  // ----------------------------
  // Relay polarity
  // ----------------------------
  static constexpr uint8_t RELAY_ON_LEVEL  = HIGH;
  static constexpr uint8_t RELAY_OFF_LEVEL = LOW;

  // ----------------------------
  // Temperature read
  // ----------------------------
  void readAllTemperaturesC() {
    for (int k = 0; k < 4; k++) {
      _tempC[k] = readTemperatureC(_tcPins[k]);
    }
  }

  // Reads a single thermocouple voltage from the specified analog pin and converts it to temperature in °C using the AD8495 characteristics and the TEMP_OFFSET_C.
  float readTemperatureC(uint8_t analogPin) {
    (void)analogRead(analogPin); // dummy read for mux settling
    const int raw = analogRead(analogPin);

    // Convert raw analog reading to voltage, then convert to temperature using the AD8495 formula: Temp(°C) = (V_out - Offset) / Slope + TEMP_OFFSET_C
    const float voltage = raw * ADC_TO_V;
    const float tempC = ((voltage - TC_OFFSET_V) / TC_SLOPE_V_PER_C) + TEMP_OFFSET_C;
    return tempC;
  }

  void printTemperaturesCsv() const {
    Serial.print(_tempC[0], 2); Serial.print(',');
    Serial.print(_tempC[1], 2); Serial.print(',');
    Serial.print(_tempC[2], 2); Serial.print(',');
    Serial.println(_tempC[3], 2);
  }

  // ----------------------------
  // Safety logic (matches original sketch)
  // ----------------------------
  void enforceSafetyLogic() {
    const float tCold = _tempC[0];
    const float tHot  = _tempC[1];
    const float tL1   = _tempC[2];
    const float tL2   = _tempC[3];

    // Light 1
    if (tL1 > _lightMaxHotC) {
      relayWrite(_pinLightRelay1, false);
    }
    if (!relayIsOn(_pinLightRelay1) && tL1 < (_lightMaxHotC - _lightHysteresisC)) {
      relayWrite(_pinLightRelay1, true);
    }

    // Light 2
    if (tL2 > _lightMaxHotC) {
      relayWrite(_pinLightRelay2, false);
    }
    if (!relayIsOn(_pinLightRelay2) && tL2 < (_lightMaxHotC - _lightHysteresisC)) {
      relayWrite(_pinLightRelay2, true);
    }

    // Peltier
    if (tCold < _peltMinColdC || tHot > _peltMaxHotC) {
      relayWrite(_pinPeltierRelay, false);
    }
    if (!relayIsOn(_pinPeltierRelay) &&
        tCold > (_peltMinColdC + _peltColdHysteresisC) &&
        tHot  < (_peltMaxHotC - _peltHotResetMarginC)) {
      relayWrite(_pinPeltierRelay, true);
    }
  }

  // ----------------------------
  // Relay helpers
  // ----------------------------
  void relayWrite(uint8_t pin, bool on) {
    digitalWrite(pin, on ? RELAY_ON_LEVEL : RELAY_OFF_LEVEL);
  }

  bool relayIsOn(uint8_t pin) const {
    return digitalRead(pin) == RELAY_ON_LEVEL;
  }

  // ----------------------------
  // Serial commands
  // ----------------------------
  void handleSerialCommands() {
    if (!Serial.available()) return;
    
    // Reads a line of input from the serial monitor, trimming whitespace, and processes commands:
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    if (line == "s") {
      printStatus();
      return;
    }

    if (line == "off") {
      turnOff();
      Serial.println(F("OK (all outputs turned OFF)"));
      return;
    }

    if (line.startsWith("dim")) {
      int spaceIndex = line.indexOf(' ');
      if (spaceIndex < 0) {
        Serial.println(F("ERR (use: dim 0-255)"));
        return;
      }

      int value = line.substring(spaceIndex + 1).toInt();
      if (value < 0) value = 0;
      if (value > 255) value = 255;

      setDimmer((uint8_t)value);
      Serial.println(F("OK (dimmer set)"));
      return;
    }

    Serial.println(F("ERR (unknown cmd). Valid: s | off | dim 0-255"));
  }
};

// ----- Instantiate with wiring pins -----
MirrorBox365nmController mirrorBox(
  2,   // Peltier relay
  13,  // Light relay 1
  12,  // Light relay 2
  5,   // Dimmer PWM
  A0,  // TC1 (cold side)
  A1,  // TC2 (hot side)
  A2,  // TC3 (light 1)
  A3   // TC4 (light 2)
);

// ----- Arduino entry points -----
void setup() {
  Serial.begin(9600);
  mirrorBox.begin(1000);

  Serial.println(F("Mirror Box 365nm controller ready. Commands:"));
  Serial.println(F("  s           -> print status"));
  Serial.println(F("  off         -> turn off all outputs (safety)"));
  Serial.println(F("  dim <0-255> -> set dimmer (0=brightest, 255=dimmest)"));
}

void loop() {
  mirrorBox.update();
}
