#include <SoftwareSerial.h>

// ============================================================
// RS-485 (MAX485) wiring
// ============================================================
static const uint8_t PIN_RO = 10; // MAX485 RO -> Arduino RX
static const uint8_t PIN_DI = 11; // MAX485 DI -> Arduino TX
static const uint8_t PIN_RE = 2;  // MAX485 RE (active LOW)
static const uint8_t PIN_DE = 3;  // MAX485 DE (active HIGH)

SoftwareSerial pumpBus(PIN_RO, PIN_DI);

// ============================================================
// Pump / bus settings
// ============================================================
static const long PUMP_BAUD = 9600;
static const char PUMP_A_ADDR[] = "/1"; // Pump A address 1
static const char PUMP_B_ADDR[] = "/2"; // Pump B address 2

// Timing
static const uint16_t BETWEEN_CMDS_MS = 30;
static const uint16_t READ_TIMEOUT_MS = 1200;

// ============================================================
// Configurable pump parameters (set via Serial)  (NO String)
// ============================================================
static uint16_t param_initial_speed  = 8000;  // aspirate speed
static uint32_t param_initial_volume = 192000; // stroke volume
static uint16_t param_output_speed   = 4000;  // dispense speed
static uint16_t param_input_speed    = 8000;  // refill speed
static uint16_t param_jDispense      = 800;   // j-dispense threshold

// ============================================================
// Command input buffer (NO String)
// ============================================================
static char inputBuf[64]; // command line buffer

// ============================================================
// Program buffers (static, no stack blowups)
// ============================================================
static char progA_buf[140];
static char progB_buf[110];

// ============================================================
// RS-485 direction control
// ============================================================
static inline void rs485_set_tx() {
  digitalWrite(PIN_RE, HIGH);
  digitalWrite(PIN_DE, HIGH);
  delayMicroseconds(50);
}

static inline void rs485_set_rx() {
  pumpBus.flush();
  digitalWrite(PIN_DE, LOW);
  digitalWrite(PIN_RE, LOW);
  delayMicroseconds(50);
}

static inline void clearRxBuffer() {
  while (pumpBus.available()) (void)pumpBus.read();
}

// DT framing: "/addr" + command-string + CR
static void sendDT(const char* addr, const char* core) {
  clearRxBuffer();
  rs485_set_tx();
  pumpBus.print(addr);
  pumpBus.print(core);
  pumpBus.print('\r');
  pumpBus.flush();     // <-- ensure bytes are out while still TX
  rs485_set_rx();
}

// Read reply into fixed buffer (NO String). Returns pointer to static buffer.
static const char* readReply(uint16_t timeout_ms = READ_TIMEOUT_MS) {
  static char reply[96];
  size_t i = 0;
  uint32_t t0 = millis();

  while ((millis() - t0) < timeout_ms && i < (sizeof(reply) - 1)) {
    while (pumpBus.available() && i < (sizeof(reply) - 1)) {
      reply[i++] = (char)pumpBus.read();
    }
  }
  reply[i] = '\0';
  return reply;
}

// Send command and print request/response
static void sendAndPrint(const __FlashStringHelper* label,
                         const char* addr,
                         const char* core,
                         uint16_t timeout = READ_TIMEOUT_MS) {
  Serial.print(label);
  Serial.print(F(" -> "));
  Serial.print(addr);
  Serial.println(core);

  sendDT(addr, core);

  const char* rep = readReply(timeout);
  Serial.print(label);
  Serial.print(F(" <- "));
  Serial.println(rep);

  delay(BETWEEN_CMDS_MS);
}

// ============================================================
// Build EEPROM program strings (NO String)
// ============================================================

static void buildPumpAProgram_restart(char* buf, size_t bufSize,
                              const char* eeprom_addr,
                              uint16_t initial_speed,
                              uint32_t initial_volume,
                              uint16_t output_speed,
                              uint16_t jDispense_val,
                              uint16_t input_speed) {
  // Program A (from your previous sprintf, but with numbers + snprintf)
  snprintf(buf, bufSize,
           "%sN2J7V%uIA%luOV%uj%uA0IV%uA%luJ7OV%uj%ugH0A0IV%uA%luJ7OV%uj%uGR",
           eeprom_addr,
           (unsigned)initial_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val);
}

