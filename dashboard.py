import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── Serial — auto-detect Arduino (works on macOS /dev/tty.* and Windows COM*) ─
BAUD = 9600

def _find_port():
    keywords = ("arduino", "ch340", "cp210", "ftdi", "usb serial", "usbserial")
    for p in serial.tools.list_ports.comports():
        if any(k in (p.description or "").lower() for k in keywords):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None

_port = _find_port()
try:
    ser = serial.Serial(_port, BAUD, timeout=1) if _port else None
except Exception:
    ser = None

# ── Physics constants ───────────────────────────────────────────────────────
WATER_MASS    = 0.3     # kg
SPECIFIC_HEAT = 4186    # J / (kg·K)

# ── Shared state ────────────────────────────────────────────────────────────
temperature    = 0.0
voltage        = 0.0
current        = 0.0
power          = 0.0
energy         = 0.0
heater_status  = 0

experiment_running = False
initial_temp       = 0.0
final_temp         = 0.0
initial_energy     = 0.0
final_energy       = 0.0
efficiency         = 0.0
heat_gained        = 0.0

temp_history = deque(maxlen=300)
time_history = deque(maxlen=300)
start_time   = time.time()

# ── Palette ─────────────────────────────────────────────────────────────────
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

# ── App ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.title("Thermodynamics Lab · 1st Law Verification")
app.geometry("1420x900")
app.configure(fg_color=BG)

# ── Header ───────────────────────────────────────────────────────────────────
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

hdr_heater = ctk.CTkLabel(
    hdr, text="●  HEATER  OFF",
    font=("SF Mono", 12, "bold"), text_color=TEXT_DIM
)
hdr_heater.pack(side="right", padx=26)

# ── Body ─────────────────────────────────────────────────────────────────────
body = ctk.CTkFrame(app, fg_color="transparent")
body.pack(fill="both", expand=True, padx=14, pady=(10, 14))
body.columnconfigure(0, weight=0, minsize=262)
body.columnconfigure(1, weight=1)
body.rowconfigure(0, weight=1)

# ── LEFT — Sensor Panel ──────────────────────────────────────────────────────
left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

ctk.CTkLabel(
    left, text="LIVE  SENSORS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(16, 4))
ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 6))


def sensor_card(parent, name, unit, color):
    f = ctk.CTkFrame(parent, fg_color=CARD2, corner_radius=10)
    f.pack(fill="x", padx=12, pady=4)
    top = ctk.CTkFrame(f, fg_color="transparent")
    top.pack(fill="x", padx=13, pady=(9, 1))
    ctk.CTkLabel(top, text="●", font=("SF Mono", 8), text_color=color).pack(side="left")
    ctk.CTkLabel(top, text=f"  {name}", font=("SF Mono", 10), text_color=TEXT_DIM).pack(side="left")
    val = ctk.CTkLabel(f, text=f"--  {unit}", font=("SF Mono", 24, "bold"), text_color=color)
    val.pack(anchor="w", padx=13, pady=(1, 9))
    return val


temp_val   = sensor_card(left, "TEMPERATURE", "°C", CYAN)
volt_val   = sensor_card(left, "VOLTAGE",     "V",  PURPLE)
curr_val   = sensor_card(left, "CURRENT",     "A",  PURPLE)
power_val  = sensor_card(left, "POWER",       "W",  AMBER)
energy_val = sensor_card(left, "ENERGY",      "J",  GREEN)

# Heater card
hc = ctk.CTkFrame(left, fg_color=CARD2, corner_radius=10)
hc.pack(fill="x", padx=12, pady=4)
hc_top = ctk.CTkFrame(hc, fg_color="transparent")
hc_top.pack(fill="x", padx=13, pady=(9, 1))
ctk.CTkLabel(hc_top, text="●", font=("SF Mono", 8), text_color=AMBER).pack(side="left")
ctk.CTkLabel(hc_top, text="  HEATER", font=("SF Mono", 10), text_color=TEXT_DIM).pack(side="left")
heater_val = ctk.CTkLabel(hc, text="OFF", font=("SF Mono", 24, "bold"), text_color=TEXT_DIM)
heater_val.pack(anchor="w", padx=13, pady=(1, 9))

