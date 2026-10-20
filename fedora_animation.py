#!/usr/bin/env python3
"""
FEDORA LINUX — Animated Edition v2
Solo biblioteca estándar de Python (turtle + tkinter).

Controles
    Espacio   pausar / reanudar
    C         cambiar de paleta (Fedora, Violeta, Esmeralda, Ámbar)
    D         mostrar / ocultar FPS
    Esc / Q   salir
    Ratón     paralaje suave del emblema

Mejoras respecto a la v1
    * Los elementos se crean UNA vez y se mueven con coords()/itemconfig()
      sobre el canvas de Tk, en lugar de borrar y redibujar todo cada
      fotograma (mucho más fluido, ~60 FPS).
    * Animación basada en tiempo real (dt): la velocidad no depende de la CPU.
    * Corrige el bug de la v1: el círculo de relleno del halo tapaba el emblema.
    * Intro con escritura progresiva del título y aparición gradual.
    * Halo luminoso, arcos giratorios, cometa con estela, estrellas que
      titilan y estrellas fugaces ocasionales.
    * Paletas intercambiables en caliente, tipografía con respaldo y salida limpia.
"""

from __future__ import annotations

import colorsys
import math
import random
import time
import tkinter as tk
import turtle
from tkinter import font as tkfont

# ============================================================
# CONFIGURACIÓN
# ============================================================

W, H = 1000, 700
FRAME_MS = 16                 # ~60 FPS objetivo
CX, CY = -260, 45             # centro del emblema (coordenadas "matemáticas", y hacia arriba)
TITLE = "Fedora"

PALETTES = [("Fedora", 0.597), ("Violeta", 0.760), ("Esmeralda", 0.420), ("Ámbar", 0.075)]

RGB = tuple[int, int, int]


# ============================================================
# UTILIDADES
# ============================================================

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def hsv(h: float, s: float = 0.75, v: float = 1.0) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s), clamp(v))
    return round(r * 255), round(g * 255), round(b * 255)


def mix(a: RGB, b: RGB, k: float) -> RGB:
    k = clamp(k)
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b))  # type: ignore[return-value]


def hx(c: RGB) -> str:
    return "#%02x%02x%02x" % c


def ease_out(k: float) -> float:
    return 1 - (1 - clamp(k)) ** 3


