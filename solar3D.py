#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solar3D.py — Viaje 3D ilustrativo de una nave inspirada en Soyuz por el Sistema Solar.

Solo usa la biblioteca estándar de Python (tkinter, math, random, time, functools).
No es un simulador orbital de precisión: usa vectores 3D, curvas de Bézier y una
cámara con perspectiva para dibujar una ruta visual.

Ejecución:
    python3 solar3D.py
En Fedora, si falta tkinter:
    sudo dnf install python3-tkinter

Controles:
    Arrastrar (ratón) ... rotar la cámara          Rueda ........ zoom
    Clic en un astro .... enfocarlo y ver su info  Clic en el itinerario ... saltar a esa etapa
    ESPACIO pausa · R reiniciar · ← / → saltar · F seguir nave · V vista general
    L etiquetas · O órbitas · +/− zoom · F11 pantalla completa
"""

import math
import random
import sys
import time
from functools import lru_cache

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:  # Fedora no trae tkinter por defecto
    sys.stderr.write("No se encontró tkinter.\n"
                     "  Fedora:        sudo dnf install python3-tkinter\n"
                     "  Debian/Ubuntu: sudo apt install python3-tk\n")
    sys.exit(1)


# -----------------------------------------------------------------------------
# UTILIDADES: vectores 3D como tuplas (x, y, z), color y easing
# -----------------------------------------------------------------------------

def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_length(a):
    return math.sqrt(v_dot(a, a))


def v_normalize(a):
    length = v_length(a)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return v_mul(a, 1.0 / length)


def v_lerp(a, b, t):
    return v_add(a, v_mul(v_sub(b, a), t))


def clamp(value, lo, hi):
    return lo if value < lo else hi if value > hi else value


def smoothstep(u):
    return u * u * (3.0 - 2.0 * u)


@lru_cache(maxsize=4096)
def mix(color_a, color_b, t):
    """Mezcla dos colores '#rrggbb'. t=0 → a, t=1 → b."""
    t = clamp(t, 0.0, 1.0)
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def bezier_3d(p0, p1, p2, p3, steps=140):
    """Muestrea una curva cúbica de Bézier en el espacio 3D."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        p = v_add(
            v_add(v_mul(p0, u ** 3), v_mul(p1, 3 * u * u * t)),
            v_add(v_mul(p2, 3 * u * t * t), v_mul(p3, t ** 3)),
        )
        points.append(p)
    return points


def make_transfer(start, end, side=1, lift=5.0, steps=150):
    """Arco de viaje 3D entre dos puntos."""
    direction = v_sub(end, start)
    distance = max(v_length(direction), 0.001)
    direction_xy = v_normalize((direction[0], direction[1], 0.0))
    perpendicular = (-direction_xy[1], direction_xy[0], 0.0)
    bend = min(distance * 0.20, 10.0) * side

    c1 = v_add(start, v_mul(direction, 0.30))
    c1 = v_add(c1, v_add(v_mul(perpendicular, bend), (0.0, 0.0, lift)))
    c2 = v_add(start, v_mul(direction, 0.72))
    c2 = v_add(c2, v_add(v_mul(perpendicular, -bend * 0.55), (0.0, 0.0, lift * 0.65)))
    return bezier_3d(start, c1, c2, end, steps)


def make_orbit(center, radius, phase=0.0, inclination=0.35, steps=180):
    """Una vuelta circular alrededor de un cuerpo, inclinada en 3D."""
    points = []
    for i in range(steps + 1):
        angle = phase + 2.0 * math.pi * i / steps
        x = radius * math.cos(angle)
        y = radius * math.sin(angle) * math.cos(inclination)
        z = radius * math.sin(angle) * math.sin(inclination)
        points.append(v_add(center, (x, y, z)))
    return points


# -----------------------------------------------------------------------------
# SISTEMA SOLAR ESTILIZADO (unidades visuales «u.v.», no están a escala real)
# -----------------------------------------------------------------------------

SUN = (0.0, 0.0, 0.0)
SUN_RADIUS = 2.4  # radio visual del Sol en u.v. (más pequeño que la órbita de Mercurio)

PLANETS = [
    {"name": "Mercurio", "orbit": 5.5, "angle": 145, "radius": 0.55, "color": "#a9a39b",
     "info": "Planeta rocoso, casi sin atmósfera", "au": 0.39, "year": "88 días"},
    {"name": "Venus", "orbit": 8.2, "angle": 220, "radius": 0.82, "color": "#e7bd83",
     "info": "Efecto invernadero extremo", "au": 0.72, "year": "225 días"},
    {"name": "Tierra", "orbit": 11.5, "angle": 0, "radius": 0.95, "color": "#4b9cdb",
     "info": "Punto de partida", "au": 1.00, "year": "365,25 días"},
    {"name": "Marte", "orbit": 16.8, "angle": 43, "radius": 0.72, "color": "#d66b4c",
     "info": "Primer destino planetario", "au": 1.52, "year": "687 días"},
    {"name": "Júpiter", "orbit": 25.5, "angle": 158, "radius": 2.65, "color": "#d7aa7b",
     "info": "Gigante gaseoso", "au": 5.20, "year": "11,9 años"},
    {"name": "Saturno", "orbit": 34.5, "angle": 285, "radius": 2.25, "color": "#e6cf9a",
     "info": "Gigante con anillos", "au": 9.58, "year": "29,5 años"},
    {"name": "Urano", "orbit": 43.2, "angle": 65, "radius": 1.48, "color": "#8bcbd0",
     "info": "Gigante helado, rota de lado", "au": 19.2, "year": "84 años"},
    {"name": "Neptuno", "orbit": 52.0, "angle": 235, "radius": 1.45, "color": "#5479dc",
     "info": "Último planeta de la ruta", "au": 30.1, "year": "165 años"},
]

for _planet in PLANETS:
    _angle = math.radians(_planet["angle"])
    _planet["pos"] = (_planet["orbit"] * math.cos(_angle), _planet["orbit"] * math.sin(_angle), 0.0)

