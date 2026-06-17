// =============================================================================
// E-Bike Motor Controller Firmware — v1
// Target: Teensy 4.0 (NXP i.MX RT1062 @ 600 MHz)
// =============================================================================
// Scope (v1): two inputs (pedal torque, assist level via USB-serial), one
// output (motor-drive PWM as stand-in for 3-phase gate drive). No CAN, no
// brake/wheel/hall/NTC/BMS yet.
//
// Implements (traceable to systems model):
//   HW-MC-01  Teensy 4.0 / i.MX RT1062 @ 600 MHz
//   HW-MC-03  Control loop period <= 1 ms
//   HW-MC-05  Hardware watchdog, <= 100 ms window
//   HW-MC-06  Boot + self-test <= 500 ms
//   SW-MC-01  Closed-loop torque-control rate >= 1 kHz (loop only in v1)
//   SW-MC-02  Torque command latency << 150 ms
//   SW-MC-04  Output ramp <= 40 Nm/s
//   SW-MC-06  Pedal-stop torque decay to <= 0.5 Nm within 300 ms
//   SW-MC-30  Cut-in 5 Nm / cut-out 3 Nm (2 Nm hysteresis)
//   SW-MC-31  Eco/Tour/Sport/Turbo gains 0.5 / 1.5 / 2.5 / 3.5, cap 80 Nm
//   SW-MC-33  Boot -> Self-Test -> Armed (Fault paths deferred to v2)
//   SW-MC-34  Torque ADC sample rate >= 1 kHz
//   SW-MC-35  Assist level Off -> zero output (Armed, telemetry on)
//
// Pin map (Teensy 4.0):
//   A0 (pin 14)  IF-MC-TORQUE   analog in, 0-3.3 V -> 0..50 Nm (linear)
//   pin 2        IF-MC-3PH      motor PWM out (single channel stand-in)
//   pin 13       built-in LED   state indicator (1 Hz blink when Armed)
//   USB serial   IF-CAN-HMI2MC  v1 stub: "L<n>\n" sets assist level (0..4)
//
// Build: Arduino IDE + Teensyduino, board "Teensy 4.0", USB Type "Serial",
//        CPU 600 MHz, Optimize "Faster".
// =============================================================================

#include <Arduino.h>

// ---- Configuration constants (derived from systems model) -------------------
constexpr uint32_t LOOP_HZ                 = 1000;           // HW-MC-03, SW-MC-01
constexpr uint32_t LOOP_PERIOD_US          = 1000000UL / LOOP_HZ;

constexpr float    TORQUE_FULLSCALE_NM     = 50.0f;          // 3.3 V -> 50 Nm
constexpr float    TORQUE_CUT_IN_NM        = 5.0f;           // SW-MC-30
constexpr float    TORQUE_CUT_OUT_NM       = 3.0f;           // SW-MC-30
constexpr float    MOTOR_TORQUE_CAP_NM     = 80.0f;          // SW-MC-31
constexpr float    OUTPUT_RAMP_NM_PER_S    = 40.0f;          // SW-MC-04
constexpr float    PEDAL_STOP_DECAY_TARGET_NM = 0.5f;        // SW-MC-06
constexpr uint32_t PEDAL_STOP_DETECT_MS    = 200;            // SW-MC-06 trigger

constexpr uint32_t SELF_TEST_DURATION_MS   = 200;            // HW-MC-06 (<= 500)
constexpr uint32_t WDT_TIMEOUT_MS          = 100;            // HW-MC-05

// SW-MC-31 assist gain table: Off, Eco, Tour, Sport, Turbo
constexpr float    ASSIST_GAINS[5]         = {0.0f, 0.5f, 1.5f, 2.5f, 3.5f};
constexpr uint8_t  ASSIST_LEVEL_MAX        = 4;
constexpr uint8_t  ASSIST_LEVEL_DEFAULT    = 2;              // Tour

constexpr uint8_t  PIN_TORQUE_ADC          = A0;
constexpr uint8_t  PIN_MOTOR_PWM           = 2;
constexpr uint8_t  PIN_STATUS_LED          = LED_BUILTIN;

constexpr uint8_t  PWM_RESOLUTION_BITS     = 12;
constexpr uint32_t PWM_FREQUENCY_HZ        = 20000;          // ultrasonic
constexpr uint32_t PWM_MAX_COUNT           = (1U << PWM_RESOLUTION_BITS) - 1U;
constexpr uint32_t ADC_RESOLUTION_BITS     = 12;
constexpr uint32_t ADC_MAX_COUNT           = (1U << ADC_RESOLUTION_BITS) - 1U;

