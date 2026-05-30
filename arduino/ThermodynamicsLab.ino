#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// =========================
// LCD  (I2C addr 0x27)
// =========================
LiquidCrystal_I2C lcd(0x27, 16, 2);

// =========================
// DS18B20  (data → D2)
// =========================
#define ONE_WIRE_BUS 2

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// =========================
// Analog pins
// =========================
const int currentPin = A1;   // ACS712 output
const int voltagePin = A2;   // Voltage divider output

// =========================
// State
// =========================
float temperature = 0;
float voltage     = 0;
float current     = 0;
float power       = 0;
float energy      = 0;        // cumulative joules since boot

bool heaterOn = false;

unsigned long previousTime;

// =========================
// Setup
// =========================
void setup()
{
    Serial.begin(9600);

    sensors.begin();

    lcd.init();
    lcd.backlight();

    lcd.setCursor(0, 0);
    lcd.print("SMART THERMO");
    lcd.setCursor(0, 1);
    lcd.print("Starting...");

    delay(2000);

    previousTime = millis();
}

// =========================
// Main Loop
// =========================
void loop()
{
    // ── Temperature ──────────────────────────────────────
    sensors.requestTemperatures();
    temperature = sensors.getTempCByIndex(0);

    // ── Voltage ──────────────────────────────────────────
    // Voltage divider ratio: R1=30kΩ, R2=7.5kΩ  →  ×5 scale
    int voltageRaw    = analogRead(voltagePin);
    float sensorVoltage = voltageRaw * (5.0 / 1023.0);
    voltage = sensorVoltage * 5.0;

    // ── Current ──────────────────────────────────────────
    // ACS712-5A: sensitivity = 0.185 V/A, zero-current output ≈ 2.5 V
    int currentRaw      = analogRead(currentPin);
    float currentVoltage = currentRaw * (5.0 / 1023.0);
    current = (currentVoltage - 2.5) / 0.185;

    if (current < 0) current = -current;   // rectify noise sign

    // Noise gate — below 0.30 A treat as zero / heater off
    if (current < 0.30)
    {
        current  = 0;
        heaterOn = false;
    }
    else
    {
        heaterOn = true;
    }

    // ── Power & Energy ────────────────────────────────────
    power = voltage * current;

    unsigned long currentTime = millis();
    float deltaTime = (currentTime - previousTime) / 1000.0;
    energy += power * deltaTime;
    previousTime = currentTime;

    // ── Serial output (Python dashboard) ─────────────────
    // Format: temperature,voltage,current,power,energy,heater_status
    Serial.print(temperature); Serial.print(",");
    Serial.print(voltage);     Serial.print(",");
    Serial.print(current);     Serial.print(",");
    Serial.print(power);       Serial.print(",");
    Serial.print(energy);      Serial.print(",");
    Serial.println(heaterOn ? 1 : 0);

    // ── LCD screen 1 — Temperature & Heater status ────────
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Temp:");
    lcd.print(temperature, 1);
    lcd.print("C");
    lcd.setCursor(0, 1);
    lcd.print(heaterOn ? "Heater: ON " : "Heater: OFF");
    delay(2000);

    // ── LCD screen 2 — Voltage, Current, Power ───────────
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("V:");
    lcd.print(voltage, 1);
    lcd.setCursor(8, 0);
    lcd.print("I:");
    lcd.print(current, 2);
    lcd.setCursor(0, 1);
    lcd.print("P:");
    lcd.print(power, 1);
    lcd.print("W");
    delay(2000);

    // ── LCD screen 3 — Cumulative energy ─────────────────
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Energy:");
    lcd.setCursor(0, 1);
    lcd.print(energy, 0);
    lcd.print(" J");
    delay(2000);
}
