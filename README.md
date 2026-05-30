# Thermodynamics Lab

![Build Status](https://github.com/arunishrajput/thermodynamics-lab/actions/workflows/build-exe.yml/badge.svg)
![Latest Release](https://img.shields.io/github/v/release/arunishrajput/thermodynamics-lab?label=download&color=00d4ff)

An Arduino-connected dashboard that **proves the 1st Law of Thermodynamics** in real time — measures electrical energy input and heat absorbed by water, then computes efficiency and verifies energy conservation.

---

## Download

<a href="https://github.com/arunishrajput/thermodynamics-lab/releases/latest/download/ThermodynamicsLab.exe">
  <img src="https://img.shields.io/badge/Download-Windows%20.exe-0078d4?style=for-the-badge&logo=windows&logoColor=white"/>
</a>
&nbsp;
<a href="https://github.com/arunishrajput/thermodynamics-lab/releases/latest/download/ThermodynamicsLab-macOS.zip">
  <img src="https://img.shields.io/badge/Download-macOS%20.app-555555?style=for-the-badge&logo=apple&logoColor=white"/>
</a>

> **macOS first run:** unzip → right-click `ThermodynamicsLab.app` → **Open** → click Open again.  
> This is a one-time Gatekeeper bypass because the app is not signed with an Apple certificate.

---

## What It Does

The dashboard connects to an Arduino over USB serial and continuously reads:

- Water **temperature** (DS18B20 sensor)
- Heater **voltage** and **current** (voltage sensor + ACS712)
- Computed **power** and cumulative **energy** from the Arduino

When you run an experiment (press **START** then **STOP**), the dashboard calculates:

| Symbol | Formula | Meaning |
|--------|---------|---------|
| **W** | `ΔE_electrical = ∫P dt` | Electrical energy supplied to the heater |
| **Q** | `m · c · ΔT` | Heat absorbed by the water |
| **Loss** | `W − Q` | Energy dissipated to the environment |
| **η** | `Q / W × 100 %` | Thermal conversion efficiency |

The **1st Law of Thermodynamics** states that energy is conserved:

> **W = Q + Q_loss**
>
> Electrical energy in = useful heat absorbed + environmental losses

The dashboard shows this balance live and prints a verdict after each experiment.

---

## Hardware

| Component | Purpose |
|-----------|---------|
| Arduino (Uno / Nano / Mega) | Reads all sensors, sends CSV over USB serial at 9600 baud |
| DS18B20 temperature sensor | Measures water temperature (°C) |
| ACS712 current sensor | Measures current through the heater (A) |
| Voltage sensor module | Measures 12V supply voltage (V) |
| 40W ceramic cartridge heater | Heats the water (powered by 12V DC adapter) |
| 12V DC adapter | Power source for the heater |

**Wiring diagram:** Arduino reads DS18B20 for temperature, uses the voltage divider module to sense the 12V rail, and uses the ACS712 to sense current through the heater circuit. The Arduino computes `P = V × I` and integrates it over time to get energy.

---

## Arduino Serial Format

The dashboard expects a comma-separated line over serial at **9600 baud**:

```
temperature,voltage,current,power,energy,heater_status
```

Example:
```
24.5,11.87,3.21,38.10,1245.0,1
```

| Field | Type | Unit |
|-------|------|------|
| temperature | float | °C |
| voltage | float | V |
| current | float | A |
| power | float | W |
| energy | float | J (cumulative since Arduino boot) |
| heater_status | int (0/1) | 1 = heater ON |

---

## Dashboard Features

- **Live sensor cards** — Temperature, Voltage, Current, Power, Energy, Heater status
- **Real-time temperature graph** with glow fill
- **Experiment mode** — START captures T₀ and E₀; STOP captures T₁ and E₁
- **Results panel** — shows T₀, T₁, ΔT, Q, W, and η
- **1st Law analysis** — prints W = Q + Loss with a colour-coded verdict
- **Auto-detects** the Arduino COM/serial port on both Windows and macOS

---

## Running from Source

```bash
git clone https://github.com/arunishrajput/thermodynamics-lab.git
cd thermodynamics-lab

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
python dashboard.py
```

---

## Building the Executable Locally

**Windows:**
```bat
build_windows.bat
# Output: dist\ThermodynamicsLab.exe
```

**macOS:**
```bash
./build_mac.sh
# Output: dist/ThermodynamicsLab-macOS.zip
```

---

## Project Context

This project was built to experimentally verify the **1st Law of Thermodynamics** — that energy cannot be created or destroyed, only converted. By heating a known mass of water with a measured electrical input and tracking the temperature rise, we can directly compare work input (W) with heat output (Q) and account for losses to the environment.