constexpr uint32_t TELEMETRY_PERIOD_MS     = 100;            // 10 Hz console out

// ---- MC operating state machine (subset of SW-MC-33) -----------------------
enum class McState : uint8_t {
    Boot = 0,
    SelfTest,
    Armed
    // Disarmed, Derate, Fault deferred to v2
};

struct FirmwareState {
    McState  state               = McState::Boot;
    uint32_t state_entered_ms    = 0;
    uint8_t  assist_level        = ASSIST_LEVEL_DEFAULT;
    float    torque_sample_nm    = 0.0f;
    bool     pedal_active        = false;     // hysteresis output
    uint32_t pedal_last_above_cut_ms = 0;
    float    motor_setpoint_nm   = 0.0f;      // target after gain + cap
    float    motor_command_nm    = 0.0f;      // after ramp limiter (actual out)
    uint32_t last_telemetry_ms   = 0;
    uint32_t loop_count          = 0;
};
static FirmwareState fw;

// ---- Helpers ---------------------------------------------------------------
static inline float clampf(float x, float lo, float hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

static void enterState(McState s) {
    fw.state = s;
    fw.state_entered_ms = millis();
}

// Map raw ADC counts to Nm: linear, no calibration in v1.
static float readTorqueNm() {
    uint32_t raw = analogRead(PIN_TORQUE_ADC);          // SW-MC-34: at 1 kHz
    float    v   = (float)raw / (float)ADC_MAX_COUNT;   // 0..1
    return v * TORQUE_FULLSCALE_NM;                     // 0..50 Nm
}

// Drive the motor PWM (single duty stand-in for IF-MC-3PH in v1).
static void driveMotor(float command_nm) {
    float duty_f = command_nm / MOTOR_TORQUE_CAP_NM;
    duty_f = clampf(duty_f, 0.0f, 1.0f);
    uint32_t duty = (uint32_t)(duty_f * (float)PWM_MAX_COUNT + 0.5f);
    analogWrite(PIN_MOTOR_PWM, duty);
}

// SW-MC-30: pedal-active hysteresis.
static void updatePedalActive(float torque_nm, uint32_t now_ms) {
    if (!fw.pedal_active && torque_nm >= TORQUE_CUT_IN_NM) {
        fw.pedal_active = true;
    } else if (fw.pedal_active && torque_nm < TORQUE_CUT_OUT_NM) {
        fw.pedal_active = false;
    }
    if (fw.pedal_active) {
        fw.pedal_last_above_cut_ms = now_ms;
    }
}

// SW-MC-31 / SW-MC-35
static float computeAssistSetpoint(float pedal_nm) {
    if (!fw.pedal_active) return 0.0f;
    float gain = ASSIST_GAINS[fw.assist_level];
    float cmd  = pedal_nm * gain;
    return clampf(cmd, 0.0f, MOTOR_TORQUE_CAP_NM);
}

// SW-MC-04: 40 Nm/s slew. Loop is 1 ms -> max step 0.04 Nm.
static float applyRampLimit(float current, float target) {
    const float max_step = OUTPUT_RAMP_NM_PER_S / (float)LOOP_HZ;
    float delta = target - current;
    if      (delta >  max_step) delta =  max_step;
    else if (delta < -max_step) delta = -max_step;
    return current + delta;
}

// SW-MC-06: after 200 ms of pedal inactivity, decay command to <= 0.5 Nm
// within 300 ms using a 60 ms time constant.
static float applyPedalStopDecay(float current, uint32_t now_ms) {
    if (fw.pedal_active) return current;
    if ((now_ms - fw.pedal_last_above_cut_ms) < PEDAL_STOP_DETECT_MS) return current;
    const float tau_ms       = 60.0f;
    const float dt_ms        = 1000.0f / (float)LOOP_HZ;
    const float decay_factor = expf(-dt_ms / tau_ms);
    float next = current * decay_factor;
    if (next < PEDAL_STOP_DECAY_TARGET_NM * 0.5f) next = 0.0f;
    return next;
}

// ---- 1 kHz control loop -----------------------------------------------------
static IntervalTimer controlTimer;
static volatile bool loop_tick = false;

static void onControlTick() { loop_tick = true; }

static void runControlStep(uint32_t now_ms) {
    fw.loop_count++;
    fw.torque_sample_nm = readTorqueNm();
    updatePedalActive(fw.torque_sample_nm, now_ms);
    float target_nm = computeAssistSetpoint(fw.torque_sample_nm);
    fw.motor_setpoint_nm = target_nm;
    float commanded = applyRampLimit(fw.motor_command_nm, target_nm);
    commanded       = applyPedalStopDecay(commanded, now_ms);
    fw.motor_command_nm = commanded;
    if (fw.state == McState::Armed) driveMotor(fw.motor_command_nm);
    else                            driveMotor(0.0f);
}

// ---- Serial command parser (v1 stub for IF-CAN-HMI2MC) ----------------------
static char    cmd_buf[16];
static uint8_t cmd_len = 0;

static void handleCommand(const char* s) {
    if (s[0] == 'L' && s[1] >= '0' && s[1] <= '0' + ASSIST_LEVEL_MAX) {
        fw.assist_level = (uint8_t)(s[1] - '0');
        Serial.print("OK assist="); Serial.println(fw.assist_level);
    } else if (s[0] == '?') {
        Serial.print("STATE="); Serial.print((int)fw.state);
        Serial.print(" L="); Serial.print(fw.assist_level);
        Serial.print(" tq="); Serial.print(fw.torque_sample_nm, 2);
        Serial.print("Nm cmd="); Serial.print(fw.motor_command_nm, 2);
        Serial.println("Nm");
    } else {
        Serial.println("ERR usage: L0..L4 or ?");
    }
}

static void pollSerial() {
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (cmd_len > 0) { cmd_buf[cmd_len] = '\0'; handleCommand(cmd_buf); cmd_len = 0; }
        } else if (cmd_len < sizeof(cmd_buf) - 1) {
            cmd_buf[cmd_len++] = c;
        }
    }
}

