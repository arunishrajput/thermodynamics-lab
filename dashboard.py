import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import json
import csv
import os
from tkinter import filedialog
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── Config persistence ────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".thermodynamics-lab.json")

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(update):
    cfg = load_config()
    cfg.update(update)
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ── Serial utilities ──────────────────────────────────────────────────────────
BAUD = 9600

def get_port_list():
    devices = [p.device for p in serial.tools.list_ports.comports()]
    return ["Auto-detect"] + devices

def _auto_detect():
    keywords = ("arduino", "ch340", "cp210", "ftdi", "usb serial", "usbserial")
    for p in serial.tools.list_ports.comports():
        if any(k in (p.description or "").lower() for k in keywords):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None

# ── Physics ───────────────────────────────────────────────────────────────────
WATER_MASS    = 0.3
SPECIFIC_HEAT = 4186

LIQUID_PRESETS = {
    "Water":      4186,
    "Ethanol":    2440,
    "Motor Oil":  1900,
    "Glycerin":   2410,
    "Mercury":     139,
    "Custom":     None,   # user fills manually
}

# ── Shared state ──────────────────────────────────────────────────────────────
ser            = None
serial_lock    = threading.Lock()
connected      = False
last_data_time = 0.0

temperature    = 0.0
voltage        = 0.0
current        = 0.0
power          = 0.0
energy         = 0.0
heater_status  = 0

experiment_running = False
experiment_start_t = 0.0
initial_temp       = 0.0
final_temp         = 0.0
initial_energy     = 0.0
final_energy       = 0.0
efficiency         = 0.0
heat_gained        = 0.0

temp_history = deque(maxlen=300)
time_history = deque(maxlen=300)
start_time   = time.time()

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#080d18"
CARD     = "#0d1424"
CARD2    = "#101828"
BORDER   = "#1c2a42"
CYAN     = "#00d4ff"
PURPLE   = "#a78bfa"
AMBER    = "#fbbf24"
GREEN    = "#34d399"
RED      = "#f87171"
TEXT_MID = "#94a3b8"
TEXT_DIM = "#475569"

# ── App ───────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.title("Thermodynamics Lab · 1st Law Verification")
app.geometry("1420x900")
app.configure(fg_color=BG)

# ── Header ────────────────────────────────────────────────────────────────────
hdr = ctk.CTkFrame(app, fg_color=CARD, corner_radius=0, height=54)
hdr.pack(fill="x")
hdr.pack_propagate(False)

ctk.CTkLabel(
    hdr, text="THERMODYNAMICS LAB",
    font=("SF Mono", 19, "bold"), text_color=CYAN
).pack(side="left", padx=26, pady=14)

ctk.CTkLabel(
    hdr, text="·   First Law of Thermodynamics   ·   Q = W   ·   mcΔT = ∫P dt",
    font=("SF Mono", 11), text_color=TEXT_DIM
).pack(side="left")

hdr_right = ctk.CTkFrame(hdr, fg_color="transparent")
hdr_right.pack(side="right", padx=26)

hdr_heater = ctk.CTkLabel(
    hdr_right, text="●  HEATER  OFF",
    font=("SF Mono", 12, "bold"), text_color=TEXT_DIM
)
hdr_heater.pack(side="right", padx=(20, 0))

hdr_conn = ctk.CTkLabel(
    hdr_right, text="●  DISCONNECTED",
    font=("SF Mono", 12, "bold"), text_color=RED
)
hdr_conn.pack(side="right")

# ── Body ──────────────────────────────────────────────────────────────────────
body = ctk.CTkFrame(app, fg_color="transparent")
body.pack(fill="both", expand=True, padx=14, pady=(10, 14))
body.columnconfigure(0, weight=0, minsize=282)
body.columnconfigure(1, weight=1)
body.rowconfigure(0, weight=1)

# ── LEFT panel ────────────────────────────────────────────────────────────────
left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

# ── Connection section ────────────────────────────────────────────────────────
ctk.CTkLabel(
    left, text="CONNECTION",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(16, 4))
ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))

conn_card = ctk.CTkFrame(left, fg_color=CARD2, corner_radius=10)
conn_card.pack(fill="x", padx=12, pady=(0, 6))