def bezier(p0, p1, p2, p3, steps: int = 48) -> list[tuple[float, float]]:
    """Puntos de una curva Bézier cúbica."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append((
            u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
        ))
    return pts


def logo_paths() -> dict[str, list[tuple[float, float]]]:
    """Geometría del símbolo (coordenadas matemáticas)."""
    loop = [
        (CX + 69 * math.sin(2 * math.pi * i / 180), CY + 41 * math.sin(4 * math.pi * i / 180))
        for i in range(181)
    ]
    stem = [(CX - 24, CY - 62), (CX - 24, CY + 26)]
    arch = bezier((CX - 24, CY + 26), (CX - 24, CY + 64), (CX + 42, CY + 72), (CX + 40, CY + 36))
    return {
        "loop": loop,
        "f": stem + arch[1:],                       # tallo + arco en un solo trazo continuo
        "bar": [(CX - 66, CY + 1), (CX + 35, CY + 1)],
    }


# ============================================================
# ESCENA
# ============================================================

class Scene:
    def __init__(self, screen: turtle.TurtleScreen) -> None:
        self.screen = screen
        self.cv = screen.getcanvas()
        self.cv.winfo_toplevel().resizable(False, False)

        fams = set(tkfont.families(self.cv))
        self.font = next(
            (f for f in ("Comfortaa", "Montserrat", "Red Hat Display", "DejaVu Sans", "Helvetica")
             if f in fams),
            "TkDefaultFont",
        )

        # Estado
        self.running = True
        self.paused = False
        self.show_fps = False
        self.pal = 0
        self.t = 0.0
        self.last = time.perf_counter()
        self.ox = self.oy = 0.0            # desplazamiento actual (paralaje, coords canvas)
        self.tx = self.ty = 0.0            # desplazamiento objetivo
        self.fps_n, self.fps_t = 0, self.last
        self.meteor = {"life": 0.0, "wait": 2.0, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0}

        self.set_palette_colors(0)
        self.build_background()
        self.build_emblem()
        self.build_text()
        self.apply_palette()

        # Entradas
        screen.listen()
        screen.onkeypress(self.toggle_pause, "space")
        screen.onkeypress(self.next_palette, "c")
        screen.onkeypress(self.toggle_fps, "d")
        screen.onkeypress(self.quit, "Escape")
        screen.onkeypress(self.quit, "q")
        self.cv.bind("<Motion>", self.on_motion)

    # ------------------------------------------------------------------
    # Coordenadas
    # ------------------------------------------------------------------

    def pt(self, x: float, y: float) -> tuple[float, float]:
        """Matemáticas -> canvas, con el paralaje aplicado."""
        return x + self.ox, -y + self.oy

    def circ(self, item: int, cx: float, cy: float, r: float) -> None:
        self.cv.coords(item, cx - r, cy - r, cx + r, cy + r)

    def line(self, pts, color: RGB, width: float, tags=()) -> int:
        flat = [c for x, y in pts for c in (x, -y)]
        return self.cv.create_line(
            *flat, fill=hx(color), width=width,
            capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags,
        )

    # ------------------------------------------------------------------
    # Paletas
    # ------------------------------------------------------------------

    def set_palette_colors(self, idx: int) -> None:
        self.pal = idx % len(PALETTES)
        h = PALETTES[self.pal][1]
        self.h = h
        self.bg_top = hsv(h, 0.62, 0.20)
        self.bg_bot = hsv(h, 0.78, 0.07)
        self.bg_mid = mix(self.bg_top, self.bg_bot, 0.5)
        self.accent = hsv(h, 0.70, 1.0)
        self.bright = hsv(h, 0.25, 1.0)
        self.loop_c = hsv(h, 0.45, 1.0)
        self.rim_c = hsv(h, 0.85, 0.31)
        self.ring_c = hsv(h, 0.80, 0.54)
        self.disk_out = hsv(h, 0.78, 0.55)
        self.disk_in = hsv(h, 0.62, 0.80)
        self.text_cols = {
            "label": hsv(h, 0.42, 0.85),
            "desc1": hsv(h, 0.24, 0.80),
            "desc2": hsv(h, 0.38, 0.62),
            "foot": hsv(h, 0.47, 0.62),
        }

    def next_palette(self) -> None:
        self.set_palette_colors(self.pal + 1)
        self.apply_palette()

    def apply_palette(self) -> None:
        cv = self.cv
        self.screen.bgcolor(hx(self.bg_bot))
        self.screen.title(f"Fedora Linux | Python Edition — {PALETTES[self.pal][0]}")

        for i, item in enumerate(self.bands):
            cv.itemconfig(item, fill=hx(mix(self.bg_top, self.bg_bot, i / (len(self.bands) - 1))))
        for item in self.grid:
            cv.itemconfig(item, fill=hx(mix(self.bg_mid, self.accent, 0.07)))

        cv.itemconfig(self.rim, fill=hx(self.rim_c), outline=hx(self.ring_c))
        n = len(self.disk_layers)
        for i, item in enumerate(self.disk_layers):
            cv.itemconfig(item, fill=hx(mix(self.disk_out, self.disk_in, i / (n - 1))))
        cv.itemconfig(self.loop, fill=hx(self.loop_c))
        shadow = hx(mix(self.disk_out, (0, 0, 0), 0.55))
        for item in self.shadows:
            cv.itemconfig(item, fill=shadow)

        cv.itemconfig(self.divider, fill=hx(mix(self.bg_bot, self.accent, 0.22)))
        cv.itemconfig(self.foot_line, fill=hx(mix(self.bg_bot, self.accent, 0.14)))
        cv.itemconfig(self.title_shadow, fill=hx(mix(self.bg_bot, (0, 0, 0), 0.6)))

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def build_background(self) -> None:
        cv = self.cv
        n = 48
        step = (H + 40) / n
        self.bands = [
            cv.create_rectangle(
                -W / 2 - 20, -H / 2 - 20 + i * step, W / 2 + 20, -H / 2 - 20 + (i + 1) * step + 1,
                width=0,
            )
            for i in range(n)
        ]

        self.grid = []
        for x in range(-480, 481, 40):
            self.grid.append(cv.create_line(x, -H / 2, x, H / 2, width=1))
        for y in range(-320, 321, 40):
            self.grid.append(cv.create_line(-W / 2, y, W / 2, y, width=1))

        # Estrellas (con la zona del logotipo despejada)
        rng = random.Random(21)
        self.stars = []
        while len(self.stars) < 70:
            x, y = rng.randint(-480, 480), rng.randint(-330, 330)
            if CX - 190 < x < CX + 190 and CY - 190 < y < CY + 190:
                continue
            r = rng.choice((1, 1.5, 2))
            item = cv.create_oval(x - r, y - r, x + r, y + r, width=0)
            self.stars.append((item, rng.uniform(0, math.tau), rng.uniform(0.6, 2.2)))

        # Estrella fugaz (reutilizable)
        self.meteor_item = cv.create_line(0, 0, 0, 0, width=2, capstyle=tk.ROUND, state="hidden")

    def build_emblem(self) -> None:
        cv = self.cv

        # Halo (detrás de todo, se anima)
        self.glow = [cv.create_oval(0, 0, 0, 0, width=3) for _ in range(7)]

        # Aro y disco con degradado radial falso
        cx, cy = self.pt(CX, CY)
        self.rim = cv.create_oval(cx - 136, cy - 136, cx + 136, cy + 136, width=2, tags="emblem")
        self.disk_layers = []
        steps = 16
        for i in range(steps):
            r = 124 - i * (112 / (steps - 1))
            self.disk_layers.append(
                cv.create_oval(cx - r, cy - r, cx + r, cy + r, width=0, tags="emblem")
            )

        # Símbolo: sombra + figura
        paths = logo_paths()
        widths = {"loop": 17, "f": 19, "bar": 18}
        self.shadows = []
        for key in ("loop", "f", "bar"):
            shifted = [(x + 4, y - 4) for x, y in paths[key]]
            self.shadows.append(self.line(shifted, (0, 0, 0), widths[key], "emblem"))
        self.loop = self.line(paths["loop"], self.loop_c, widths["loop"], "emblem")
        self.line(paths["f"], (255, 255, 255), widths["f"], "emblem")
        self.line(paths["bar"], (255, 255, 255), widths["bar"], "emblem")

        # Anillo pulsante, arcos giratorios y cometa
        self.ring = cv.create_oval(0, 0, 0, 0, width=2)
        self.arcs = [
            # (item, radio extra, extensión, velocidad °/s, ancho, fase)
            (cv.create_arc(0, 0, 0, 0, style=tk.ARC, start=0, extent=70, width=3), 14, 40, 3, 0),
            (cv.create_arc(0, 0, 0, 0, style=tk.ARC, start=0, extent=40, width=2), 27, -65, 2, 120),
            (cv.create_arc(0, 0, 0, 0, style=tk.ARC, start=0, extent=25, width=2), 40, 90, 2, 240),
        ]
        self.trail = [cv.create_oval(0, 0, 0, 0, width=0) for _ in range(18)]
        self.partner = cv.create_oval(0, 0, 0, 0, width=0)

    def build_text(self) -> None:
        cv = self.cv
        f = self.font
        left = -65

        self.label = cv.create_text(left, -118, text="OPERATING SYSTEM", anchor="w",
                                    font=(f, 10, "bold"))
        self.divider = cv.create_line(left, -100, 360, -100, width=2)

        self.title_shadow = cv.create_text(left + 3, -52 + 3, text="", anchor="w",
                                           font=(f, 56, "bold"))
        self.title = cv.create_text(left, -52, text="", anchor="w", font=(f, 56, "bold"))

        self.ul_glow = cv.create_line(left, 0, left, 0, width=9, capstyle=tk.ROUND)
        self.ul = cv.create_line(left, 0, left, 0, width=3, capstyle=tk.ROUND)

        self.desc1 = cv.create_text(left, 32, text="COMMUNITY  /  OPEN SOURCE", anchor="w",
                                    font=(f, 11))
        self.desc2 = cv.create_text(left, 62, text="Built for developers and creators.", anchor="w",
                                    font=(f, 11))

        self.foot_line = cv.create_line(-450, 265, 450, 265, width=1)
        self.foot1 = cv.create_text(-445, 290, text="FEDORA PROJECT", anchor="w", font=(f, 9, "bold"))
        self.foot2 = cv.create_text(445, 290, text="LINUX  •  COMMUNITY  •  FREEDOM", anchor="e",
                                    font=(f, 9))
        self.hint = cv.create_text(445, 318, anchor="e", font=(f, 8),
                                   text="ESPACIO pausa · C paleta · D FPS · ESC salir")
        self.fps_item = cv.create_text(-480, -335, anchor="nw", font=(f, 9), text="", state="hidden")

        self.fades = [
            (self.label, "label"), (self.desc1, "desc1"), (self.desc2, "desc2"),
            (self.foot1, "foot"), (self.foot2, "foot"), (self.hint, "foot"), (self.fps_item, "foot"),
        ]

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def toggle_fps(self) -> None:
        self.show_fps = not self.show_fps
        self.cv.itemconfig(self.fps_item, state="normal" if self.show_fps else "hidden")

    def on_motion(self, e: tk.Event) -> None:
        w, h = self.screen.window_width(), self.screen.window_height()
        self.tx = clamp((e.x - w / 2) / (w / 2), -1, 1) * -12
        self.ty = clamp((e.y - h / 2) / (h / 2), -1, 1) * -8

    def quit(self) -> None:
        self.running = False
        try:
            self.screen.bye()
        except (tk.TclError, turtle.Terminator):
            pass

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------

    def tick(self) -> None:
        if not self.running:
            return
        try:
            now = time.perf_counter()
            dt = min(now - self.last, 0.1)
            self.last = now
            if not self.paused:
                self.t += dt
            self.update(dt, 0.0 if self.paused else dt)

            self.fps_n += 1
            if now - self.fps_t >= 0.5:
                if self.show_fps:
                    self.cv.itemconfig(self.fps_item, text=f"{self.fps_n / (now - self.fps_t):.0f} FPS")
                self.fps_n, self.fps_t = 0, now

            self.screen.ontimer(self.tick, FRAME_MS)
        except (tk.TclError, turtle.Terminator):
            self.running = False

    def update(self, real_dt: float, dt: float) -> None:
        cv, t = self.cv, self.t
        intro = ease_out((t - 0.1) / 1.0)

        # --- Paralaje suave del emblema ---
        a = min(1.0, real_dt * 6)
        nx, ny = self.ox + (self.tx - self.ox) * a, self.oy + (self.ty - self.oy) * a
        if nx != self.ox or ny != self.oy:
            cv.move("emblem", nx - self.ox, ny - self.oy)
            self.ox, self.oy = nx, ny
        cx, cy = self.pt(CX, CY)

        # --- Estrellas ---
        for item, phase, speed in self.stars:
            k = 0.30 + 0.70 * (0.5 + 0.5 * math.sin(t * speed + phase))
            cv.itemconfig(item, fill=hx(mix(self.bg_mid, self.bright, k * 0.55)))

        self.update_meteor(dt)

        # --- Halo y anillo pulsante ---
        pulse = 0.5 + 0.5 * math.sin(t * 1.6)
        R = 147 + 3 * pulse
        hue = self.h + 0.018 * math.sin(t * 0.6)
        accent = hsv(hue, 0.70, 1.0)

        n = len(self.glow)
        for k, item in enumerate(self.glow):
            strength = (1 - k / n) ** 2 * 0.42 * intro * (0.75 + 0.25 * pulse)
            self.circ(item, cx, cy, R + 4 + k * 6)
            cv.itemconfig(item, outline=hx(mix(self.bg_mid, accent, strength)))

        self.circ(self.ring, cx, cy, R)
        cv.itemconfig(self.ring, outline=hx(mix(self.bg_mid, accent, intro)))

        # --- Arcos giratorios ---
        for item, extra, speed, width, phase in self.arcs:
            self.circ(item, cx, cy, R + extra)
            cv.itemconfig(item, start=(phase + speed * t) % 360,
                          outline=hx(mix(self.bg_mid, accent, 0.55 * intro)))

        # --- Cometa con estela ---
        head = t * 1.8
        n = len(self.trail)
        for i, item in enumerate(self.trail):
            ang = head - i * 0.055
            k = 1 - i / n
            r = 1.5 + 6.5 * k
            x, y = cx + R * math.cos(ang), cy - R * math.sin(ang)
            cv.coords(item, x - r, y - r, x + r, y + r)
            col = self.bright if i == 0 else mix(self.bg_mid, accent, k ** 1.4)
            cv.itemconfig(item, fill=hx(mix(self.bg_mid, col, intro)))

        ang = math.pi - head * 0.6
        x, y = cx + R * math.cos(ang), cy - R * math.sin(ang)
        cv.coords(self.partner, x - 3, y - 3, x + 3, y + 3)
        cv.itemconfig(self.partner, fill=hx(mix(self.bg_mid, accent, 0.8 * intro)))

        # --- Título: escritura progresiva y deriva de color ---
        shown = 0 if t < 0.35 else min(len(TITLE), int((t - 0.35) / 0.16) + 1)
        text = TITLE[:shown]
        cv.itemconfig(self.title, text=text, fill=hx(hsv(self.h + 0.025 * math.sin(t * 0.9), 0.40, 1.0)))
        cv.itemconfig(self.title_shadow, text=text)

        # --- Subrayado que respira ---
        k_ul = ease_out((t - 1.3) / 0.8)
        length = (40 + (0.5 + 0.5 * math.sin(t * 1.9)) * 310) * k_ul
        cv.coords(self.ul_glow, -65, 0, -65 + length, 0)
        cv.coords(self.ul, -65, 0, -65 + length, 0)
        cv.itemconfig(self.ul_glow, fill=hx(mix(self.bg_mid, accent, 0.28)))
        cv.itemconfig(self.ul, fill=hx(accent))

        # --- Textos secundarios (aparición gradual) ---
        k_txt = ease_out((t - 0.9) / 1.0)
        for item, key in self.fades:
            cv.itemconfig(item, fill=hx(mix(self.bg_mid, self.text_cols[key], k_txt)))

    def update_meteor(self, dt: float) -> None:
        m, cv = self.meteor, self.cv
        if m["life"] <= 0:
            m["wait"] -= dt
            if m["wait"] <= 0:
                ang = math.radians(random.uniform(20, 40))
                m.update(
                    x=random.uniform(-450, 150), y=random.uniform(-330, -140),
                    vx=math.cos(ang) * 750, vy=math.sin(ang) * 750, life=0.7,
                )
            return
        m["life"] -= dt
        m["x"] += m["vx"] * dt
        m["y"] += m["vy"] * dt
        if m["life"] <= 0:
            cv.itemconfig(self.meteor_item, state="hidden")
            m["wait"] = random.uniform(3, 7)
            return
        cv.coords(self.meteor_item, m["x"], m["y"], m["x"] - m["vx"] * 0.09, m["y"] - m["vy"] * 0.09)
        cv.itemconfig(self.meteor_item, state="normal",
                      fill=hx(mix(self.bg_mid, self.bright, m["life"] / 0.7)))


# ============================================================
# INICIO
# ============================================================

def main() -> None:
    screen = turtle.Screen()
    screen.setup(W, H)
    scene = Scene(screen)
    scene.tick()
    try:
        screen.mainloop()
    except (tk.TclError, turtle.Terminator):
        pass


if __name__ == "__main__":
    main()