# ── RIGHT ────────────────────────────────────────────────────────────────────
right = ctk.CTkFrame(body, fg_color="transparent")
right.grid(row=0, column=1, sticky="nsew")
right.rowconfigure(0, weight=3)   # graph
right.rowconfigure(1, weight=2)   # results + analysis
right.rowconfigure(2, weight=0)   # controls
right.columnconfigure(0, weight=1)

# ── Graph ────────────────────────────────────────────────────────────────────
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

# ── Results ──────────────────────────────────────────────────────────────────
rf = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12)
rf.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

ctk.CTkLabel(
    rf, text="EXPERIMENT  RESULTS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(13, 4))
ctk.CTkFrame(rf, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))

# 2 rows × 3 columns of result cards
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


# Row 0: temperatures
r_init  = result_card(rg, 0, 0, "T₀  initial",      "--.- °C", CYAN)
r_final = result_card(rg, 0, 1, "T₁  final",        "--.- °C", CYAN)
r_dt    = result_card(rg, 0, 2, "ΔT  rise",         "--.- °C", AMBER)

# Row 1: energy balance
r_q     = result_card(rg, 1, 0, "Q = mcΔT  (heat)", "-- J",    GREEN)
r_w     = result_card(rg, 1, 1, "W = ΔE  (work in)", "-- J",   AMBER)
r_eff   = result_card(rg, 1, 2, "η  efficiency",    "-- %",    PURPLE)

# ── 1st Law Analysis ─────────────────────────────────────────────────────────
ctk.CTkFrame(rf, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(2, 8))

ctk.CTkLabel(
    rf, text="1ST LAW ANALYSIS",
    font=("SF Mono", 10, "bold"), text_color=TEXT_DIM
).pack(anchor="w", padx=18, pady=(0, 5))

analysis_frame = ctk.CTkFrame(rf, fg_color=CARD2, corner_radius=8)
analysis_frame.pack(fill="x", padx=12, pady=(0, 12))

PLACEHOLDER = "  Run an experiment — press  ▶ START  then  ■ STOP  to see the 1st Law verification."

analysis_lbl = ctk.CTkLabel(
    analysis_frame,
    text=PLACEHOLDER,
    font=("SF Mono", 11),
    text_color=TEXT_DIM,
    justify="left",
    anchor="w",
)
analysis_lbl.pack(fill="x", padx=16, pady=12)

verdict_lbl = ctk.CTkLabel(
    analysis_frame,
    text="",
    font=("SF Mono", 11, "bold"),
    justify="left",
    anchor="w",
    text_color=TEXT_DIM,
)
verdict_lbl.pack(fill="x", padx=16, pady=(0, 12))

# ── Controls ─────────────────────────────────────────────────────────────────
cf = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12)
cf.grid(row=2, column=0, sticky="ew")

btn_row = ctk.CTkFrame(cf, fg_color="transparent")
btn_row.pack(fill="x", padx=16, pady=13)

exp_status = ctk.CTkLabel(
    btn_row, text="●  IDLE",
    font=("SF Mono", 12), text_color=TEXT_DIM
)
exp_status.pack(side="right", padx=6)


# ── Experiment logic ──────────────────────────────────────────────────────────
def start_experiment():
    global experiment_running, initial_temp, initial_energy
    experiment_running = True
    initial_temp       = temperature
    initial_energy     = energy
    r_init.configure(text=f"{initial_temp:.1f} °C")
    exp_status.configure(text="●  RECORDING", text_color=GREEN)
    start_btn.configure(fg_color="#0a2e1a", border_color=GREEN, text_color=GREEN)
    # Clear stale results
    analysis_lbl.configure(text="  Recording…  temperature is rising.", text_color=TEXT_DIM)
    verdict_lbl.configure(text="")