# Port row: dropdown + refresh
port_row = ctk.CTkFrame(conn_card, fg_color="transparent")
port_row.pack(fill="x", padx=10, pady=(10, 5))
port_row.columnconfigure(0, weight=1)

port_var  = ctk.StringVar(value=load_config().get("last_port", "Auto-detect"))
port_menu = ctk.CTkOptionMenu(
    port_row,
    variable=port_var,
    values=get_port_list(),
    font=("SF Mono", 11),
    fg_color=CARD, button_color=BORDER, button_hover_color=CYAN,
    text_color=TEXT_MID, dropdown_fg_color=CARD,
    dropdown_text_color=TEXT_MID, dropdown_hover_color=BORDER,
    corner_radius=6, dynamic_resizing=False,
    command=lambda _: None,
)
port_menu.grid(row=0, column=0, sticky="ew", padx=(0, 5))

ctk.CTkButton(
    port_row, text="⟳", width=34, height=28,
    fg_color=CARD, border_width=1, border_color=BORDER,
    text_color=TEXT_MID, hover_color=BORDER,
    font=("SF Mono", 14), corner_radius=6,
    command=lambda: refresh_ports()
).grid(row=0, column=1)

# Connect button (text/command toggled by connect/disconnect)
connect_btn = ctk.CTkButton(
    conn_card, text="▶  CONNECT", height=32,
    fg_color=CARD, border_width=1,
    border_color=GREEN, text_color=GREEN, hover_color="#0a2e1a",
    font=("SF Mono", 12, "bold"), corner_radius=6,
    command=lambda: connect()
)
connect_btn.pack(fill="x", padx=10, pady=(0, 6))

conn_status = ctk.CTkLabel(
    conn_card, text="●  Not connected",
    font=("SF Mono", 10), text_color=TEXT_DIM, anchor="w"
)
conn_status.pack(anchor="w", padx=12, pady=(0, 10))

# ── Sensor section ────────────────────────────────────────────────────────────
ctk.CTkLabel(
    left, text="LIVE  SENSORS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(8, 4))
ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 6))


def sensor_card(parent, name, unit, color):
    f = ctk.CTkFrame(parent, fg_color=CARD2, corner_radius=10)
    f.pack(fill="x", padx=12, pady=3)
    top = ctk.CTkFrame(f, fg_color="transparent")
    top.pack(fill="x", padx=13, pady=(7, 1))
    ctk.CTkLabel(top, text="●", font=("SF Mono", 8), text_color=color).pack(side="left")
    ctk.CTkLabel(top, text=f"  {name}", font=("SF Mono", 10), text_color=TEXT_DIM).pack(side="left")
    val = ctk.CTkLabel(f, text=f"--  {unit}", font=("SF Mono", 22, "bold"), text_color=color)
    val.pack(anchor="w", padx=13, pady=(1, 7))
    return val


temp_val   = sensor_card(left, "TEMPERATURE", "°C", CYAN)
volt_val   = sensor_card(left, "VOLTAGE",     "V",  PURPLE)
curr_val   = sensor_card(left, "CURRENT",     "A",  PURPLE)
power_val  = sensor_card(left, "POWER",       "W",  AMBER)
energy_val = sensor_card(left, "ENERGY",      "J",  GREEN)

# Heater card
hc = ctk.CTkFrame(left, fg_color=CARD2, corner_radius=10)
hc.pack(fill="x", padx=12, pady=3)
hc_top = ctk.CTkFrame(hc, fg_color="transparent")
hc_top.pack(fill="x", padx=13, pady=(7, 1))
ctk.CTkLabel(hc_top, text="●", font=("SF Mono", 8), text_color=AMBER).pack(side="left")
ctk.CTkLabel(hc_top, text="  HEATER", font=("SF Mono", 10), text_color=TEXT_DIM).pack(side="left")
heater_val = ctk.CTkLabel(hc, text="OFF", font=("SF Mono", 22, "bold"), text_color=TEXT_DIM)
heater_val.pack(anchor="w", padx=13, pady=(1, 7))

# ── Parameters section ────────────────────────────────────────────────────────
ctk.CTkLabel(
    left, text="PARAMETERS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(10, 4))
ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))

