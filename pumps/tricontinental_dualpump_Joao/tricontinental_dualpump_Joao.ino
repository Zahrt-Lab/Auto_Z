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
// Configurable pump parameters (set via Serial)
// -------------------------
String param_initial_speed = "2000";
String param_initial_volume = "24000";
String param_output_speed = "1000";
String param_input_speed = "2000";
String param_jDispense = "100";

// Helper function to parse "command value" and extract the value
String parseValue(const String& input) {
  int spaceIndex = input.indexOf(' ');
  if (spaceIndex > 0) {
    return input.substring(spaceIndex + 1);
  }
  return "";
}

void printCurrentParams() {
  Serial.println("--- Current Parameters ---");
  Serial.print("  initial_speed:  "); Serial.println(param_initial_speed);
  Serial.print("  initial_volume: "); Serial.println(param_initial_volume);
  Serial.print("  output_speed:   "); Serial.println(param_output_speed);
  Serial.print("  input_speed:    "); Serial.println(param_input_speed);
  Serial.print("  jDispense:      "); Serial.println(param_jDispense);
  Serial.println("--------------------------");
}

void printHelp() {
  Serial.println("=== Available Commands ===");
  Serial.println("  initial_speed <value>   - Set aspirate speed (e.g., initial_speed 2000)");
  Serial.println("  initial_volume <value>  - Set stroke volume (e.g., initial_volume 24000)");
  Serial.println("  output_speed <value>    - Set dispense speed (e.g., output_speed 1000)");
  Serial.println("  input_speed <value>     - Set refill speed (e.g., input_speed 2000)");
  Serial.println("  jDispense <value>       - Set j-dispense threshold (e.g., jDispense 100)");
  Serial.println("  params                  - Show current parameters");
  Serial.println("  initialize              - Send Z (home) once to both pumps (do this only when needed)");
  Serial.println("  start                   - Program and run both pumps");
  Serial.println("  stop                    - Stop both pumps");
  Serial.println("  status                  - Query pump status");
  Serial.println("  help                    - Show this help");
  Serial.println("===========================");
}

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

// Buffers for program strings (static to avoid stack issues)
static char progA_buf[150];
static char progB_buf[120];

// Create command for string program A
void buildPumpAProgram(
   char* buf,
   const char* eeprom_addr,
   const char* initial_speed,
   const char* initial_volume,
   const char* output_speed,
   const char* jDispense_val,
   const char* input_speed) {
  
  sprintf(buf, 
    "%sJ7V%sIA%sOV%sj%sA0IV%sA%sJ7OV%sj%sgH0A0IV%sA%sJ7OV%sj%sGR",
    eeprom_addr,
    initial_speed,
    initial_volume,
    output_speed,
    jDispense_val,
    input_speed,
    initial_volume,
    output_speed,
    jDispense_val,
    input_speed,
    initial_volume,
    output_speed,
    jDispense_val
  );
}
// Pump A (address 1), store in EEPROM location 0:
// static const char* PROG_A =
  //"s0J7ZV2000IA24000OV1000j100A0IV2000A24000J7OV1000j100gH0A0IV2000A24000J7OV1000j100GR";

// Create command for string program B
void buildPumpBProgram(
   char* buf,
   const char* eeprom_addr,
   const char* initial_speed,
   const char* initial_volume,
   const char* output_speed,
   const char* jDispense_val,
   const char* input_speed) {
  
  sprintf(buf,
    "%sJ7V%sIA%sOV%sj%sgH0A0IV%sA%sJ7OV%sj%sGR",
    eeprom_addr,
    initial_speed,
    initial_volume,
    output_speed,
    jDispense_val,
    input_speed,
    initial_volume,
    output_speed,
    jDispense_val
  );
}
// Pump B (address 2), store in EEPROM location 1:
// static const char* PROG_B =
 // "s1J7ZV2000IA24000OV1000j100gH0A0IV2000A24000J7OV1000j100GR";


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

  Serial.println("Programming C3000 dual-pump continuous flow");
  Serial.println("Arduino set up complete. Type 'help' for commands.");
  printHelp();
  printCurrentParams();
}