EARTH = next(p["pos"] for p in PLANETS if p["name"] == "Tierra")
MOON = v_add(EARTH, (1.45, 0.45, 0.28))  # distancia lunar exagerada para verla
_MOON_R = math.hypot(MOON[0] - EARTH[0], MOON[1] - EARTH[1])

SUN_BODY = {"name": "Sol", "pos": SUN, "radius": SUN_RADIUS / 1.15, "color": "#ffd783",
            "info": "Estrella de tipo G, centro del sistema", "au": None, "year": None}
MOON_BODY = {"name": "Luna", "pos": MOON, "radius": 0.40, "color": "#c4c9d2",
             "info": "Satélite natural de la Tierra\n(distancia exagerada)", "au": 1.00,
             "year": "27,3 días (órbita)"}

BODIES = [SUN_BODY] + PLANETS + [MOON_BODY]
BODY_BY_NAME = {b["name"]: b for b in BODIES}

ORBIT_RINGS = {p["name"]: [(p["orbit"] * math.cos(2 * math.pi * i / 96),
                            p["orbit"] * math.sin(2 * math.pi * i / 96), 0.0)
                           for i in range(97)] for p in PLANETS}
MOON_ORBIT = [v_add(EARTH, (_MOON_R * math.cos(2 * math.pi * i / 48),
                            _MOON_R * math.sin(2 * math.pi * i / 48), 0.28))
              for i in range(49)]


# -----------------------------------------------------------------------------
# CONSTRUCCIÓN DE LA RUTA (con tiempos por etapa para dar ritmo al viaje)
# -----------------------------------------------------------------------------

def build_mission():
    """Devuelve ruta, distancias acumuladas, etapas y distancia total."""
    segments = []  # (etiqueta, puntos, tipo, segundos a velocidad 1×)
    ship_start = v_add(EARTH, (0.0, -1.35, 0.35))

    moon_entry = v_add(MOON, (1.25, 0.0, 0.0))
    segments.append(("Tierra → Luna", make_transfer(ship_start, moon_entry, side=1, lift=2.8),
                     "transfer", 8.0))
    segments.append(("Vuelta alrededor de la Luna",
                     make_orbit(MOON, 1.25, phase=0.0, inclination=0.55, steps=150), "orbit", 6.0))

    previous = moon_entry
    # (cuerpo, radio de órbita, inclinación, s de crucero, s de órbita)
    destinations = [
        ("Marte", 1.55, 0.18, 12.0, 6.0),
        ("Júpiter", 4.2, 0.38, 15.0, 8.0),
        ("Saturno", 3.8, 0.48, 15.0, 8.0),
        ("Urano", 2.6, 0.62, 15.0, 7.0),
        ("Neptuno", 2.6, 0.72, 15.0, 7.0),
    ]

    for index, (name, orbit_radius, inclination, t_cruise, t_orbit) in enumerate(destinations):
        body = BODY_BY_NAME[name]
        entry = v_add(body["pos"], (orbit_radius, 0.0, 0.0))
        label = "Crucero: Luna → Marte" if name == "Marte" else f"Crucero hacia {name}"
        segments.append((label, make_transfer(previous, entry, side=(-1) ** index,
                                              lift=4.0 + index * 1.4), "transfer", t_cruise))
        segments.append((f"Vuelta alrededor de {name}",
                         make_orbit(body["pos"], orbit_radius, phase=0.0,
                                    inclination=inclination, steps=160), "orbit", t_orbit))
        previous = entry

    neptune = BODY_BY_NAME["Neptuno"]["pos"]
    outward = v_normalize(neptune)
    exit_point = v_add(neptune, v_add(v_mul(outward, 15.0), (0.0, 0.0, 8.0)))
    segments.append(("Salida del Sistema Solar",
                     make_transfer(previous, exit_point, side=1, lift=13.0, steps=190),
                     "transfer", 16.0))

    route, cumulative, stages = [], [], []
    total, clock = 0.0, 0.0
    for label, points, kind, seconds in segments:
        start_distance = total
        if route and points:
            points = points[1:]  # evita duplicar el punto de unión
        for point in points:
            if route:
                total += v_length(v_sub(point, route[-1]))
            route.append(point)
            cumulative.append(total)
        stages.append({"label": label, "kind": kind, "start": start_distance, "end": total,
                       "t0": clock, "t1": clock + seconds})
        clock += seconds

    return route, cumulative, stages, total, clock


ROUTE, ROUTE_DISTANCE, STAGES, TOTAL_DISTANCE, TOTAL_TIME = build_mission()
ROUTE_BACKGROUND = ROUTE[::5] + ([ROUTE[-1]] if (len(ROUTE) - 1) % 5 else [])


def _stage_of(prefix):
    return next(i for i, s in enumerate(STAGES) if s["label"].startswith(prefix))


# (nombre, etapa de llegada) — se usa para el itinerario clicable
ITINERARY = [
    ("Tierra", 0),
    ("Luna", _stage_of("Vuelta alrededor de la Luna")),
    ("Marte", _stage_of("Vuelta alrededor de Marte")),
    ("Júpiter", _stage_of("Vuelta alrededor de Júpiter")),
    ("Saturno", _stage_of("Vuelta alrededor de Saturno")),
    ("Urano", _stage_of("Vuelta alrededor de Urano")),
    ("Neptuno", _stage_of("Vuelta alrededor de Neptuno")),
    ("Salida solar", _stage_of("Salida")),
]


def stage_index_at(progress):
    t = clamp(progress, 0.0, 1.0) * TOTAL_TIME
    for i, stage in enumerate(STAGES):
        if t <= stage["t1"]:
            return i
    return len(STAGES) - 1