params_card = ctk.CTkFrame(left, fg_color=CARD2, corner_radius=10)
params_card.pack(fill="x", padx=12, pady=(0, 12))

def _prow(parent, title):
    """Labelled parameter row — returns the inner frame for child widgets."""
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=13, pady=(8, 0))
    ctk.CTkLabel(f, text=title, font=("SF Mono", 9), text_color=TEXT_DIM).pack(anchor="w")
    return f

# Liquid preset
liq_row = _prow(params_card, "LIQUID PRESET")
liquid_var  = ctk.StringVar(value="Water")
liquid_menu = ctk.CTkOptionMenu(
    liq_row, variable=liquid_var,
    values=list(LIQUID_PRESETS.keys()),
    font=("SF Mono", 11),
    fg_color=CARD, button_color=BORDER, button_hover_color=CYAN,
    text_color=TEXT_MID, dropdown_fg_color=CARD,
    dropdown_text_color=TEXT_MID, dropdown_hover_color=BORDER,
    corner_radius=6, dynamic_resizing=False,
    command=lambda choice: on_preset_change(choice),
)
liquid_menu.pack(fill="x", pady=(3, 0))

# Water mass
mass_row = _prow(params_card, "WATER MASS")
mass_unit_row = ctk.CTkFrame(mass_row, fg_color="transparent")
mass_unit_row.pack(fill="x", pady=(3, 0))
mass_unit_row.columnconfigure(0, weight=1)
mass_entry = ctk.CTkEntry(
    mass_unit_row, font=("SF Mono", 13),
    fg_color=CARD, border_color=BORDER, text_color=TEXT_MID,
    corner_radius=6, justify="right",
)
mass_entry.insert(0, str(WATER_MASS))
mass_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
ctk.CTkLabel(
    mass_unit_row, text="kg",
    font=("SF Mono", 11), text_color=TEXT_DIM
).grid(row=0, column=1)

# Specific heat capacity
heat_row = _prow(params_card, "SPECIFIC HEAT")
heat_unit_row = ctk.CTkFrame(heat_row, fg_color="transparent")
heat_unit_row.pack(fill="x", pady=(3, 0))
heat_unit_row.columnconfigure(0, weight=1)
heat_entry = ctk.CTkEntry(
    heat_unit_row, font=("SF Mono", 13),
    fg_color=CARD, border_color=BORDER, text_color=TEXT_MID,
    corner_radius=6, justify="right",
)
heat_entry.insert(0, str(SPECIFIC_HEAT))
heat_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
ctk.CTkLabel(
    heat_unit_row, text="J/kg·K",
    font=("SF Mono", 11), text_color=TEXT_DIM
).grid(row=0, column=1)

# Apply button + live status
apply_btn = ctk.CTkButton(
    params_card, text="APPLY", height=30,
    fg_color=CARD, border_width=1,
    border_color=CYAN, text_color=CYAN, hover_color="#082030",
    font=("SF Mono", 11, "bold"), corner_radius=6,
    command=lambda: apply_params()
)
apply_btn.pack(fill="x", padx=13, pady=(10, 4))

params_status = ctk.CTkLabel(
    params_card,
    text=f"  m = {WATER_MASS} kg   c = {SPECIFIC_HEAT} J/kg·K",
    font=("SF Mono", 9), text_color=TEXT_DIM, anchor="w",
)
params_status.pack(anchor="w", padx=13, pady=(0, 10))

# ── RIGHT panel ───────────────────────────────────────────────────────────────
right = ctk.CTkFrame(body, fg_color="transparent")
right.grid(row=0, column=1, sticky="nsew")
right.rowconfigure(0, weight=3)
right.rowconfigure(1, weight=2)
right.rowconfigure(2, weight=0)
right.columnconfigure(0, weight=1)

# ── Graph ─────────────────────────────────────────────────────────────────────
gf = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12)
gf.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

ctk.CTkLabel(
    gf, text="TEMPERATURE  vs  TIME",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(13, 4))
ctk.CTkFrame(gf, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 6))