void loop() {
  if (Serial.available() == 0) return;
  
  String input = Serial.readStringUntil('\n');
  input.trim();  // Remove whitespace/newlines
  
  if (input.length() == 0) return;
  
  Serial.print("> "); Serial.println(input);

  // --- Parameter setting commands ---
  if (input.startsWith("initial_speed ")) {
    param_initial_speed = parseValue(input);
    Serial.print("Set initial_speed = "); Serial.println(param_initial_speed);
  }
  else if (input.startsWith("initial_volume ")) {
    param_initial_volume = parseValue(input);
    Serial.print("Set initial_volume = "); Serial.println(param_initial_volume);
  }
  else if (input.startsWith("output_speed ")) {
    param_output_speed = parseValue(input);
    Serial.print("Set output_speed = "); Serial.println(param_output_speed);
  }
  else if (input.startsWith("input_speed ")) {
    param_input_speed = parseValue(input);
    Serial.print("Set input_speed = "); Serial.println(param_input_speed);
  }
  else if (input.startsWith("jDispense ")) {
    param_jDispense = parseValue(input);
    Serial.print("Set jDispense = "); Serial.println(param_jDispense);
  }
  // --- Show current parameters ---
  else if (input.startsWith("params")) {
    printCurrentParams();
  }
    else if (input == "initialize") {
    Serial.println("Initializing both pumps (mechanical home)...");
    // Use ZR so you get a reply back
    sendAndPrint("INIT A", PUMP_A_ADDR, "ZR", 2500);
    sendAndPrint("INIT B", PUMP_B_ADDR, "ZR", 2500);
    Serial.println("Initialization done. (This homed plunger + valve.)");
  }
  // --- Help ---
  else if (input.startsWith("help")) {
    printHelp();
  }
  // --- Start: program pumps and run ---
  else if (input.startsWith("start")) {
    Serial.println("Programming pumps with current parameters...");
    printCurrentParams();
    
    // Build program strings using current parameters (using static char buffers)
    buildPumpAProgram(
      progA_buf,
      "s0",
      param_initial_speed.c_str(),
      param_initial_volume.c_str(),
      param_output_speed.c_str(),
      param_jDispense.c_str(),
      param_input_speed.c_str()
    );
    
    buildPumpBProgram(
      progB_buf,
      "s1",
      param_initial_speed.c_str(),
      param_initial_volume.c_str(),
      param_output_speed.c_str(),
      param_jDispense.c_str(),
      param_input_speed.c_str()
    );
    
    Serial.print("PROG_A: "); Serial.println(progA_buf);
    Serial.print("PROG_B: "); Serial.println(progB_buf);
    
    // 1) Store programs in EEPROM
    sendAndPrint("STORE A", PUMP_A_ADDR, progA_buf, 2000);
    sendAndPrint("STORE B", PUMP_B_ADDR, progB_buf, 2000);
    
    // 2) Execute stored strings
    // Start Pump B FIRST so it is waiting on H0 when Pump A begins dispensing
    sendAndPrint("RUN B", PUMP_B_ADDR, "e1R", 800);
    delay(200);
    sendAndPrint("RUN A", PUMP_A_ADDR, "e0R", 800);
    
    Serial.println("Pumps started! Use 'status' to check or 'stop' to halt.");
  }
  // --- Status ---
  else if (input.startsWith("status")) {
    sendAndPrint("STATUS A", PUMP_A_ADDR, "Q", 500);
    sendAndPrint("STATUS B", PUMP_B_ADDR, "Q", 500);
  }
  // --- Stop ---
  else if (input.startsWith("stop")) {
    sendAndPrint("STOP A", PUMP_A_ADDR, "T", 500);
    sendAndPrint("STOP B", PUMP_B_ADDR, "T", 500);
    Serial.println("Pumps stopped.");
  }
  // --- Unknown command ---
  else {
    Serial.println("Unknown command. Type 'help' for available commands.");
  }
}