def distance_at(progress):
    """Progreso temporal (0..1) → distancia recorrida, con aceleración suave en los cruceros."""
    t = clamp(progress, 0.0, 1.0) * TOTAL_TIME
    for stage in STAGES:
        if t <= stage["t1"]:
            u = (t - stage["t0"]) / (stage["t1"] - stage["t0"])
            if stage["kind"] == "transfer":
                u = 0.5 * u + 0.5 * smoothstep(u)
            return stage["start"] + u * (stage["end"] - stage["start"])
    return TOTAL_DISTANCE


def route_sample(distance):
    """Interpolación por longitud de arco: devuelve posición, tangente e índice."""
    if distance <= 0:
        return ROUTE[0], v_normalize(v_sub(ROUTE[1], ROUTE[0])), 0
    if distance >= TOTAL_DISTANCE:
        return ROUTE[-1], v_normalize(v_sub(ROUTE[-1], ROUTE[-2])), len(ROUTE) - 1

    lo, hi = 0, len(ROUTE_DISTANCE) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if ROUTE_DISTANCE[mid] < distance:
            lo = mid + 1
        else:
            hi = mid
    index = max(1, lo)
    d0, d1 = ROUTE_DISTANCE[index - 1], ROUTE_DISTANCE[index]
    factor = 0.0 if d1 == d0 else (distance - d0) / (d1 - d0)
    position = v_lerp(ROUTE[index - 1], ROUTE[index], factor)
    tangent = v_normalize(v_sub(ROUTE[index], ROUTE[index - 1]))
    return position, tangent, index


# -----------------------------------------------------------------------------
# VENTANA Y RENDERIZADO 3D EN TKINTER
# -----------------------------------------------------------------------------

PERSPECTIVE = 260.0   # distancia de la cámara (en u.v.) para el efecto de perspectiva
STAR_SHADES = [mix("#222f45", "#c3d1ea", i / 7.0) for i in range(8)]