fig = Figure(figsize=(10, 4), dpi=96)
fig.patch.set_facecolor(CARD)
ax = fig.add_subplot(111)
ax.set_facecolor(BG)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["bottom"].set_color(BORDER)
ax.spines["left"].set_color(BORDER)
ax.tick_params(colors=TEXT_DIM, labelsize=9)
ax.set_xlabel("Time (s)", color=TEXT_DIM, fontsize=9, labelpad=6)
ax.set_ylabel("Temperature (°C)", color=TEXT_DIM, fontsize=9, labelpad=6)
ax.grid(True, color=BORDER, linestyle="--", linewidth=0.4, alpha=0.7)
fig.tight_layout(pad=2.5)

line_plot, = ax.plot([], [], color=CYAN, linewidth=2, solid_capstyle="round")
fill_ref   = [None]

mpl_canvas = FigureCanvasTkAgg(fig, master=gf)
mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

# ── Results ───────────────────────────────────────────────────────────────────
rf = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12)
rf.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

ctk.CTkLabel(
    rf, text="EXPERIMENT  RESULTS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(13, 4))
ctk.CTkFrame(rf, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))

rg = ctk.CTkFrame(rf, fg_color="transparent")
rg.pack(fill="x", padx=12, pady=(0, 6))
for c in range(3):
    rg.columnconfigure(c, weight=1)


def result_card(parent, row, col, label, init, color):
    f = ctk.CTkFrame(parent, fg_color=CARD2, corner_radius=8)
    f.grid(row=row, column=col, padx=4, pady=3, sticky="ew")
    ctk.CTkLabel(f, text=label, font=("SF Mono", 9), text_color=TEXT_DIM).pack(anchor="w", padx=10, pady=(7, 2))
    lbl = ctk.CTkLabel(f, text=init, font=("SF Mono", 16, "bold"), text_color=color)
    lbl.pack(anchor="w", padx=10, pady=(0, 7))
    return lbl


r_init  = result_card(rg, 0, 0, "T₀  initial",        "--.- °C", CYAN)
r_final = result_card(rg, 0, 1, "T₁  final",          "--.- °C", CYAN)
r_dt    = result_card(rg, 0, 2, "ΔT  rise",           "--.- °C", AMBER)
r_q     = result_card(rg, 1, 0, "Q = mcΔT  (heat)",   "-- J",    GREEN)
r_w     = result_card(rg, 1, 1, "W = ΔE  (work in)",  "-- J",    AMBER)
r_eff   = result_card(rg, 1, 2, "η  efficiency",      "-- %",    PURPLE)

# Analysis
ctk.CTkFrame(rf, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(2, 8))
ctk.CTkLabel(
    rf, text="1ST LAW ANALYSIS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(0, 5))

analysis_frame = ctk.CTkFrame(rf, fg_color=CARD2, corner_radius=8)
analysis_frame.pack(fill="x", padx=12, pady=(0, 12))

PLACEHOLDER = "  Run an experiment — press  ▶ START  then  ■ STOP  to see the 1st Law verification."

analysis_lbl = ctk.CTkLabel(
    analysis_frame, text=PLACEHOLDER,
    font=("SF Mono", 11), text_color=TEXT_DIM,
    justify="left", anchor="w",
)
analysis_lbl.pack(fill="x", padx=16, pady=12)

verdict_lbl = ctk.CTkLabel(
    analysis_frame, text="",
    font=("SF Mono", 11, "bold"),
    justify="left", anchor="w", text_color=TEXT_DIM,
)
verdict_lbl.pack(fill="x", padx=16, pady=(0, 12))

# ── Controls ──────────────────────────────────────────────────────────────────
cf = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12)
cf.grid(row=2, column=0, sticky="ew")

btn_row = ctk.CTkFrame(cf, fg_color="transparent")
btn_row.pack(fill="x", padx=16, pady=13)

exp_status = ctk.CTkLabel(
    btn_row, text="●  IDLE",
    font=("SF Mono", 12), text_color=TEXT_DIM
)
exp_status.pack(side="right", padx=6)


# ── Event handlers ────────────────────────────────────────────────────────────

def refresh_ports():
    ports = get_port_list()
    port_menu.configure(values=ports)
    if port_var.get() not in ports:
        port_var.set("Auto-detect")