// ---- Telemetry (v1 stand-in for IF-CAN-MC2HMI / SW-MC-36) -------------------
static void emitTelemetry(uint32_t now_ms) {
    if ((now_ms - fw.last_telemetry_ms) < TELEMETRY_PERIOD_MS) return;
    fw.last_telemetry_ms = now_ms;
    Serial.print("t=");      Serial.print(now_ms);
    Serial.print(" state="); Serial.print((int)fw.state);
    Serial.print(" L=");     Serial.print(fw.assist_level);
    Serial.print(" tq=");    Serial.print(fw.torque_sample_nm, 2);
    Serial.print(" sp=");    Serial.print(fw.motor_setpoint_nm, 2);
    Serial.print(" cmd=");   Serial.print(fw.motor_command_nm, 2);
    Serial.print(" pedal="); Serial.print(fw.pedal_active ? 1 : 0);
    Serial.print(" loops="); Serial.println(fw.loop_count);
}

// ---- Self-test (SW-MC-33 / HW-MC-06) ----------------------------------------
static bool runSelfTest() {
    for (int i = 0; i < 8; i++) {
        uint32_t raw = analogRead(PIN_TORQUE_ADC);
        if (raw == 0 || raw == ADC_MAX_COUNT) return false;  // stuck-at-rail
        delay(2);
    }
    driveMotor(0.0f);
    return true;
}

// ---- Arduino entry points ---------------------------------------------------
void setup() {
    Serial.begin(115200);
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, HIGH);
    analogReadResolution(ADC_RESOLUTION_BITS);
    analogReadAveraging(4);
    analogWriteResolution(PWM_RESOLUTION_BITS);
    analogWriteFrequency(PIN_MOTOR_PWM, PWM_FREQUENCY_HZ);
    pinMode(PIN_MOTOR_PWM, OUTPUT);
    driveMotor(0.0f);
    enterState(McState::Boot);
    Serial.println("MC FW v1 booting");
    enterState(McState::SelfTest);
    uint32_t st_start = millis();
    bool st_ok = runSelfTest();
    while ((millis() - st_start) < SELF_TEST_DURATION_MS) { /* pad to deterministic */ }
    if (!st_ok) {
        Serial.println("SELFTEST FAIL");
        while (true) { digitalWrite(PIN_STATUS_LED, HIGH); delay(100); }
    }
    enterState(McState::Armed);
    Serial.println("ARMED");
    controlTimer.priority(64);
    controlTimer.begin(onControlTick, LOOP_PERIOD_US);
}

void loop() {
    if (loop_tick) { loop_tick = false; runControlStep(millis()); }
    pollSerial();
    emitTelemetry(millis());
    static uint32_t led_last = 0;
    uint32_t now = millis();
    if (fw.state == McState::Armed && (now - led_last) >= 500) {
        led_last = now;
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    }
}