static void buildPumpBProgram_restart(char* buf, size_t bufSize,
                              const char* eeprom_addr,
                              uint16_t initial_speed,
                              uint32_t initial_volume,
                              uint16_t output_speed,
                              uint16_t jDispense_val,
                              uint16_t input_speed) {
  // Program B (from your previous sprintf, but with numbers + snprintf)
  snprintf(buf, bufSize,
           "%sN2J7V%uIA%luOV%uj%ugH0A0IV%uA%luJ7OV%uj%uGR",
           eeprom_addr,
           (unsigned)initial_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val);
}

static void buildPumpAProgram(char* buf, size_t bufSize,
                              const char* eeprom_addr,
                              uint16_t initial_speed,
                              uint32_t initial_volume,
                              uint16_t output_speed,
                              uint16_t jDispense_val,
                              uint16_t input_speed) {
  // Program A (from your previous sprintf, but with numbers + snprintf)
  snprintf(buf, bufSize,
           "%sN2J7V%uOV%uj%uA0IV%uA%luJ7OV%uj%ugH0A0IV%uA%luJ7OV%uj%uGR",
           eeprom_addr,
           (unsigned)initial_speed,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val);
}

static void buildPumpBProgram(char* buf, size_t bufSize,
                              const char* eeprom_addr,
                              uint16_t initial_speed,
                              uint32_t initial_volume,
                              uint16_t output_speed,
                              uint16_t jDispense_val,
                              uint16_t input_speed) {
  // Program B (from your previous sprintf, but with numbers + snprintf)
  snprintf(buf, bufSize,
           "%sN2J7V%uIA%luOV%uj%ugH0A0IV%uA%luJ7OV%uj%uGR",
           eeprom_addr,
           (unsigned)initial_speed,
           (unsigned long) initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val,
           (unsigned)input_speed,
           (unsigned long)initial_volume,
           (unsigned)output_speed,
           (unsigned)jDispense_val);
}

static void buildCustomProgram(char* buf, size_t bufSize,
                               const char* eeprom_addr,
                               const char* program_body) {
  snprintf(buf, bufSize, "%s%s", eeprom_addr, program_body);
}

// ============================================================
//Store command variables parsing

static const char* addrFromSelector(char sel) {
  sel = (char)toupper((unsigned char)sel);
  if (sel == 'A') return PUMP_A_ADDR;
  if (sel == 'B') return PUMP_B_ADDR;
  return nullptr; // invalid
}

// Returns pointer to first non-space after the nth token.
// Example: line="store A s0N2J7..." -> restAfterToken(line, 2) points at "s0N2J7..."
static char* restAfterToken(char* line, int tokenIndex) {
  // tokenIndex = 0 means start of line; tokenIndex = 1 means after first token, etc.
  char* p = line;
  int t = 0;

  // Skip leading spaces
  while (*p == ' ' || *p == '\t') p++;

  while (*p && t < tokenIndex) {
    // Skip current token
    while (*p && *p != ' ' && *p != '\t') p++;
    // Skip spaces
    while (*p == ' ' || *p == '\t') p++;
    t++;
  }
  return (*p) ? p : nullptr;
}

// ============================================================
// Send comands to pump

static void cmd_send(char* line) {
  // line starts with "send ..."
  char* pSel = restAfterToken(line, 1);   // token 1 = selector
  char* pCore = restAfterToken(line, 2);  // token 2 = core

  if (!pSel || !pCore || !*pSel || !*pCore) {
    Serial.println(F("Usage: send <A|B|*> <core>   e.g. send A Q"));
    return;
  }

  char sel = pSel[0];
  if (sel == '*') {
    sendAndPrint(F("SEND A"), PUMP_A_ADDR, pCore, 1500);
    sendAndPrint(F("SEND B"), PUMP_B_ADDR, pCore, 1500);
    return;
  }

  const char* addr = addrFromSelector(sel);
  if (!addr) {
    Serial.println(F("Bad pump selector. Use A, B, or *."));
    return;
  }

  sendAndPrint(F("SEND"), addr, pCore, 1500);
}

// ============================================================
// UI printing (all strings in FLASH using F())
// ============================================================