def on_preset_change(choice):
    """Auto-fill specific heat when a liquid preset is selected."""
    heat = LIQUID_PRESETS.get(choice)
    if heat is not None:
        heat_entry.delete(0, "end")
        heat_entry.insert(0, str(heat))


def apply_params():
    global WATER_MASS, SPECIFIC_HEAT
    try:
        new_mass = float(mass_entry.get().strip())
        new_heat = float(heat_entry.get().strip())
        if new_mass <= 0 or new_heat <= 0:
            raise ValueError
    except (ValueError, TypeError):
        params_status.configure(text="  ⚠  Enter valid positive numbers", text_color=RED)
        def _reset_err():
            params_status.configure(
                text=f"  m = {WATER_MASS} kg   c = {SPECIFIC_HEAT} J/kg·K",
                text_color=TEXT_DIM,
            )
        app.after(2500, _reset_err)
        return

    WATER_MASS    = round(new_mass, 4)
    SPECIFIC_HEAT = round(new_heat, 1)
    save_config({"water_mass": WATER_MASS, "specific_heat": SPECIFIC_HEAT})
    params_status.configure(
        text=f"  ✓  m = {WATER_MASS} kg   c = {SPECIFIC_HEAT} J/kg·K",
        text_color=GREEN,
    )
    apply_btn.configure(border_color=GREEN, text_color=GREEN)

    def _reset():
        params_status.configure(
            text=f"  m = {WATER_MASS} kg   c = {SPECIFIC_HEAT} J/kg·K",
            text_color=TEXT_DIM,
        )
        apply_btn.configure(border_color=CYAN, text_color=CYAN)
    app.after(2500, _reset)


def connect():
    global ser, connected
    selected = port_var.get()
    port     = _auto_detect() if selected == "Auto-detect" else selected

    if not port:
        conn_status.configure(text="●  No device found", text_color=RED)
        hdr_conn.configure(text="●  NO DEVICE", text_color=RED)
        return

    try:
        with serial_lock:
            if ser and ser.is_open:
                ser.close()
            ser = serial.Serial(port, BAUD, timeout=1)
        connected = True
        save_config({"last_port": selected})
        conn_status.configure(text=f"●  {port}", text_color=GREEN)
        connect_btn.configure(
            text="■  DISCONNECT",
            border_color=RED, text_color=RED, hover_color="#2e0a0a",
            command=lambda: disconnect()
        )
        hdr_conn.configure(text="●  CONNECTED", text_color=GREEN)
    except serial.SerialException as e:
        msg = "●  Port busy — try another" if "busy" in str(e).lower() else "●  Connection failed"
        conn_status.configure(text=msg, text_color=RED)
        hdr_conn.configure(text="●  DISCONNECTED", text_color=RED)


def disconnect():
    global ser, connected
    connected = False
    with serial_lock:
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
        ser = None
    conn_status.configure(text="●  Disconnected", text_color=TEXT_DIM)
    connect_btn.configure(
        text="▶  CONNECT",
        border_color=GREEN, text_color=GREEN, hover_color="#0a2e1a",
        command=lambda: connect()
    )
    hdr_conn.configure(text="●  DISCONNECTED", text_color=RED)


def start_experiment():
    global experiment_running, initial_temp, initial_energy, experiment_start_t
    experiment_running = True
    initial_temp       = temperature
    initial_energy     = energy
    experiment_start_t = time.time()
    r_init.configure(text=f"{initial_temp:.1f} °C")
    start_btn.configure(fg_color="#0a2e1a", border_color=GREEN, text_color=GREEN)
    analysis_lbl.configure(text="  Recording…  temperature is rising.", text_color=TEXT_DIM)
    verdict_lbl.configure(text="")