class Solar3D:
    BG = "#080d18"
    SPACE = "#050912"
    PANEL = "#101a2b"
    TEXT = "#e8f0ff"
    MUTED = "#91a4c2"
    CYAN = "#65e6e2"
    GOLD = "#f4c879"
    DIM = "#5d708c"

    def __init__(self, root):
        self.root = root
        self.root.title("solar3D.py | Soyuz — Solar System Tour")
        self.root.geometry("1280x840")
        self.root.minsize(940, 660)
        self.root.configure(bg=self.BG)

        self.ready = False
        self.paused = False
        self.scrubbing = False
        self.progress = 0.0
        self.speed = 1.0
        self.stage_idx = 0

        # Cámara orbital: yaw/elev (rad), zoom suavizado, objetivo y astro enfocado.
        self.yaw, self.elev = 0.25, 0.85
        self.zoom = self.zoom_goal = 1.0
        self.target = SUN
        self.focus = "Sol"
        self.selected = None
        self.auto_rotate = True
        self.show_route = self.show_orbits = self.show_labels = True
        self.dragging = False
        self.drag_last = (0, 0)
        self.drag_moved = 0

        self.ship_pos, self.ship_tangent = ROUTE[0], v_normalize(v_sub(ROUTE[1], ROUTE[0]))
        self.ship_angle = 0.0
        self.hits = []
        self.sun_xy = (0.0, 0.0)
        self.frame = 0
        self.fps = 30.0
        self.cw, self.ch = 1000, 700
        self.last_time = time.perf_counter()
        self.stars = self.make_stars()
        self.belt = self.make_belt()
        self._slider_lock = False

        self.configure_style()
        self.build_interface()
        self.bind_events()
        self.ready = True
        self.update_ship()
        self.update_camera()
        self.animate()

    # -- Datos procedurales ----------------------------------------------------
    @staticmethod
    def make_stars():
        rng = random.Random(17)
        stars = []
        for _ in range(280):
            z = rng.uniform(-1.0, 1.0)
            a = rng.uniform(0.0, 2.0 * math.pi)
            r = math.sqrt(1.0 - z * z)
            d = rng.uniform(60.0, 115.0)
            stars.append(((r * math.cos(a) * d, r * math.sin(a) * d, z * d),
                          rng.choice((1, 1, 1, 2)), rng.uniform(0, 6.28), rng.uniform(0.6, 1.5)))
        return stars

    @staticmethod
    def make_belt():
        rng = random.Random(5)
        shades = ("#6f7480", "#8a8578", "#5c6270")
        belt = []
        for _ in range(170):
            radius = rng.uniform(19.3, 22.6)
            a = rng.uniform(0.0, 2.0 * math.pi)
            belt.append(((radius * math.cos(a), radius * math.sin(a), rng.gauss(0.0, 0.25)),
                         rng.choice(shades)))
        return belt

    # -- Interfaz --------------------------------------------------------------
    def configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("DejaVu Sans", 9), padding=(9, 6),
                        background="#20324b", foreground=self.TEXT, borderwidth=0)
        style.map("TButton", background=[("active", "#345274")])
        style.configure("Horizontal.TScale", background=self.PANEL, troughcolor="#26364d")
        style.configure("TCheckbutton", background=self.PANEL, foreground=self.TEXT,
                        font=("DejaVu Sans", 9))
        style.map("TCheckbutton", background=[("active", self.PANEL)])

    def build_interface(self):
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(header, text="SOLAR 3D", bg=self.BG, fg=self.TEXT,
                 font=("DejaVu Sans", 21, "bold")).pack(side="left")
        tk.Label(header, text=" /  SOYUZ DEEP-SPACE TOUR", bg=self.BG, fg=self.CYAN,
                 font=("DejaVu Sans", 10, "bold")).pack(side="left", padx=(10, 0), pady=(8, 0))
        tk.Label(header, text="SIMULACIÓN VECTORIAL 3D · MODO ILUSTRATIVO", bg=self.BG,
                 fg=self.MUTED, font=("DejaVu Sans", 8)).pack(side="right", pady=(12, 0))

        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=16, pady=4)

        visual = tk.Frame(content, bg=self.SPACE, highlightbackground="#1c2b42", highlightthickness=1)
        visual.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(visual, bg=self.SPACE, highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill="both", expand=True)

        side = tk.Frame(content, bg=self.PANEL, width=252)
        side.pack(side="right", fill="y", padx=(10, 0))
        side.pack_propagate(False)
        self.build_side_panel(side)

        controls = tk.Frame(self.root, bg=self.PANEL, highlightbackground="#1c2b42", highlightthickness=1)
        controls.pack(fill="x", padx=16, pady=(8, 4))
        row = tk.Frame(controls, bg=self.PANEL)
        row.pack(fill="x")

        def button(text, command):
            b = ttk.Button(row, text=text, command=command, takefocus=False)
            b.pack(side="left", padx=4, pady=(8, 4))
            return b

        self.pause_button = button("Ⅱ  Pausar", self.toggle_pause)
        self.pause_button.pack_configure(padx=(10, 4))
        button("↺  Reiniciar", self.reset)
        button("−  Retroceder", lambda: self.seek(-0.04))
        button("+  Avanzar", lambda: self.seek(0.04))
        button("◎  Vista general", self.overview)

        tk.Label(row, text="VELOCIDAD", bg=self.PANEL, fg=self.MUTED,
                 font=("DejaVu Sans", 8, "bold")).pack(side="left", padx=(18, 5), pady=(8, 4))
        self.speed_value = tk.StringVar(value="1.0×")
        self.speed_scale = ttk.Scale(row, from_=0.25, to=4.0, value=1.0, command=self.change_speed,
                                     length=120, takefocus=False)
        self.speed_scale.pack(side="left", padx=5, pady=(8, 4))
        tk.Label(row, textvariable=self.speed_value, bg=self.PANEL, fg=self.CYAN,
                 font=("DejaVu Sans", 9, "bold"), width=5).pack(side="left", pady=(8, 4))

        self.rotate_var = tk.BooleanVar(value=True)
        self.route_var = tk.BooleanVar(value=True)
        self.labels_var = tk.BooleanVar(value=True)
        self.orbits_var = tk.BooleanVar(value=True)
        self.follow_var = tk.BooleanVar(value=False)
        for text, var, cmd in (
                ("Cámara auto", self.rotate_var, lambda: setattr(self, "auto_rotate", self.rotate_var.get())),
                ("Etiquetas", self.labels_var, lambda: setattr(self, "show_labels", self.labels_var.get())),
                ("Órbitas", self.orbits_var, lambda: setattr(self, "show_orbits", self.orbits_var.get())),
                ("Ruta", self.route_var, lambda: setattr(self, "show_route", self.route_var.get())),
                ("Seguir nave", self.follow_var, self.toggle_follow)):
            ttk.Checkbutton(row, text=text, variable=var, command=cmd, takefocus=False
                            ).pack(side="right", padx=6, pady=(8, 4))

        # Línea de tiempo: arrastra para saltar a cualquier punto de la misión.
        row2 = tk.Frame(controls, bg=self.PANEL)
        row2.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(row2, text="MISIÓN", bg=self.PANEL, fg=self.MUTED,
                 font=("DejaVu Sans", 8, "bold")).pack(side="left", padx=(0, 8))
        self.timeline = ttk.Scale(row2, from_=0.0, to=1.0, command=self.on_timeline, takefocus=False)
        self.timeline.pack(side="left", fill="x", expand=True)
        self.timeline.bind("<ButtonPress-1>", lambda _e: setattr(self, "scrubbing", True))
        self.timeline.bind("<ButtonRelease-1>", lambda _e: setattr(self, "scrubbing", False))

        tk.Label(self.root,
                 text="Arrastrar: rotar  ·  Rueda: zoom  ·  Clic en astro: enfocar  ·  ESPACIO: pausa  ·  "
                      "R: reiniciar  ·  ←/→: saltar  ·  F: seguir nave  ·  V: vista general  |  "
                      "Distancias y tiempos NO están a escala real",
                 bg=self.BG, fg="#71839e", font=("DejaVu Sans", 8)).pack(pady=(0, 7))

    def build_side_panel(self, panel):
        def heading(text):
            tk.Label(panel, text=text, bg=self.PANEL, fg=self.MUTED,
                     font=("DejaVu Sans", 8, "bold")).pack(anchor="w", padx=14, pady=(13, 4))

        def info(text="", fg=None, font=("DejaVu Sans", 8)):
            label = tk.Label(panel, text=text, bg=self.PANEL, fg=fg or self.TEXT, font=font,
                             justify="left", anchor="w", wraplength=225)
            label.pack(anchor="w", padx=14, pady=1)
            return label

        heading("ESTADO DE LA MISIÓN")
        self.status_label = info("En preparación", self.CYAN, ("DejaVu Sans", 11, "bold"))
        self.progress_label = info("0.0 % completado", font=("DejaVu Sans", 9))

        heading("TELEMETRÍA VECTORIAL")
        self.position_label = info("Posición: —")
        self.velocity_label = info("Dirección: —")
        self.distance_label = info("Recorrido: —")
        self.speed_label = info("Velocidad: —")
        self.time_label = info("Tiempo simulado: —")

        heading("OBJETO SELECCIONADO")
        self.sel_title = info("—", self.GOLD, ("DejaVu Sans", 10, "bold"))
        self.sel_text = info("Haz clic en un astro\no en la nave para enfocarlo.", self.MUTED)

        heading("ITINERARIO  (clic para saltar)")
        self.itinerary_labels = []
        for i, (name, arrival) in enumerate(ITINERARY):
            label = tk.Label(panel, text=f"○ {i + 1:02d}  {name}", bg=self.PANEL, fg=self.DIM,
                             anchor="w", font=("DejaVu Sans Mono", 9), cursor="hand2")
            label.pack(anchor="w", padx=14)
            label.bind("<Button-1>", lambda _e, st=arrival: self.jump_to_stage(st))
            self.itinerary_labels.append(label)

        tk.Label(panel, text="MODELO SIMPLIFICADO\nVectores 3D + curvas Bézier.\nNo es una trayectoria real.",
                 bg=self.PANEL, fg="#8da0bc", justify="left",
                 font=("DejaVu Sans", 8)).pack(side="bottom", anchor="w", padx=14, pady=12)

    def bind_events(self):
        c = self.canvas
        c.bind("<Configure>", lambda _e: self.draw_scene())
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<MouseWheel>", lambda e: self.zoom_by(1.12 if e.delta > 0 else 1 / 1.12))
        c.bind("<Button-4>", lambda _e: self.zoom_by(1.12))   # X11/Wayland (XWayland)
        c.bind("<Button-5>", lambda _e: self.zoom_by(1 / 1.12))
        r = self.root
        r.bind("<space>", lambda _e: self.toggle_pause())
        r.bind("<r>", lambda _e: self.reset())
        r.bind("<Left>", lambda _e: self.seek(-0.025))
        r.bind("<Right>", lambda _e: self.seek(0.025))
        r.bind("<f>", lambda _e: self.set_follow(self.focus != "Nave"))
        r.bind("<v>", lambda _e: self.overview())
        r.bind("<l>", lambda _e: self.toggle_var(self.labels_var, "show_labels"))
        r.bind("<o>", lambda _e: self.toggle_var(self.orbits_var, "show_orbits"))
        for key in ("<plus>", "<equal>", "<KP_Add>"):
            r.bind(key, lambda _e: self.zoom_by(1.2))
        for key in ("<minus>", "<KP_Subtract>"):
            r.bind(key, lambda _e: self.zoom_by(1 / 1.2))
        r.bind("<F11>", lambda _e: r.attributes("-fullscreen", not r.attributes("-fullscreen")))
        r.bind("<Escape>", lambda _e: r.attributes("-fullscreen", False))

    # -- Cámara ----------------------------------------------------------------
    def update_camera(self):
        self.cw = max(self.canvas.winfo_width(), 500)
        self.ch = max(self.canvas.winfo_height(), 400)
        sy, cy = math.sin(self.yaw), math.cos(self.yaw)
        se, ce = math.sin(self.elev), math.cos(self.elev)
        self.cam_r = (cy, sy, 0.0)                    # derecha de pantalla
        self.cam_u = (-se * sy, se * cy, ce)          # arriba de pantalla
        self.cam_c = (ce * sy, -ce * cy, se)          # hacia el observador
        self.base0 = min(self.cw / 118.0, self.ch / 112.0)
        self.base = self.base0 * self.zoom

    def project(self, p):
        """Vector 3D → (x_pantalla, y_pantalla, escala_px_por_uv, profundidad)."""
        tx, ty, tz = self.target
        x, y, z = p[0] - tx, p[1] - ty, p[2] - tz
        r, u, c = self.cam_r, self.cam_u, self.cam_c
        sx = x * r[0] + y * r[1]
        sy = x * u[0] + y * u[1] + z * u[2]
        depth = x * c[0] + y * c[1] + z * c[2]
        f = clamp(PERSPECTIVE / max(PERSPECTIVE - depth, 40.0), 0.6, 1.8)
        s = self.base * f
        return self.cw * 0.5 + sx * s, self.ch * 0.5 - sy * s, s, depth

    def focus_position(self):
        if self.focus == "Nave":
            return self.ship_pos
        body = BODY_BY_NAME.get(self.focus)
        return body["pos"] if body else SUN

    def step_camera(self, dt):
        self.target = v_lerp(self.target, self.focus_position(), 1.0 - math.exp(-dt * 8.0))
        self.zoom += (self.zoom_goal - self.zoom) * (1.0 - math.exp(-dt * 7.0))
        if self.auto_rotate and not self.dragging:
            self.yaw += dt * 0.05

    def zoom_by(self, factor):
        self.zoom_goal = clamp(self.zoom_goal * factor, 0.5, 16.0)

    def overview(self):
        self.focus, self.zoom_goal = "Sol", 1.0
        self.follow_var.set(False)

    def set_follow(self, on):
        self.follow_var.set(on)
        if on:
            self.select("Nave")
        else:
            self.overview()

    def toggle_follow(self):
        self.set_follow(self.follow_var.get())

    def toggle_var(self, var, attr):
        var.set(not var.get())
        setattr(self, attr, var.get())

    # -- Ratón -----------------------------------------------------------------
    def on_press(self, event):
        self.canvas.focus_set()
        self.dragging = True
        self.drag_last = (event.x, event.y)
        self.drag_moved = 0

    def on_drag(self, event):
        dx, dy = event.x - self.drag_last[0], event.y - self.drag_last[1]
        self.drag_last = (event.x, event.y)
        self.drag_moved += abs(dx) + abs(dy)
        self.yaw -= dx * 0.008
        self.elev = clamp(self.elev + dy * 0.006, 0.08, 1.50)

    def on_release(self, event):
        self.dragging = False
        if self.drag_moved < 5:
            self.pick(event.x, event.y)

    def pick(self, mx, my):
        best, best_d = None, None
        for x, y, r, name in self.hits:  # gana el centro más cercano al clic
            d = (mx - x) ** 2 + (my - y) ** 2
            if d <= (max(r, 9.0) + 3.0) ** 2 and (best_d is None or d < best_d):
                best, best_d = name, d
        if best:
            self.select(best)

    def select(self, name):
        self.selected = name
        self.focus = name
        if name == "Nave":
            self.zoom_goal = 3.5
        elif name == "Sol":
            self.zoom_goal = 1.0
        elif name == "Luna":
            self.zoom_goal = 7.0
        else:
            self.zoom_goal = clamp(3.2 / math.sqrt(max(BODY_BY_NAME[name]["radius"], 0.8)), 1.8, 4.0)
        self.follow_var.set(name == "Nave")
        self.refresh_selection()

    # -- Controles de misión ---------------------------------------------------
    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.config(text="▶  Continuar" if self.paused else "Ⅱ  Pausar")
        self.last_time = time.perf_counter()

    def reset(self):
        self.progress = 0.0
        self.paused = False
        self.pause_button.config(text="Ⅱ  Pausar")
        self.last_time = time.perf_counter()

    def seek(self, amount):
        self.progress = clamp(self.progress + amount, 0.0, 1.0)

    def jump_to_stage(self, stage_index):
        self.progress = STAGES[stage_index]["t0"] / TOTAL_TIME

    def on_timeline(self, value):
        if not self._slider_lock:
            self.progress = clamp(float(value), 0.0, 1.0)

    def change_speed(self, value):
        self.speed = float(value)
        self.speed_value.set(f"{self.speed:.1f}×")

    # -- Panel lateral ---------------------------------------------------------
    def refresh_selection(self):
        name = self.selected
        if name is None:
            self.sel_title.config(text="—")
            self.sel_text.config(text="Haz clic en un astro\no en la nave para enfocarlo.")
            return
        if name == "Nave":
            self.sel_title.config(text="SOYUZ")
            lines = ["Nave estilizada: cápsula,", "módulo orbital y paneles.",
                     f"Etapa {self.stage_idx + 1} de {len(STAGES)}"]
        else:
            body = BODY_BY_NAME[name]
            self.sel_title.config(text=name.upper())
            lines = [body["info"]]
            if body.get("au"):
                lines.append(f"Distancia al Sol: {body['au']:.2f} UA")
            if body.get("year"):
                lines.append(f"Año: {body['year']}")
            lines.append(f"Distancia a la nave: {v_length(v_sub(body['pos'], self.ship_pos)):.1f} u.v.")
        self.sel_text.config(text="\n".join(lines), fg=self.TEXT)

    def update_panel(self, position, tangent, distance):
        stage = STAGES[self.stage_idx]
        years = self.progress * 18.0
        dp = 0.001
        velocity = (distance_at(min(1.0, self.progress + dp)) - distance_at(max(0.0, self.progress - dp))) \
            / (2 * dp * TOTAL_TIME)
        self.status_label.config(text=stage["label"])
        self.progress_label.config(text=f"{100 * self.progress:05.1f} % completado")
        self.position_label.config(text=f"Posición  {position[0]:6.1f}, {position[1]:6.1f}, {position[2]:6.1f}")
        self.velocity_label.config(text=f"Vector dir. {tangent[0]:+.2f}, {tangent[1]:+.2f}, {tangent[2]:+.2f}")
        self.distance_label.config(text=f"Recorrido  {distance:,.1f} u.v.")
        self.speed_label.config(text=f"Velocidad  {0 if self.paused else velocity * self.speed:.1f} u.v./s")
        self.time_label.config(text=f"Tiempo ficticio  {years:04.1f} años")

        next_i = next((i for i, (_, arr) in enumerate(ITINERARY) if arr > self.stage_idx), None)
        for i, ((name, arrival), label) in enumerate(zip(ITINERARY, self.itinerary_labels)):
            if arrival < self.stage_idx:
                mark, color = "✓", self.MUTED
            elif arrival == self.stage_idx:
                mark, color = "●", self.CYAN
            elif i == next_i:
                mark, color = "►", self.GOLD
            else:
                mark, color = "○", self.DIM
            label.config(text=f"{mark} {i + 1:02d}  {name}", fg=color)
        if self.selected:
            self.refresh_selection()

    # -- Dibujo ----------------------------------------------------------------
    def update_ship(self):
        distance = distance_at(self.progress)
        self.ship_pos, self.ship_tangent, self.route_index = route_sample(distance)
        self.stage_idx = stage_index_at(self.progress)
        self.travelled = distance

    def flat(self, points):
        out = []
        for p in points:
            x, y, _, _ = self.project(p)
            out.append(x)
            out.append(y)
        return out

    def polyline(self, points, color, width=1, dash=None):
        if len(points) < 2:
            return
        options = {"fill": color, "width": width, "capstyle": tk.ROUND, "joinstyle": tk.ROUND}
        if dash:
            options["dash"] = dash
        self.canvas.create_line(*self.flat(points), **options)

    def draw_stars(self, now):
        c = self.canvas
        r, u = self.cam_r, self.cam_u
        scale = self.base0 * 0.95
        cx, cy = self.cw * 0.5, self.ch * 0.5
        for (p, size, phase, rate) in self.stars:
            x = cx + (p[0] * r[0] + p[1] * r[1]) * scale
            y = cy - (p[0] * u[0] + p[1] * u[1] + p[2] * u[2]) * scale
            if 0 <= x <= self.cw and 0 <= y <= self.ch:
                shade = STAR_SHADES[int((0.5 + 0.5 * math.sin(now * rate + phase)) * 7.99)]
                c.create_rectangle(x, y, x + size, y + size, fill=shade, outline="")

    def draw_orbits(self):
        for planet in PLANETS:
            hot = self.selected == planet["name"]
            self.polyline(ORBIT_RINGS[planet["name"]], "#3b5f88" if hot else "#1b2b40", 1)
        self.polyline(MOON_ORBIT, "#3d5069", 1, dash=(2, 4))

    def draw_belt(self):
        if not self.show_orbits:
            return
        c = self.canvas
        for p, color in self.belt:
            x, y, _, _ = self.project(p)
            c.create_rectangle(x, y, x + 1.4, y + 1.4, fill=color, outline="")

    def draw_route(self):
        if not self.show_route:
            return
        self.polyline(ROUTE_BACKGROUND, "#2a4260", 1, dash=(3, 6))
        travelled = ROUTE[:self.route_index:3] + [self.ship_pos]
        self.polyline(travelled, "#123a40", 5)   # halo
        self.polyline(travelled, self.CYAN, 2)   # cinta luminosa

    def draw_sphere(self, x, y, r, color, lx, ly):
        """Esfera sombreada: sombra base, zona iluminada hacia el Sol y un brillo."""
        c = self.canvas
        c.create_oval(x - r, y - r, x + r, y + r, fill=mix(color, "#05070d", 0.62),
                      outline=mix(color, "#ffffff", 0.25))
        if r < 4:
            return
        r2 = r * 0.88
        ox, oy = x + lx * r * 0.12, y + ly * r * 0.12
        c.create_oval(ox - r2, oy - r2, ox + r2, oy + r2, fill=color, outline="")
        r3 = r * 0.42
        hx, hy = x + lx * r * 0.36, y + ly * r * 0.36
        c.create_oval(hx - r3, hy - r3, hx + r3, hy + r3, fill=mix(color, "#ffffff", 0.28), outline="")

    def light_dir(self, x, y):
        lx, ly = self.sun_xy[0] - x, self.sun_xy[1] - y
        length = math.hypot(lx, ly)
        return (lx / length, ly / length) if length > 1e-6 else (-0.6, -0.6)

    def saturn_ring(self, x, y, r, back):
        tilt = max(0.10, math.sin(self.elev))
        for factor, color, width in ((1.95, "#c6ae7d", 3), (1.6, "#8a795e", 2)):
            rx = r * factor
            ry = rx * tilt
            self.canvas.create_arc(x - rx, y - ry, x + rx, y + ry, start=0 if back else 180,
                                   extent=180, style=tk.ARC, outline=color, width=width)

    def draw_label(self, text, x, y, r, selected):
        if self.show_labels or selected:
            self.canvas.create_text(x + r + 5, y - r - 3, text=text, anchor="sw",
                                    fill=self.GOLD if selected else "#d5e1f3",
                                    font=("DejaVu Sans", 8, "bold" if selected else "normal"))

    def draw_marker(self, x, y, r, selected):
        if selected:
            m = r + 7
            self.canvas.create_oval(x - m, y - m, x + m, y + m, outline=self.GOLD, dash=(3, 3))

    def draw_sun(self, x, y, s, now):
        c = self.canvas
        r = SUN_RADIUS * s
        pulse = 1.0 + 0.03 * math.sin(now * 2.0)
        for factor, color in ((1.9, "#2a2018"), (1.55, "#4a3420"), (1.25, "#8a5a28")):
            rr = r * factor * pulse
            c.create_oval(x - rr, y - rr, x + rr, y + rr, fill=color, outline="")
        c.create_oval(x - r, y - r, x + r, y + r, fill="#ffd783", outline="#fff0bd")
        c.create_oval(x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55, fill="#ffe9ae", outline="")
        selected = self.selected == "Sol"
        self.draw_marker(x, y, r * 1.25, selected)
        if self.show_labels or selected:
            c.create_text(x + 14, y + r * 1.25 + 4, text="SOL", fill="#f4d69b", anchor="w",
                          font=("DejaVu Sans", 8, "bold"))
        self.hits.append((x, y, r, "Sol"))

    def draw_planet(self, body, x, y, s):
        c = self.canvas
        name = body["name"]
        color = body["color"]
        r = max(3.5, body["radius"] * 1.15 * s)
        lx, ly = self.light_dir(x, y)
        selected = self.selected == name

        if name == "Saturno":
            self.saturn_ring(x, y, r, back=True)
        if name == "Tierra":
            c.create_oval(x - r * 1.18, y - r * 1.18, x + r * 1.18, y + r * 1.18,
                          outline="#2d5f8f", width=2)
        self.draw_sphere(x, y, r, color, lx, ly)

        if name in ("Júpiter", "Saturno") and r > 6:
            for k in (-0.5, -0.15, 0.25, 0.55):
                half = r * math.sqrt(1.0 - k * k) * 0.94
                c.create_line(x - half, y + k * r, x + half, y + k * r,
                              fill=mix(color, "#7a4a2a", 0.35), width=max(1, int(r * 0.11)))
        elif name == "Tierra" and r > 6:
            c.create_arc(x - r * 0.7, y - r * 0.6, x + r * 0.7, y + r * 0.6, start=20, extent=130,
                         style=tk.ARC, outline="#85d4a4", width=2)
        elif name == "Marte" and r > 6:
            c.create_oval(x - r * 0.25, y - r * 0.92, x + r * 0.25, y - r * 0.62,
                          fill="#f2f2f2", outline="")
        if name == "Saturno":
            self.saturn_ring(x, y, r, back=False)

        self.draw_marker(x, y, r * (1.95 if name == "Saturno" else 1.0), selected)
        self.draw_label(name, x, y, r, selected)
        self.hits.append((x, y, r, name))

    def draw_moon(self, body, x, y, s):
        r = max(2.5, body["radius"] * s)
        lx, ly = self.light_dir(x, y)
        self.draw_sphere(x, y, r, body["color"], lx, ly)
        selected = self.selected == "Luna"
        self.draw_marker(x, y, r, selected)
        if self.zoom > 1.6 or selected:
            self.draw_label("Luna", x, y, r, selected)
        self.hits.append((x, y, r, "Luna"))

    def draw_ship(self, x, y, s):
        """Nave Soyuz estilizada, orientada según la tangente de la ruta en pantalla."""
        c = self.canvas
        ahead = self.project(v_add(self.ship_pos, v_mul(self.ship_tangent, 0.5)))
        dx, dy = ahead[0] - x, ahead[1] - y
        if abs(dx) + abs(dy) > 1e-3:
            self.ship_angle = math.atan2(-dy, dx)
        angle = self.ship_angle
        ca, sa = math.cos(angle), math.sin(angle)
        size = clamp(s / 9.0, 0.9, 3.2)

        def local(forward, side):
            return (x + (forward * ca - side * sa) * size,
                    y - (forward * sa + side * ca) * size)

        def polygon(points, fill, outline="#e7f0ff"):
            coords = []
            for f, sd in points:
                coords.extend(local(f, sd))
            c.create_polygon(*coords, fill=fill, outline=outline, width=1)

        # Llama del motor (parpadea mientras avanza).
        if not self.paused and self.progress < 1.0:
            flame = random.uniform(4.0, 8.0)
            polygon([(-8.5, -1.8), (-8.5 - flame, 0), (-8.5, 1.8)], "#75e7e0", "#c8fffb")
        polygon([(-7, 5), (-3, 5), (-3, 12), (-7, 12)], "#315c89", "#77a9d8")      # paneles
        polygon([(-7, -12), (-3, -12), (-3, -5), (-7, -5)], "#315c89", "#77a9d8")
        for side in (-1, 1):
            p1, p2 = local(-5, side * 5), local(-5, side * 12)
            c.create_line(*p1, *p2, fill="#9bc9f0", width=1)
        polygon([(-8, -3.3), (-2, -3.3), (-2, 3.3), (-8, 3.3)], "#a8b6c7")          # servicio
        polygon([(-3, -3.7), (4, -3.7), (5, 0), (4, 3.7), (-3, 3.7)], "#e2e8ef")    # orbital
        polygon([(10, 0), (4, -3.5), (-1, -3.5), (-3, 0), (-1, 3.5), (4, 3.5)],     # cápsula
                "#f5c879", "#fff0c7")
        wx, wy = local(3.5, 0)
        rw = 1.35 * size
        c.create_oval(wx - rw, wy - rw, wx + rw, wy + rw, fill="#223a57", outline="#d8e6f4")

        selected = self.selected == "Nave"
        self.draw_marker(x, y, 13 * size, selected)
        c.create_text(x + 14 * size, y + 15 * size, text="SOYUZ", fill=self.GOLD, anchor="nw",
                      font=("DejaVu Sans", 8, "bold"))
        self.hits.append((x, y, 11 * size, "Nave"))

    def draw_hud(self):
        c = self.canvas
        stage = STAGES[self.stage_idx]["label"]
        c.create_rectangle(14, 14, 330, 91, fill="#0b1423", outline="#263b56")
        c.create_text(27, 28, text="DEEP SPACE NAVIGATION", fill=self.CYAN, anchor="nw",
                      font=("DejaVu Sans", 8, "bold"))
        c.create_text(27, 48, text=f"ETAPA  /  {stage.upper()}", fill=self.TEXT, anchor="nw",
                      width=290, font=("DejaVu Sans", 9))
        c.create_text(27, 72, text=f"MISSION CLOCK  {self.progress * 18.0:05.2f} y", fill=self.MUTED,
                      anchor="nw", font=("DejaVu Sans Mono", 8))
        c.create_text(self.cw - 14, 16, anchor="ne", fill="#5f7390", font=("DejaVu Sans Mono", 8),
                      text=f"{self.fps:4.0f} fps · zoom {self.zoom:.1f}× · foco: {self.focus}")
        if self.progress >= 1.0:
            c.create_rectangle(14, 104, 330, 137, fill="#102a2a", outline=self.CYAN)
            c.create_text(25, 120, text="OBJETIVO ALCANZADO · RUTA DE ESCAPE", anchor="w",
                          fill=self.CYAN, font=("DejaVu Sans", 8, "bold"))
        if self.paused:
            c.create_rectangle(self.cw / 2 - 78, self.ch - 54, self.cw / 2 + 78, self.ch - 20,
                               fill=self.PANEL, outline="#45617d")
            c.create_text(self.cw / 2, self.ch - 37, text="SIMULACIÓN EN PAUSA", fill=self.GOLD,
                          font=("DejaVu Sans", 9, "bold"))

    def draw_scene(self):
        if not self.ready:
            return
        now = time.perf_counter()
        self.update_ship()
        self.update_camera()
        c = self.canvas
        c.delete("all")
        self.hits = []
        self.sun_xy = self.project(SUN)[:2]

        self.draw_stars(now)
        if self.show_orbits:
            self.draw_orbits()
        self.draw_belt()
        self.draw_route()

        # Algoritmo del pintor: los objetos más lejanos se dibujan primero.
        queue = []
        for body in BODIES:
            x, y, s, depth = self.project(body["pos"])
            queue.append((depth, body["name"], body, x, y, s))
        sx, sy, ss, sd = self.project(self.ship_pos)
        queue.append((sd + 0.05, "Nave", None, sx, sy, ss))
        queue.sort(key=lambda item: item[0])

        for _depth, name, body, x, y, s in queue:
            if name == "Sol":
                self.draw_sun(x, y, s, now)
            elif name == "Luna":
                self.draw_moon(body, x, y, s)
            elif name == "Nave":
                self.draw_ship(x, y, s)
            else:
                self.draw_planet(body, x, y, s)

        self.draw_hud()

    # -- Bucle principal ---------------------------------------------------------
    def animate(self):
        now = time.perf_counter()
        dt = clamp(now - self.last_time, 0.001, 0.1)
        self.last_time = now
        self.fps = self.fps * 0.92 + (1.0 / dt) * 0.08
        self.frame += 1

        if not self.paused and not self.scrubbing and self.progress < 1.0:
            self.progress = min(1.0, self.progress + dt * self.speed / TOTAL_TIME)

        self.update_ship()
        self.step_camera(dt)
        self.draw_scene()

        if not self.scrubbing:
            self._slider_lock = True
            self.timeline.set(self.progress)
            self._slider_lock = False
        if self.frame % 4 == 0:
            self.update_panel(self.ship_pos, self.ship_tangent, self.travelled)

        elapsed_ms = int((time.perf_counter() - now) * 1000)
        self.root.after(max(1, 28 - elapsed_ms), self.animate)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        sys.stderr.write(f"No se pudo abrir la ventana (¿hay entorno gráfico / DISPLAY?): {error}\n")
        sys.exit(1)
    Solar3D(root)
    root.mainloop()


if __name__ == "__main__":
    main()