static void printCurrentParams() {
  Serial.println(F("--- Current Parameters ---"));
  Serial.print(F("  initial_speed:  "));  Serial.println(param_initial_speed);
  Serial.print(F("  initial_volume: "));  Serial.println(param_initial_volume);
  Serial.print(F("  output_speed:   "));  Serial.println(param_output_speed);
  Serial.print(F("  input_speed:    "));  Serial.println(param_input_speed);
  Serial.print(F("  jDispense:      "));  Serial.println(param_jDispense);
  Serial.println(F("--------------------------"));
}

static void printHelp() {
  Serial.println(F("=== Available Commands ==="));
  Serial.println(F("  initial_speed <value>   - Set aspirate speed (e.g., initial_speed 2000)"));
  Serial.println(F("  initial_volume <value>  - Set stroke volume (e.g., initial_volume 24000)"));
  Serial.println(F("  output_speed <value>    - Set dispense speed (e.g., output_speed 1000)"));
  Serial.println(F("  input_speed <value>     - Set refill speed (e.g., input_speed 2000)"));
  Serial.println(F("  jDispense <value>       - Set j-dispense threshold (e.g., jDispense 100)"));
  Serial.println(F("  params                  - Show current parameters"));
  Serial.println(F("  initialize              - Send Z (home) once to both pumps (do this only when needed)"));
  Serial.println(F("  start                   - Program and run both pumps"));
  Serial.println(F("  fill_A                  - Fill pump A only with initial refill"));
  Serial.println(F("  restart                 - Program and run both pumps with initial refill"));
  Serial.println(F("  send <A|B|*> <core>     - Send raw DT command core (e.g. send A Q, send * ZR)"));
  Serial.println(F("  stop                    - Stop both pumps"));
  Serial.println(F("  status                  - Query pump status"));
  Serial.println(F("  init_status             - Query the initialization status. It prints 0 if not initialized; 1 if initialized"));
  Serial.println(F("  help                    - Show this help"));
  Serial.println(F("==========================="));
}

// ============================================================
// Serial command parsing (NO String)
// ============================================================

static inline bool startsWith(const char* s, const char* prefix) {
  while (*prefix) {
    if (*s++ != *prefix++) return false;
  }
  return true;
}

static void trimWhitespace(char* s) {
  // Trim leading
  char* p = s;
  while (*p == ' ' || *p == '\t' || *p == '\r') p++;
  if (p != s) memmove(s, p, strlen(p) + 1);

  // Trim trailing
  size_t n = strlen(s);
  while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t' || s[n - 1] == '\r')) {
    s[n - 1] = '\0';
    n--;
  }
}

static bool parseU16AfterSpace(const char* line, uint16_t& out) {
  const char* sp = strchr(line, ' ');
  if (!sp) return false;
  while (*sp == ' ') sp++;
  if (*sp == '\0') return false;
  long v = atol(sp);
  if (v < 0 || v > 65535) return false;
  out = (uint16_t)v;
  return true;
}

static bool parseU32AfterSpace(const char* line, uint32_t& out) {
  const char* sp = strchr(line, ' ');
  if (!sp) return false;
  while (*sp == ' ') sp++;
  if (*sp == '\0') return false;
  unsigned long v = strtoul(sp, nullptr, 10);
  out = (uint32_t)v;
  return true;
}

// Read a line from Serial into inputBuf. Returns true if a full line read.
static bool readLineFromSerial() {
  if (Serial.available() == 0) return false;

  size_t n = Serial.readBytesUntil('\n', inputBuf, sizeof(inputBuf) - 1);
  inputBuf[n] = '\0';
  trimWhitespace(inputBuf);
  return (strlen(inputBuf) > 0);
}

// ============================================================
// Init status code

static int parseInitFlagFromReply(const char* rep) {
  // Returns 0 or 1 if found, -1 if unknown
  const char* p0 = strchr(rep, '`');   // backtick character
  if (!p0) return -1;
  char c = *(p0 + 1);
  if (c == '0') return 0;
  if (c == '1') return 1;
  return -1;
}
// ============================================================

// ============================================================
// Main
// ============================================================

