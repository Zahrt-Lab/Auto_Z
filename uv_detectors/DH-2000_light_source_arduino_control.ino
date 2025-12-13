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

const int PIN_SHUTTER = 7;  // DB15 Pin 13 (level control)
const int PIN_DEUT    = 8;  // DB15 Pin 2  (toggle)
const int PIN_HAL     = 9;  // DB15 Pin 3  (toggle)

void pulseToggle(int pin) {
  digitalWrite(pin, LOW);
  delay(5);
  digitalWrite(pin, HIGH);   // rising edge toggles lamp state
  delay(20);
  digitalWrite(pin, LOW);
  delay(5);
}

void setup() {
  pinMode(PIN_SHUTTER, OUTPUT);
  pinMode(PIN_DEUT, OUTPUT);
  pinMode(PIN_HAL, OUTPUT);

  // Close shutter first for safety
  digitalWrite(PIN_SHUTTER, LOW);

  // --- TURN BOTH LAMPS OFF ---
  pulseToggle(PIN_DEUT);  // toggle Deuterium OFF
  pulseToggle(PIN_HAL);   // toggle Halogen OFF
}

void loop() {
  // Turn halogen ON
  pulseToggle(PIN_HAL);
  delay(5000);

  // Turn halogen OFF
  pulseToggle(PIN_HAL);
  delay(5000);
}

