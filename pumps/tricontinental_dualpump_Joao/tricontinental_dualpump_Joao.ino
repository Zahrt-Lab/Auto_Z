#include <SoftwareSerial.h>

// -------------------------
// RS-485 (MAX485) wiring
// -------------------------
static const uint8_t PIN_RO = 10; // MAX485 RO -> Arduino RX
static const uint8_t PIN_DI = 11; // MAX485 DI -> Arduino TX
static const uint8_t PIN_RE = 2;  // MAX485 RE (active LOW)
static const uint8_t PIN_DE = 3;  // MAX485 DE (active HIGH)

// -------------------------
// Pump / bus settings
// -------------------------
static const long PUMP_BAUD = 9600;
static const char* PUMP_A_ADDR = "/1"; // Pump A address 1
static const char* PUMP_B_ADDR = "/2"; // Pump B address 2

SoftwareSerial pumpBus(PIN_RO, PIN_DI);

// Timing
static const uint16_t BETWEEN_CMDS_MS = 30;
static const uint16_t READ_TIMEOUT_MS = 1200;

// -------------------------
// RS-485 direction control
// -------------------------
void rs485_set_tx() {
  digitalWrite(PIN_RE, HIGH);
  digitalWrite(PIN_DE, HIGH);
  delayMicroseconds(50);
}

void rs485_set_rx() {
  pumpBus.flush();
  digitalWrite(PIN_DE, LOW);
  digitalWrite(PIN_RE, LOW);
  delayMicroseconds(50);
}

void clearRxBuffer() {
  while (pumpBus.available()) (void)pumpBus.read();
}

// DT framing: "/addr" + command-string + CR
void sendDT(const char* addr, const String& core) {
  String msg = String(addr) + core + "\r";
  clearRxBuffer();
  rs485_set_tx();
  pumpBus.print(msg);
  rs485_set_rx();
}

String readReply(uint16_t timeout_ms = READ_TIMEOUT_MS) {
  String r;
  uint32_t t0 = millis();
  while (millis() - t0 < timeout_ms) {
    while (pumpBus.available()) r += char(pumpBus.read());
  }
  return r;
}

void sendAndPrint(const char* label, const char* addr, const String& core, uint16_t timeout = READ_TIMEOUT_MS) {
  Serial.print(label); Serial.print(" -> "); Serial.println(String(addr) + core);
  sendDT(addr, core);
  String rep = readReply(timeout);
  Serial.print(label); Serial.print(" <- "); Serial.println(rep);
  delay(BETWEEN_CMDS_MS);
}

// -------------------------
// Chapter 9 C3000 continuous flow EEPROM strings
// (verbatim from manual example)
// -------------------------
// Pump A (address 1), store in EEPROM location 0:
static const char* PROG_A =
  "s0J7ZV2000IA24000OV1000j100A0IV2000A24000J7OV1000j100gH0A0IV2000A24000J7OV1000j100GR";


// Pump B (address 2), store in EEPROM location 1:
static const char* PROG_B =
  "s1J7ZV2000IA24000OV1000j100gH0A0IV2000A24000J7OV1000j100GR";


// Notes on what these do (from manual):
// - J7: set aux outputs high initially; j100: when position <= 10, set outputs low (state 0)
// - V2000 aspirate, V1000 dispense; A3000 full-stroke aspirate, A0 dispense
// - H0: wait for trigger from other pump
// - g ... G: loop forever
// See manual Chapter 9 breakdown. :contentReference[oaicite:3]{index=3}

// -------------------------
// Main
// -------------------------
void setup() {
  pinMode(PIN_RE, OUTPUT);
  pinMode(PIN_DE, OUTPUT);
  rs485_set_rx();

  Serial.begin(115200);
  pumpBus.begin(PUMP_BAUD);

  Serial.println("Programming C3000 dual-pump continuous flow (Chapter 9)...");

  // 1) Load program strings into EEPROM
  // EEPROM storage uses s<n>...R (string length limit applies, but the manual’s strings are valid examples). :contentReference[oaicite:4]{index=4}
  sendAndPrint("STORE A", PUMP_A_ADDR, PROG_A, 2000);
  sendAndPrint("STORE B", PUMP_B_ADDR, PROG_B, 2000);

  // 2) Execute stored strings.
  // Start Pump B FIRST so it is waiting on H0 when Pump A begins dispensing.
  // Execute program string stored in EEPROM uses e<n>R. :contentReference[oaicite:5]{index=5}
  sendAndPrint("RUN B", PUMP_B_ADDR, "e1R", 800);
  delay(200);
  sendAndPrint("RUN A", PUMP_A_ADDR, "e0R", 800);

  Serial.println("Running. Pumps should now alternate dispense/refill using aux trigger wiring.");
}

void loop() {
  // Nothing needed: pumps are running their internal programs.
  // Optional: you can poll Q here for status/diagnostics if you want.
}