void setup() {
  pinMode(PIN_RE, OUTPUT);
  pinMode(PIN_DE, OUTPUT);
  rs485_set_rx();

  Serial.begin(115200);
  pumpBus.begin(PUMP_BAUD);

  Serial.println(F("Programming C24000 dual-pump continuous flow"));
  Serial.println(F("Arduino set up complete. Type 'help' for commands."));
  printHelp();
  printCurrentParams();
}

void loop() {
  if (!readLineFromSerial()) return;

  Serial.print(F("> "));
  Serial.println(inputBuf);

  // --- Parameter setting commands ---
  if (startsWith(inputBuf, "initial_speed ")) {
    uint16_t v;
    if (parseU16AfterSpace(inputBuf, v)) {
      param_initial_speed = v;
      Serial.print(F("Set initial_speed = "));
      Serial.println(param_initial_speed);
    } else {
      Serial.println(F("Bad value. Example: initial_speed 2000"));
    }
  }
  else if (startsWith(inputBuf, "initial_volume ")) {
    uint32_t v;
    if (parseU32AfterSpace(inputBuf, v)) {
      param_initial_volume = v;
      Serial.print(F("Set initial_volume = "));
      Serial.println(param_initial_volume);
    } else {
      Serial.println(F("Bad value. Example: initial_volume 24000"));
    }
  }
  else if (startsWith(inputBuf, "output_speed ")) {
    uint16_t v;
    if (parseU16AfterSpace(inputBuf, v)) {
      param_output_speed = v;
      Serial.print(F("Set output_speed = "));
      Serial.println(param_output_speed);
    } else {
      Serial.println(F("Bad value. Example: output_speed 1000"));
    }
  }
  else if (startsWith(inputBuf, "input_speed ")) {
    uint16_t v;
    if (parseU16AfterSpace(inputBuf, v)) {
      param_input_speed = v;
      Serial.print(F("Set input_speed = "));
      Serial.println(param_input_speed);
    } else {
      Serial.println(F("Bad value. Example: input_speed 2000"));
    }
  }
  else if (startsWith(inputBuf, "jDispense ")) {
    uint16_t v;
    if (parseU16AfterSpace(inputBuf, v)) {
      param_jDispense = v;
      Serial.print(F("Set jDispense = "));
      Serial.println(param_jDispense);
    } else {
      Serial.println(F("Bad value. Example: jDispense 100"));
    }
  }
  // --- Send custom command ---
  else if (startsWith(inputBuf, "send ")) {
  cmd_send(inputBuf);
  }  

  // --- Show current parameters ---
  else if (strcmp(inputBuf, "params") == 0) {
    printCurrentParams();
  }
  // --- Initialize ---
  else if (strcmp(inputBuf, "initialize") == 0) {
    Serial.println(F("Initializing both pumps (mechanical home)..."));
    // Use ZR so you get a reply back
    sendAndPrint(F("INIT A"), PUMP_A_ADDR, "N2YZR", 2500);
    sendAndPrint(F("INIT B"), PUMP_B_ADDR, "N2YZR", 2500);
    Serial.println(F("Initialization done. (This homed plunger + valve.)"));
    Serial.println(F("INIT_DONE"));
  }
  // --- Help ---
  else if (strcmp(inputBuf, "help") == 0) {
    printHelp();
  }
  // --- Start: program pumps and run ---
  else if (strcmp(inputBuf, "start") == 0) {
    Serial.println(F("Programming pumps with current parameters..."));
    printCurrentParams();

    // Build program strings using current parameters (static char buffers)
    buildPumpAProgram(
      progA_buf, sizeof(progA_buf),
      "s0",
      param_initial_speed,
      param_initial_volume,
      param_output_speed,
      param_jDispense,
      param_input_speed
    );

    buildPumpBProgram(
      progB_buf, sizeof(progB_buf),
      "s1",
      param_initial_speed,
      param_initial_volume,
      param_output_speed,
      param_jDispense,
      param_input_speed
    );

    Serial.print(F("PROG_A: "));
    Serial.println(progA_buf);
    Serial.print(F("PROG_B: "));
    Serial.println(progB_buf);

    // 1) Store programs in EEPROM
    sendAndPrint(F("STORE A"), PUMP_A_ADDR, progA_buf, 2000);
    sendAndPrint(F("STORE B"), PUMP_B_ADDR, progB_buf, 2000);

    // 2) Execute stored strings
    // Start Pump B FIRST so it is waiting on H0 when Pump A begins dispensing
    sendAndPrint(F("RUN B"), PUMP_B_ADDR, "e1R", 800);
    delay(200);
    sendAndPrint(F("RUN A"), PUMP_A_ADDR, "e0R", 800);

    Serial.println(F("Pumps started! Use 'status' to check or 'stop' to halt."));
  }

  else if (strcmp(inputBuf, "restart") == 0) {
    Serial.println(F("Programming pumps with current parameters..."));
    printCurrentParams();

    // Build program strings using current parameters (static char buffers)
    buildPumpAProgram_restart(
      progA_buf, sizeof(progA_buf),
      "s0",
      param_initial_speed,
      param_initial_volume,
      param_output_speed,
      param_jDispense,
      param_input_speed
    );

    buildPumpBProgram_restart(
      progB_buf, sizeof(progB_buf),
      "s1",
      param_initial_speed,
      param_initial_volume,
      param_output_speed,
      param_jDispense,
      param_input_speed
    );

    Serial.print(F("PROG_A: "));
    Serial.println(progA_buf);
    Serial.print(F("PROG_B: "));
    Serial.println(progB_buf);

    // 1) Store programs in EEPROM
    sendAndPrint(F("STORE A"), PUMP_A_ADDR, progA_buf, 2000);
    sendAndPrint(F("STORE B"), PUMP_B_ADDR, progB_buf, 2000);

    // 2) Execute stored strings
    // Start Pump B FIRST so it is waiting on H0 when Pump A begins dispensing
    sendAndPrint(F("RUN B"), PUMP_B_ADDR, "e1R", 800);
    delay(200);
    sendAndPrint(F("RUN A"), PUMP_A_ADDR, "e0R", 800);

    Serial.println(F("Pumps started with initial refill! Use 'status' to check or 'stop' to halt."));
  }
  else if (strcmp(inputBuf, "fill_A") == 0) {
    Serial.println(F("Filling pump A with initial refill..."));
    // Send command to pump A to perform initial refill
    sendAndPrint(F("FILL A"), PUMP_A_ADDR, "N2V8000IA192000R", 2000); // Example command, adjust as needed
    Serial.println(F("Pump A filled with initial refill."));
  }

    // --- Initialization status ---
  else if (strcmp(inputBuf, "init_status") == 0) {
    // Query pump A
    sendDT(PUMP_A_ADDR, "?19");
    const char* repA = readReply(1500);
    int a = parseInitFlagFromReply(repA);

    // Query pump B
    sendDT(PUMP_B_ADDR, "?19");
    const char* repB = readReply(1500);
    int b = parseInitFlagFromReply(repB);

    // Optional debug: show raw + hex
    Serial.print(F("INIT_A_RAW: ")); Serial.println(repA);
    //printHexLine("INIT_A_HEX:", repA);
    Serial.print(F("INIT_B_RAW: ")); Serial.println(repB);
    //printHexLine("INIT_B_HEX:", repB);

    // Clean machine-readable one-liner for Python
    Serial.print(F("INIT_STATUS A="));
    Serial.print(a);
    Serial.print(F(" B="));
    Serial.println(b);

    // If either is unknown, also emit an error marker
    if (a < 0 || b < 0) {
      Serial.println(F("INIT_STATUS_ERROR"));
    }
  }

  // --- Status ---
  else if (strcmp(inputBuf, "status") == 0) {
    sendAndPrint(F("STATUS A"), PUMP_A_ADDR, "Q", 500);
    sendAndPrint(F("STATUS B"), PUMP_B_ADDR, "Q", 500);
  }
  // --- Stop ---
  else if (strcmp(inputBuf, "stop") == 0) {
    sendAndPrint(F("STOP A"), PUMP_A_ADDR, "T", 500);
    sendAndPrint(F("STOP B"), PUMP_B_ADDR, "T", 500);
    Serial.println(F("Pumps stopped."));
  }
  // --- Unknown command ---
  else {
    Serial.println(F("Unknown command. Type 'help' for available commands."));
  }
}