def stop_experiment():
    global experiment_running, final_temp, final_energy, efficiency, heat_gained
    experiment_running = False
    final_temp    = temperature
    final_energy  = energy
    delta_t       = final_temp - initial_temp
    heat_gained   = WATER_MASS * SPECIFIC_HEAT * delta_t
    energy_used   = final_energy - initial_energy
    heat_loss     = energy_used - heat_gained if energy_used > heat_gained else 0.0

    if energy_used > 0:
        efficiency = (heat_gained / energy_used) * 100
    else:
        efficiency = 0.0

    # Result cards
    r_final.configure(text=f"{final_temp:.1f} °C")
    r_dt.configure(text=f"{delta_t:.1f} °C")
    r_q.configure(text=f"{heat_gained:.0f} J")
    r_w.configure(text=f"{energy_used:.0f} J")
    r_eff.configure(text=f"{efficiency:.1f} %")

    # Efficiency colour
    if efficiency >= 75:
        eff_color = GREEN
    elif efficiency >= 50:
        eff_color = AMBER
    else:
        eff_color = RED
    r_eff.configure(text_color=eff_color)

    exp_status.configure(text="●  STOPPED", text_color=RED)
    start_btn.configure(fg_color=CARD2, border_color=BORDER, text_color=TEXT_MID)

    # 1st Law analysis statements
    analysis_text = (
        f"  W  =  ΔE_electrical  =  {energy_used:>8.1f} J    →  electrical energy supplied to the heater\n"
        f"  Q  =  m·c·ΔT         =  {heat_gained:>8.1f} J    →  heat absorbed by water  (m={WATER_MASS} kg, c={SPECIFIC_HEAT} J/kg·K)\n"
        f"  Loss = W − Q         =  {heat_loss:>8.1f} J    →  dissipated to environment  (conduction / radiation)\n"
        f"  η   = Q / W × 100   =  {efficiency:>8.1f} %    →  thermal conversion efficiency"
    )
    analysis_lbl.configure(text=analysis_text, text_color=TEXT_MID)

    if efficiency >= 75:
        verdict_color = GREEN
        verdict_text  = "  ✓  W = Q + Q_loss  →  Energy is conserved  →  1st Law of Thermodynamics verified"
    elif efficiency >= 50:
        verdict_color = AMBER
        verdict_text  = "  ~  W = Q + Q_loss  →  Energy is conserved  →  1st Law holds  (notable loss to environment)"
    else:
        verdict_color = RED
        verdict_text  = "  ⚠  W = Q + Q_loss  →  Energy is conserved  →  1st Law holds  (high environmental heat loss)"

    verdict_lbl.configure(text=verdict_text, text_color=verdict_color)


def reset_experiment():
    global efficiency, heat_gained
    efficiency  = 0
    heat_gained = 0
    r_init.configure(text="--.- °C")
    r_final.configure(text="--.- °C")
    r_dt.configure(text="--.- °C")
    r_q.configure(text="-- J")
    r_w.configure(text="-- J")
    r_eff.configure(text="-- %", text_color=PURPLE)
    analysis_lbl.configure(text=PLACEHOLDER, text_color=TEXT_DIM)
    verdict_lbl.configure(text="")
    exp_status.configure(text="●  IDLE", text_color=TEXT_DIM)
    start_btn.configure(fg_color=CARD2, border_color=GREEN, text_color=GREEN)


start_btn = ctk.CTkButton(
    btn_row, text="▶  START", width=140, height=36,
    fg_color=CARD2, border_width=1, border_color=GREEN,
    text_color=GREEN, hover_color="#0a2e1a",
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=start_experiment
)
start_btn.pack(side="left", padx=(0, 8))

ctk.CTkButton(
    btn_row, text="■  STOP", width=140, height=36,
    fg_color=CARD2, border_width=1, border_color=RED,
    text_color=RED, hover_color="#2e0a0a",
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=stop_experiment
).pack(side="left", padx=(0, 8))

ctk.CTkButton(
    btn_row, text="↺  RESET", width=140, height=36,
    fg_color=CARD2, border_width=1, border_color=BORDER,
    text_color=TEXT_MID, hover_color=CARD2,
    font=("SF Mono", 12, "bold"), corner_radius=8,
    command=reset_experiment
).pack(side="left")

# ── Serial reader ────────────────────────────────────────────────────────────
def read_serial():
    global temperature, voltage, current, power, energy, heater_status
    while True:
        if ser is None:
            time.sleep(0.5)
            continue
        try:
            raw   = ser.readline().decode().strip()
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
        except Exception:
            pass


threading.Thread(target=read_serial, daemon=True).start()

# ── UI update loop ────────────────────────────────────────────────────────────
def update_ui():
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


update_ui()
app.mainloop()