def stop_experiment():
    global experiment_running, final_temp, final_energy, efficiency, heat_gained
    experiment_running = False
    final_temp   = temperature
    final_energy = energy
    delta_t      = final_temp - initial_temp
    heat_gained  = WATER_MASS * SPECIFIC_HEAT * delta_t
    energy_used  = final_energy - initial_energy
    heat_loss    = max(0.0, energy_used - heat_gained)
    efficiency   = (heat_gained / energy_used * 100) if energy_used > 0 else 0.0

    r_final.configure(text=f"{final_temp:.1f} °C")
    r_dt.configure(text=f"{delta_t:.1f} °C")
    r_q.configure(text=f"{heat_gained:.0f} J")
    r_w.configure(text=f"{energy_used:.0f} J")
    r_eff.configure(text=f"{efficiency:.1f} %")

    eff_color = GREEN if efficiency >= 75 else (AMBER if efficiency >= 50 else RED)
    r_eff.configure(text_color=eff_color)

    exp_status.configure(text="●  STOPPED", text_color=RED)
    start_btn.configure(fg_color=CARD2, border_color=BORDER, text_color=TEXT_MID)

    analysis_lbl.configure(text_color=TEXT_MID, text=(
        f"  W  =  ΔE_electrical  =  {energy_used:>8.1f} J    →  electrical energy supplied to the heater\n"
        f"  Q  =  m·c·ΔT         =  {heat_gained:>8.1f} J    →  heat absorbed by water  (m={WATER_MASS} kg, c={SPECIFIC_HEAT} J/kg·K)\n"
        f"  Loss = W − Q         =  {heat_loss:>8.1f} J    →  dissipated to environment  (conduction / radiation)\n"
        f"  η   = Q / W × 100   =  {efficiency:>8.1f} %    →  thermal conversion efficiency"
    ))

    if efficiency >= 75:
        vc, vt = GREEN, "  ✓  W = Q + Q_loss  →  Energy is conserved  →  1st Law of Thermodynamics verified"
    elif efficiency >= 50:
        vc, vt = AMBER, "  ~  W = Q + Q_loss  →  Energy is conserved  →  1st Law holds  (notable loss to environment)"
    else:
        vc, vt = RED,   "  ⚠  W = Q + Q_loss  →  Energy is conserved  →  1st Law holds  (high environmental heat loss)"
    verdict_lbl.configure(text=vt, text_color=vc)


def reset_experiment():
    global efficiency, heat_gained
    efficiency  = 0
    heat_gained = 0
    for lbl, txt in [(r_init, "--.- °C"), (r_final, "--.- °C"), (r_dt, "--.- °C"),
                     (r_q, "-- J"), (r_w, "-- J")]:
        lbl.configure(text=txt)
    r_eff.configure(text="-- %", text_color=PURPLE)
    analysis_lbl.configure(text=PLACEHOLDER, text_color=TEXT_DIM)
    verdict_lbl.configure(text="")
    exp_status.configure(text="●  IDLE", text_color=TEXT_DIM)
    start_btn.configure(fg_color=CARD2, border_color=GREEN, text_color=GREEN)


def export_csv():
    if not temp_history:
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile="thermodynamics_data.csv",
        title="Export Temperature Data"
    )
    if not filename:
        return
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)", "Temperature (°C)"])
        for t, temp in zip(time_history, temp_history):
            writer.writerow([f"{t:.2f}", f"{temp:.2f}"])


# ── Buttons ───────────────────────────────────────────────────────────────────
start_btn = ctk.CTkButton(
    btn_row, text="▶  START", width=120, height=36,
    fg_color=CARD2, border_width=1, border_color=GREEN,
    text_color=GREEN, hover_color="#0a2e1a",
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=lambda: start_experiment()
)
start_btn.pack(side="left", padx=(0, 8))

ctk.CTkButton(
    btn_row, text="■  STOP", width=120, height=36,
    fg_color=CARD2, border_width=1, border_color=RED,
    text_color=RED, hover_color="#2e0a0a",
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=lambda: stop_experiment()
).pack(side="left", padx=(0, 8))

ctk.CTkButton(
    btn_row, text="↺  RESET", width=120, height=36,
    fg_color=CARD2, border_width=1, border_color=BORDER,
    text_color=TEXT_MID, hover_color=CARD2,
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=lambda: reset_experiment()
).pack(side="left", padx=(0, 16))

ctk.CTkButton(
    btn_row, text="⬇  EXPORT CSV", width=148, height=36,
    fg_color=CARD2, border_width=1, border_color=PURPLE,
    text_color=PURPLE, hover_color="#1a1030",
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=lambda: export_csv()
).pack(side="left")

