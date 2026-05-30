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

The dashboard shows this balance live and prints a colour-coded verdict after each experiment.

---

## Dashboard Features

| Feature | Details |
|---------|---------|
| **Live sensor cards** | Temperature, Voltage, Current, Power, Energy, Heater status — updated every second |
| **Real-time graph** | Temperature vs time with glow fill, auto-scales as data arrives |
| **Experiment mode** | START captures T₀ and E₀ · STOP captures T₁ and E₁ · live timer shows elapsed time |
| **Results panel** | T₀, T₁, ΔT, Q, W, η — scrollable so nothing is ever cropped |
| **1st Law analysis** | Full breakdown of W, Q, Loss and η with a colour-coded verdict |
| **Port selector** | Auto-detect Arduino or choose a specific COM/serial port from a dropdown |
| **Connection status** | Live indicator in the header; detects unexpected disconnects automatically |
| **Configurable parameters** | Set water mass and specific heat · liquid preset dropdown (Water, Ethanol, Motor Oil, Glycerin, Mercury, Custom) · values persist between sessions |
| **CSV export** | Save the full temperature vs time log to a `.csv` file |
| **Scrollable sidebar** | All panels (Connection, Live Sensors, Parameters) scroll independently so nothing is hidden at any window size |

---

## Hardware

| Component | Purpose |
|-----------|---------|
| Arduino (Uno / Nano / Mega) | Reads all sensors, sends CSV over USB serial at 9600 baud |
| DS18B20 temperature sensor | Measures water temperature (°C) |
| ACS712 current sensor | Measures current through the heater (A) |
| Voltage sensor module | Measures 12 V supply voltage (V) |
| 40 W ceramic cartridge heater | Heats the water (powered by 12 V DC adapter) |
| 12 V DC adapter | Power source for the heater |

**Wiring:** Arduino reads DS18B20 for temperature, uses the voltage divider module to sense the 12 V rail, and uses the ACS712 to sense current through the heater circuit. It computes `P = V × I` and integrates over time to get cumulative energy, then sends all six values over serial every ~1 s.

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
