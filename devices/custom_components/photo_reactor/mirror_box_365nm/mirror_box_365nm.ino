//# ------------------------------------------------------------------------------
// Software: Auto_Z
// Copyright (c) 2026 Zahrt Research Group
//
// Contributions by Scott Laverty are acknowledged.
//
// Licensed under the MIT License. See the LICENSE file in the repository root.
// ------------------------------------------------------------------------------
//
// Wiring:
//   Light relay #1 -> D13      Light relay #2 -> D12
//   Dimmer PWM     -> D5       TC3 (light 1)  -> A2
//   TC4 (light 2)  -> A3       GND            -> GND
//
// TC1 (A0) and TC2 (A1) are nonfunctional — not used.
//
// Commands (newline-terminated):
//   s           -> print status (2 lines)
//   dim <0-255> -> set dimmer (0 = brightest, 255 = off), reply OK
//
// Streams TC3,TC4 temperatures as CSV every 1 second.

// --- Pins ---
const uint8_t PIN_LIGHT1 = 13;
const uint8_t PIN_LIGHT2 = 12;
const uint8_t PIN_DIMMER = 5;
const uint8_t PIN_TC3    = A2;
const uint8_t PIN_TC4    = A3;

// --- Thresholds (AD8495: 1.25V offset, 5mV/°C, -10°C board offset) ---
const float LIGHT_MAX_C    = 57.0f;
const float LIGHT_HYSTER_C = 3.0f;   // re-enable after cooling to (MAX - HYSTER)°C

// --- State ---
uint8_t dimmerValue = 255;
unsigned long lastSampleMs = 0;
const unsigned long SAMPLE_MS = 1000;

// --- Helpers ---
float readTempC(uint8_t pin) {
  analogRead(pin);                          // dummy read for mux settling
  float v = analogRead(pin) * (5.0f / 1023.0f);
  return (v - 1.25f) / 0.005f - 10.0f;
}

void setDimmer(uint8_t value) {
  dimmerValue = value;
  analogWrite(PIN_DIMMER, dimmerValue);
}

// --- Arduino entry points ---
void setup() {
  Serial.begin(9600);
  pinMode(PIN_LIGHT1, OUTPUT);
  pinMode(PIN_LIGHT2, OUTPUT);
  pinMode(PIN_DIMMER, OUTPUT);
  // Safe startup: lights off, dimmer at max (dimmest)
  digitalWrite(PIN_LIGHT1, LOW);
  digitalWrite(PIN_LIGHT2, LOW);
  setDimmer(255);
  lastSampleMs = millis();
  Serial.println(F("TC3_light1,TC4_light2"));
}

void loop() {
  // Serial commands
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line == "s") {
      float t3 = readTempC(PIN_TC3);
      float t4 = readTempC(PIN_TC4);
      Serial.print(F("Light1: ")); Serial.print(digitalRead(PIN_LIGHT1) ? F("ON") : F("OFF"));
      Serial.print(F(" | Light2: ")); Serial.print(digitalRead(PIN_LIGHT2) ? F("ON") : F("OFF"));
      Serial.print(F(" | DimmerPWM: ")); Serial.println(dimmerValue);
      Serial.print(F("Temps(C): ")); Serial.print(t3, 2); Serial.print('\t'); Serial.println(t4, 2);

    } else if (line.startsWith("dim")) {
      int sp = line.indexOf(' ');
      if (sp < 0) { Serial.println(F("ERR (use: dim 0-255)")); return; }
      int val = constrain(line.substring(sp + 1).toInt(), 0, 255);
      setDimmer((uint8_t)val);
      Serial.println(F("OK (dimmer set)"));

    } else if (line.length() > 0) {
      Serial.println(F("ERR (unknown cmd). Valid: s | dim 0-255"));
    }
  }

  // Temperature sample + light safety
  unsigned long now = millis();
  if (now - lastSampleMs < SAMPLE_MS) return;
  lastSampleMs = now;

  float t3 = readTempC(PIN_TC3);
  float t4 = readTempC(PIN_TC4);

  if (t3 > LIGHT_MAX_C)                                               digitalWrite(PIN_LIGHT1, LOW);
  else if (!digitalRead(PIN_LIGHT1) && t3 < LIGHT_MAX_C - LIGHT_HYSTER_C) digitalWrite(PIN_LIGHT1, HIGH);

  if (t4 > LIGHT_MAX_C)                                               digitalWrite(PIN_LIGHT2, LOW);
  else if (!digitalRead(PIN_LIGHT2) && t4 < LIGHT_MAX_C - LIGHT_HYSTER_C) digitalWrite(PIN_LIGHT2, HIGH);

  Serial.print(t3, 2); Serial.print(','); Serial.println(t4, 2);
}