# ── Serial reader thread ──────────────────────────────────────────────────────
def read_serial():
    global temperature, voltage, current, power, energy, heater_status
    global connected, last_data_time, ser
    while True:
        with serial_lock:
            s = ser
        if s is None or not s.is_open:
            time.sleep(0.3)
            continue
        try:
            raw   = s.readline().decode("utf-8", errors="ignore").strip()
            parts = raw.split(",")
            if len(parts) != 6:
                continue
            temperature   = float(parts[0])
            voltage       = float(parts[1])
            current       = float(parts[2])
            power         = float(parts[3])
            energy        = float(parts[4])
            heater_status = int(parts[5])
            temp_history.append(temperature)
            time_history.append(time.time() - start_time)
            last_data_time = time.time()
        except serial.SerialException:
            # Port was physically unplugged or lost
            connected = False
            with serial_lock:
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                ser = None
        except Exception:
            pass


threading.Thread(target=read_serial, daemon=True).start()

# ── UI update loop ────────────────────────────────────────────────────────────
_prev_connected = None


def update_ui():
    global _prev_connected

    # React to unexpected disconnects (port unplugged mid-session)
    if connected != _prev_connected:
        if not connected:
            conn_status.configure(text="●  Connection lost", text_color=RED)
            connect_btn.configure(
                text="▶  CONNECT",
                border_color=GREEN, text_color=GREEN, hover_color="#0a2e1a",
                command=lambda: connect()
            )
        _prev_connected = connected

    # Header: connection + staleness
    if connected:
        stale = last_data_time > 0 and (time.time() - last_data_time > 5)
        hdr_conn.configure(
            text="●  NO DATA" if stale else "●  CONNECTED",
            text_color=AMBER   if stale else GREEN
        )
    else:
        hdr_conn.configure(text="●  DISCONNECTED", text_color=RED)

    # Sensor values
    temp_val.configure(text=f"{temperature:.1f}  °C")
    volt_val.configure(text=f"{voltage:.2f}  V")
    curr_val.configure(text=f"{current:.3f}  A")
    power_val.configure(text=f"{power:.2f}  W")
    energy_val.configure(text=f"{energy:.1f}  J")

    if heater_status:
        heater_val.configure(text="ON",  text_color=AMBER)
        hdr_heater.configure(text="●  HEATER  ON",  text_color=AMBER)
    else:
        heater_val.configure(text="OFF", text_color=TEXT_DIM)
        hdr_heater.configure(text="●  HEATER  OFF", text_color=TEXT_DIM)

    # Experiment timer
    if experiment_running:
        elapsed = time.time() - experiment_start_t
        m, s   = divmod(int(elapsed), 60)
        exp_status.configure(text=f"●  RECORDING  {m:02d}:{s:02d}", text_color=GREEN)

    # Graph
    t_list = list(time_history)
    t_temp = list(temp_history)
    if len(t_list) > 1:
        line_plot.set_data(t_list, t_temp)
        if fill_ref[0] is not None:
            fill_ref[0].remove()
        fill_ref[0] = ax.fill_between(t_list, t_temp, alpha=0.06, color=CYAN)
        ax.relim()
        ax.autoscale_view()
    mpl_canvas.draw_idle()

    app.after(1000, update_ui)


# ── Startup: restore saved parameters then auto-connect ──────────────────────
def startup_connect():
    global WATER_MASS, SPECIFIC_HEAT
    cfg = load_config()

    # Restore physics parameters (fall back to defaults if never saved)
    WATER_MASS    = cfg.get("water_mass",    0.3)
    SPECIFIC_HEAT = cfg.get("specific_heat", 4186)
    mass_entry.delete(0, "end")
    mass_entry.insert(0, str(WATER_MASS))
    heat_entry.delete(0, "end")
    heat_entry.insert(0, str(SPECIFIC_HEAT))
    params_status.configure(
        text=f"  m = {WATER_MASS} kg   c = {SPECIFIC_HEAT} J/kg·K"
    )

    port_var.set(cfg.get("last_port", "Auto-detect"))
    connect()


app.after(400, startup_connect)
update_ui()
app.mainloop()
