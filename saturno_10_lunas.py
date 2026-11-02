#!/usr/bin/env python3
"""Saturn System Simulator: Saturn + 10 moons, 2D Newtonian N-body model.

Only Python's standard library is used: math, dataclasses, collections and tkinter.
The orbital elements are approximate mean elements, flattened into a common 2D plane.
This is an educational model, not a precision ephemeris.
"""

from __future__ import annotations

import math
import random
import tkinter as tk
from collections import deque
from dataclasses import dataclass, field
from tkinter import ttk


# -----------------------------------------------------------------------------
# CONSTANTES FISICAS (SI: kg, m, s)
# -----------------------------------------------------------------------------

G = 6.67430e-11                 # Constante de gravitación universal [m^3 kg^-1 s^-2]
MASA_SATURNO = 5.6834e26       # Masa de Saturno [kg]
RADIO_SATURNO_KM = 58_232      # Radio medio aproximado [km]
DT = 120.0                     # Paso de integración [s]
PASOS_BASE = 4                 # Subpasos por fotograma a velocidad 1x
SUAVIZADO = 1_000.0            # Suavizado numérico muy pequeño [m]
MAX_DISTANCIA_KM = 15_500_000  # Cubre aproximadamente el apoapsis de Phoebe
REFERENCIA_LOG_KM = 150_000    # Escala característica de la vista logarítmica


@dataclass
class Luna:
    """Cuerpo celeste con estado dinámico y elementos orbitales aproximados."""

    nombre: str
    masa: float
    radio_km: float
    color: str
    a_km: float
    excentricidad: float
    periapsis_deg: float
    anomalia_media_deg: float
    inclinacion_deg: float
    nodo_deg: float
    periodo_dias: float
    posicion: list[float] = field(default_factory=lambda: [0.0, 0.0])
    velocidad: list[float] = field(default_factory=lambda: [0.0, 0.0])
    estela: deque = field(default_factory=lambda: deque(maxlen=360))

    @property
    def sentido(self) -> float:
        # En el modelo plano, inclinación > 90° representa movimiento retrógrado.
        return -1.0 if self.inclinacion_deg > 90.0 else 1.0


@dataclass
class Cuerpo:
    """Representa a Saturno o una luna dentro del integrador N-body."""

    nombre: str
    masa: float
    posicion: list[float]
    velocidad: list[float]


# Datos orbitales aproximados: a [km], e, argumento del periapsis [°],
# anomalía media [°], inclinación [°], nodo ascendente [°], período [días].
# Masas y radios son valores redondeados para un modelo educativo.
DATOS_LUNAS = [
    {
        "nombre": "Janus", "masa": 1.90e18, "radio": 89.2, "a": 151_500,
        "e": 0.007, "w": 11.1, "M": 111.7, "i": 0.2, "nodo": 159.9,
        "periodo": 0.697353, "color": "#c6a77b",
    },
    {
        "nombre": "Mimas", "masa": 3.79e19, "radio": 198.2, "a": 186_000,
        "e": 0.020, "w": 160.4, "M": 275.3, "i": 1.6, "nodo": 66.2,
        "periodo": 0.942422, "color": "#b7c4d8",
    },
    {
        "nombre": "Enceladus", "masa": 1.08e20, "radio": 252.1, "a": 238_400,
        "e": 0.005, "w": 119.5, "M": 57.0, "i": 0.0, "nodo": 0.0,
        "periodo": 1.370218, "color": "#e7f0f4",
    },
    {
        "nombre": "Tethys", "masa": 6.18e20, "radio": 531.1, "a": 295_000,
        "e": 0.001, "w": 335.3, "M": 0.0, "i": 1.1, "nodo": 273.0,
        "periodo": 1.887802, "color": "#91b8c9",
    },
    {
        "nombre": "Dione", "masa": 1.10e21, "radio": 561.4, "a": 377_700,
        "e": 0.002, "w": 116.0, "M": 212.0, "i": 0.0, "nodo": 0.0,
        "periodo": 2.736916, "color": "#b9c5d2",
    },
    {
        "nombre": "Rhea", "masa": 2.31e21, "radio": 763.5, "a": 527_200,
        "e": 0.001, "w": 44.3, "M": 31.5, "i": 0.3, "nodo": 133.7,
        "periodo": 4.517503, "color": "#d5c3a5",
    },
    {
        "nombre": "Titan", "masa": 1.3455e23, "radio": 2_574.76, "a": 1_221_900,
        "e": 0.029, "w": 78.3, "M": 11.7, "i": 0.3, "nodo": 78.6,
        "periodo": 15.945448, "color": "#e6a04d",
    },
    {
        "nombre": "Hyperion", "masa": 5.60e18, "radio": 135.0, "a": 1_481_500,
        "e": 0.105, "w": 214.0, "M": 122.9, "i": 0.6, "nodo": 87.1,
        "periodo": 21.276658, "color": "#bd8c72",
    },
    {
        "nombre": "Iapetus", "masa": 1.81e21, "radio": 734.3, "a": 3_561_700,
        "e": 0.028, "w": 254.5, "M": 74.8, "i": 7.6, "nodo": 86.5,
        "periodo": 79.331002, "color": "#9b9da7",
    },
    {
        "nombre": "Phoebe", "masa": 8.30e18, "radio": 106.5, "a": 12_929_400,
        "e": 0.164, "w": 240.3, "M": 308.0, "i": 175.2, "nodo": 192.7,
        "periodo": 550.303910, "color": "#a78bbd",
    },
]


def resolver_kepler(anomalia_media: float, excentricidad: float) -> float:
    """Resuelve E - e sen(E) = M mediante Newton-Raphson."""
    anomalia_e = anomalia_media

    for _ in range(30):
        f = anomalia_e - excentricidad * math.sin(anomalia_e) - anomalia_media
        derivada = 1.0 - excentricidad * math.cos(anomalia_e)
        correccion = f / derivada
        anomalia_e -= correccion
        if abs(correccion) < 1e-13:
            break

    return anomalia_e


def estado_orbital_inicial(datos: dict) -> tuple[list[float], list[float]]:
    """Convierte elementos orbitales en vectores de posición y velocidad 2D."""
    a = datos["a"] * 1_000.0
    e = datos["e"]
    masa_luna = datos["masa"]
    anomalia_media = math.radians(datos["M"])
    anomalia_e = resolver_kepler(anomalia_media, e)

    cos_e = math.cos(anomalia_e)
    sin_e = math.sin(anomalia_e)
    factor = 1.0 - e * cos_e

    # Coordenadas y velocidades en el plano orbital (marco perifocal).
    x = a * (cos_e - e)
    y = a * math.sqrt(1.0 - e * e) * sin_e

    mu = G * (MASA_SATURNO + masa_luna)
    movimiento_medio = math.sqrt(mu / (a ** 3))
    vx = -a * movimiento_medio * sin_e / factor
    vy = a * movimiento_medio * math.sqrt(1.0 - e * e) * cos_e / factor

    # Aplanamos las inclinaciones. Phoebe conserva el sentido retrógrado.
    if datos["i"] > 90.0:
        y = -y
        vy = -vy

    angulo = math.radians(datos["w"] + datos["nodo"])
    cos_a = math.cos(angulo)
    sin_a = math.sin(angulo)

    posicion = [x * cos_a - y * sin_a, x * sin_a + y * cos_a]
    velocidad = [vx * cos_a - vy * sin_a, vx * sin_a + vy * cos_a]

    return posicion, velocidad


class SistemaSaturno:
    """Integrador gravitacional de Saturno y sus diez lunas."""

    def __init__(self) -> None:
        self.saturno = Cuerpo(
            "Saturno", MASA_SATURNO, [0.0, 0.0], [0.0, 0.0]
        )
        self.lunas: list[Luna] = []
        self.cuerpos: list[Cuerpo] = []
        self.reiniciar()

    def reiniciar(self) -> None:
        self.lunas = []

        for datos in DATOS_LUNAS:
            posicion, velocidad = estado_orbital_inicial(datos)
            luna = Luna(
                nombre=datos["nombre"],
                masa=datos["masa"],
                radio_km=datos["radio"],
                color=datos["color"],
                a_km=datos["a"],
                excentricidad=datos["e"],
                periapsis_deg=datos["w"],
                anomalia_media_deg=datos["M"],
                inclinacion_deg=datos["i"],
                nodo_deg=datos["nodo"],
                periodo_dias=datos["periodo"],
                posicion=posicion,
                velocidad=velocidad,
            )
            self.lunas.append(luna)

        self.saturno = Cuerpo(
            "Saturno", MASA_SATURNO, [0.0, 0.0], [0.0, 0.0]
        )
        self.cuerpos = [self.saturno] + [
            Cuerpo(l.nombre, l.masa, l.posicion, l.velocidad) for l in self.lunas
        ]

        # Trasladar todo al centro de masa y al marco de reposo del baricentro.
        masa_total = sum(c.masa for c in self.cuerpos)
        centro_x = sum(c.masa * c.posicion[0] for c in self.cuerpos) / masa_total
        centro_y = sum(c.masa * c.posicion[1] for c in self.cuerpos) / masa_total
        velocidad_x = sum(c.masa * c.velocidad[0] for c in self.cuerpos) / masa_total
        velocidad_y = sum(c.masa * c.velocidad[1] for c in self.cuerpos) / masa_total

        for cuerpo in self.cuerpos:
            cuerpo.posicion[0] -= centro_x
            cuerpo.posicion[1] -= centro_y
            cuerpo.velocidad[0] -= velocidad_x
            cuerpo.velocidad[1] -= velocidad_y

        self.saturno = self.cuerpos[0]
        for indice, luna in enumerate(self.lunas, start=1):
            luna.posicion = self.cuerpos[indice].posicion
            luna.velocidad = self.cuerpos[indice].velocidad
            luna.estela.clear()

    def calcular_aceleraciones(self, posiciones: list[list[float]]) -> list[list[float]]:
        """Calcula todas las aceleraciones usando pares de vectores acción-reacción."""
        n = len(self.cuerpos)
        aceleraciones = [[0.0, 0.0] for _ in range(n)]
        masas = [c.masa for c in self.cuerpos]

        for i in range(n - 1):
            for j in range(i + 1, n):
                dx = posiciones[j][0] - posiciones[i][0]
                dy = posiciones[j][1] - posiciones[i][1]
                distancia2 = dx * dx + dy * dy + SUAVIZADO * SUAVIZADO
                inversa_r3 = 1.0 / (distancia2 * math.sqrt(distancia2))
                factor = G * inversa_r3

                # Aceleración de i hacia j y de j hacia i.
                aceleraciones[i][0] += factor * masas[j] * dx
                aceleraciones[i][1] += factor * masas[j] * dy
                aceleraciones[j][0] -= factor * masas[i] * dx
                aceleraciones[j][1] -= factor * masas[i] * dy

        return aceleraciones

    def paso(self, dt: float = DT) -> None:
        """Integra un paso mediante Velocity Verlet (posición y velocidad vectorial)."""
        posiciones = [c.posicion for c in self.cuerpos]
        velocidades = [c.velocidad for c in self.cuerpos]
        aceleraciones_0 = self.calcular_aceleraciones(posiciones)
        dt2 = dt * dt

        nuevas_posiciones = []
        for r, v, a in zip(posiciones, velocidades, aceleraciones_0):
            nuevas_posiciones.append([
                r[0] + v[0] * dt + 0.5 * a[0] * dt2,
                r[1] + v[1] * dt + 0.5 * a[1] * dt2,
            ])

        aceleraciones_1 = self.calcular_aceleraciones(nuevas_posiciones)

        for indice, cuerpo in enumerate(self.cuerpos):
            cuerpo.velocidad[0] += 0.5 * (
                aceleraciones_0[indice][0] + aceleraciones_1[indice][0]
            ) * dt
            cuerpo.velocidad[1] += 0.5 * (
                aceleraciones_0[indice][1] + aceleraciones_1[indice][1]
            ) * dt
            cuerpo.posicion[0] = nuevas_posiciones[indice][0]
            cuerpo.posicion[1] = nuevas_posiciones[indice][1]


class AplicacionSaturno:
    """Interfaz gráfica sencilla construida con Tkinter."""

    FONDO = "#070b14"
    PANEL = "#0d1422"
    TEXTO = "#e6edf7"
    TEXTO_SECUNDARIO = "#94a3b8"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Saturn System Simulator | Python N-Body")
        self.root.geometry("1280x820")
        self.root.minsize(980, 650)
        self.root.configure(bg=self.FONDO)

        self.sistema = SistemaSaturno()
        self.tiempo_simulado = 0.0
        self.ejecutando = True
        self.escala_logaritmica = True
        self.mostrar_estelas = True
        self.fotograma = 0
        self.velocidad = tk.IntVar(value=2)
        self.estrellas = self.crear_estrellas(180)

        self.crear_interfaz()
        self.root.bind("<space>", self.alternar_ejecucion)
        self.root.after(100, self.bucle)

    def crear_estrellas(self, cantidad: int) -> list[tuple[float, float, int]]:
        generador = random.Random(42)
        return [
            (generador.random(), generador.random(), generador.choice((1, 1, 1, 2)))
            for _ in range(cantidad)
        ]

    def crear_boton(self, padre, texto: str, comando):
        return tk.Button(
            padre,
            text=texto,
            command=comando,
            bg="#1b2a40",
            fg=self.TEXTO,
            activebackground="#29415f",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=11,
            pady=7,
            font=("TkDefaultFont", 9, "bold"),
            cursor="hand2",
        )

    def crear_interfaz(self) -> None:
        encabezado = tk.Frame(self.root, bg=self.PANEL, padx=15, pady=11)
        encabezado.pack(side="top", fill="x")

        titulo = tk.Label(
            encabezado,
            text="SATURN SYSTEM  /  N-BODY SIMULATOR",
            bg=self.PANEL,
            fg=self.TEXTO,
            font=("TkDefaultFont", 14, "bold"),
        )
        titulo.pack(side="left", padx=(0, 18))

        self.boton_pausa = self.crear_boton(encabezado, "Pausar", self.alternar_ejecucion)
        self.boton_pausa.pack(side="left", padx=3)
        self.crear_boton(encabezado, "Reiniciar", self.reiniciar).pack(side="left", padx=3)
        self.boton_escala = self.crear_boton(
            encabezado, "Escala: logarítmica", self.alternar_escala
        )
        self.boton_escala.pack(side="left", padx=3)
        self.boton_estelas = self.crear_boton(
            encabezado, "Estelas: ON", self.alternar_estelas
        )
        self.boton_estelas.pack(side="left", padx=3)

        velocidad_frame = tk.Frame(encabezado, bg=self.PANEL)
        velocidad_frame.pack(side="right", padx=(10, 0))
        tk.Label(
            velocidad_frame, text="VELOCIDAD", bg=self.PANEL, fg=self.TEXTO_SECUNDARIO,
            font=("TkDefaultFont", 8, "bold")
        ).pack(side="left", padx=(0, 6))
        tk.Scale(
            velocidad_frame,
            from_=1,
            to=8,
            orient="horizontal",
            variable=self.velocidad,
            length=125,
            showvalue=True,
            bg=self.PANEL,
            fg=self.TEXTO,
            troughcolor="#26364d",
            highlightthickness=0,
            bd=0,
            activebackground="#6da8d9",
        ).pack(side="left")

        contenido = tk.Frame(self.root, bg=self.FONDO)
        contenido.pack(fill="both", expand=True, padx=12, pady=12)

        self.canvas = tk.Canvas(
            contenido, bg=self.FONDO, highlightthickness=1,
            highlightbackground="#1c293b"
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        lateral = tk.Frame(contenido, bg=self.PANEL, width=255, padx=13, pady=13)
        lateral.pack(side="right", fill="y", padx=(10, 0))
        lateral.pack_propagate(False)

        tk.Label(
            lateral, text="CUERPOS ORBITALES", bg=self.PANEL, fg=self.TEXTO,
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w", pady=(0, 8))

        for luna in self.sistema.lunas:
            fila = tk.Frame(lateral, bg=self.PANEL)
            fila.pack(fill="x", pady=4)
            tk.Label(
                fila, text="●", fg=luna.color, bg=self.PANEL,
                font=("TkDefaultFont", 12)
            ).pack(side="left", padx=(0, 7))
            texto = (
                f"{luna.nombre}\n"
                f"a = {luna.a_km:,.0f} km  |  P = {luna.periodo_dias:g} d"
            )
            tk.Label(
                fila, text=texto, justify="left", anchor="w", bg=self.PANEL,
                fg=self.TEXTO_SECUNDARIO, font=("TkDefaultFont", 8)
            ).pack(side="left", fill="x")

        ttk.Separator(lateral, orient="horizontal").pack(fill="x", pady=12)
        tk.Label(
            lateral, text="MODELO FÍSICO", bg=self.PANEL, fg=self.TEXTO,
            font=("TkDefaultFont", 9, "bold")
        ).pack(anchor="w", pady=(0, 5))
        descripcion = (
            "• Gravedad newtoniana\n"
            "• 11 cuerpos interactuando\n"
            "• Integrador Velocity Verlet\n"
            "• Vectores x, y en SI\n"
            "• Baricentro conservado\n"
            "• Phoebe retrógrada"
        )
        tk.Label(
            lateral, text=descripcion, justify="left", anchor="w", bg=self.PANEL,
            fg=self.TEXTO_SECUNDARIO, font=("TkDefaultFont", 8)
        ).pack(anchor="w")

        self.etiqueta_tiempo = tk.Label(
            lateral, text="Tiempo simulado: 0.00 días", bg=self.PANEL,
            fg="#8cc8f2", font=("TkDefaultFont", 9, "bold")
        )
        self.etiqueta_tiempo.pack(side="bottom", anchor="w", pady=(10, 0))

        pie = tk.Label(
            self.root,
            text=(
                "MODELO 2D  |  Escala logarítmica = distancias deformadas; usa escala lineal para proporciones.  "
                "Se omiten el Sol, el achatamiento J₂ y la gravedad de los anillos."
            ),
            bg=self.FONDO,
            fg=self.TEXTO_SECUNDARIO,
            font=("TkDefaultFont", 8),
            pady=5,
        )
        pie.pack(side="bottom", fill="x")

    def alternar_ejecucion(self, _evento=None) -> None:
        self.ejecutando = not self.ejecutando
        self.boton_pausa.configure(text="Pausar" if self.ejecutando else "Continuar")

    def alternar_escala(self) -> None:
        self.escala_logaritmica = not self.escala_logaritmica
        modo = "logarítmica" if self.escala_logaritmica else "lineal"
        self.boton_escala.configure(text=f"Escala: {modo}")
        self.dibujar_escena()

    def alternar_estelas(self) -> None:
        self.mostrar_estelas = not self.mostrar_estelas
        self.boton_estelas.configure(
            text=f"Estelas: {'ON' if self.mostrar_estelas else 'OFF'}"
        )
        self.dibujar_escena()

    def reiniciar(self) -> None:
        self.sistema.reiniciar()
        self.tiempo_simulado = 0.0
        self.fotograma = 0
        self.dibujar_escena()

    def avanzar(self) -> None:
        cantidad_pasos = PASOS_BASE * self.velocidad.get()
        for _ in range(cantidad_pasos):
            self.sistema.paso(DT)
            self.tiempo_simulado += DT

        self.fotograma += 1
        if self.fotograma % 2 == 0:
            saturno = self.sistema.saturno
            for luna in self.sistema.lunas:
                luna.estela.append((
                    luna.posicion[0] - saturno.posicion[0],
                    luna.posicion[1] - saturno.posicion[1],
                ))

    def bucle(self) -> None:
        if self.ejecutando:
            self.avanzar()
        self.dibujar_escena()
        dias = self.tiempo_simulado / 86_400.0
        self.etiqueta_tiempo.configure(text=f"Tiempo simulado: {dias:,.2f} días")
        self.root.after(33, self.bucle)

    def radio_en_pantalla(self, distancia_km: float, radio_max_px: float) -> float:
        distancia_km = max(0.0, distancia_km)
        if self.escala_logaritmica:
            numerador = math.log1p(distancia_km / REFERENCIA_LOG_KM)
            denominador = math.log1p(MAX_DISTANCIA_KM / REFERENCIA_LOG_KM)
            return radio_max_px * numerador / denominador
        return radio_max_px * distancia_km / MAX_DISTANCIA_KM

    def coordenada_pantalla(
        self, x_m: float, y_m: float, cx: float, cy: float, radio_max_px: float
    ) -> tuple[float, float]:
        x_km = x_m / 1_000.0
        y_km = y_m / 1_000.0
        distancia = math.hypot(x_km, y_km)
        if distancia == 0.0:
            return cx, cy
        radio_px = self.radio_en_pantalla(distancia, radio_max_px)
        return (
            cx + radio_px * x_km / distancia,
            cy - radio_px * y_km / distancia,
        )

    def dibujar_estrellas(self, ancho: int, alto: int) -> None:
        for x, y, tamano in self.estrellas:
            px = x * ancho
            py = y * alto
            self.canvas.create_oval(
                px, py, px + tamano, py + tamano,
                fill="#52647e", outline=""
            )

    def dibujar_orbitas(self, cx: float, cy: float, radio_max_px: float) -> None:
        for luna in self.sistema.lunas:
            a = luna.a_km * 1_000.0
            e = luna.excentricidad
            angulo_periapsis = math.radians(luna.periapsis_deg + luna.nodo_deg)
            puntos = []

            for indice in range(181):
                nu = 2.0 * math.pi * indice / 180.0
                radio = a * (1.0 - e * e) / (1.0 + e * math.cos(nu))
                angulo = angulo_periapsis + luna.sentido * nu
                x = radio * math.cos(angulo)
                y = radio * math.sin(angulo)
                px, py = self.coordenada_pantalla(x, y, cx, cy, radio_max_px)
                puntos.extend((px, py))

            self.canvas.create_line(
                *puntos, fill=luna.color, width=1, dash=(2, 5), smooth=False
            )

    def dibujar_anillos_y_planeta(
        self, cx: float, cy: float, radio_max_px: float
    ) -> None:
        radio_planeta = max(
            10.0, self.radio_en_pantalla(RADIO_SATURNO_KM, radio_max_px)
        )
        radio_anillo_exterior = max(
            radio_planeta * 1.75, self.radio_en_pantalla(140_000, radio_max_px)
        )
        radio_anillo_interior = max(
            radio_planeta * 1.35, self.radio_en_pantalla(74_000, radio_max_px)
        )

        # Anillos esquemáticos: no participan en el cálculo gravitacional.
        self.canvas.create_oval(
            cx - radio_anillo_exterior,
            cy - radio_anillo_exterior * 0.34,
            cx + radio_anillo_exterior,
            cy + radio_anillo_exterior * 0.34,
            outline="#a88e69", width=5,
        )
        self.canvas.create_oval(
            cx - radio_anillo_interior,
            cy - radio_anillo_interior * 0.34,
            cx + radio_anillo_interior,
            cy + radio_anillo_interior * 0.34,
            outline="#d2b58c", width=3,
        )

        self.canvas.create_oval(
            cx - radio_planeta, cy - radio_planeta,
            cx + radio_planeta, cy + radio_planeta,
            fill="#d8b77c", outline="#f3d8a7", width=1,
        )
        self.canvas.create_arc(
            cx - radio_planeta * 0.9, cy - radio_planeta * 0.6,
            cx + radio_planeta * 0.9, cy + radio_planeta * 0.6,
            start=190, extent=160, style="arc", outline="#9e7951", width=2,
        )
        self.canvas.create_text(
            cx, cy - radio_planeta - 12, text="SATURNO",
            fill="#e9d3ad", font=("TkDefaultFont", 8, "bold")
        )

    def dibujar_lunas(self, cx: float, cy: float, radio_max_px: float) -> None:
        saturno = self.sistema.saturno

        for indice, luna in enumerate(self.sistema.lunas):
            dx = luna.posicion[0] - saturno.posicion[0]
            dy = luna.posicion[1] - saturno.posicion[1]
            x, y = self.coordenada_pantalla(dx, dy, cx, cy, radio_max_px)

            if self.mostrar_estelas and len(luna.estela) > 2:
                puntos = []
                for tx, ty in luna.estela:
                    px, py = self.coordenada_pantalla(tx, ty, cx, cy, radio_max_px)
                    puntos.extend((px, py))
                self.canvas.create_line(
                    *puntos, fill=luna.color, width=2, smooth=True
                )

            tamano = 3.5 + min(2.0, 0.55 * math.log10(max(luna.radio_km, 1.0)))
            self.canvas.create_oval(
                x - tamano, y - tamano, x + tamano, y + tamano,
                fill=luna.color, outline="#f1f5f9", width=1,
            )

            # Etiquetas pequeñas, alternadas para reducir solapamientos.
            desplazamiento_y = -10 if indice % 2 == 0 else 10
            self.canvas.create_text(
                x + 8, y + desplazamiento_y, text=luna.nombre,
                anchor="w", fill="#d7e0ed", font=("TkDefaultFont", 8)
            )

    def dibujar_escena(self) -> None:
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("all")
        ancho = max(self.canvas.winfo_width(), 2)
        alto = max(self.canvas.winfo_height(), 2)
        cx = ancho / 2.0
        cy = alto / 2.0
        radio_max_px = min(ancho, alto) * 0.45

        self.dibujar_estrellas(ancho, alto)
        self.dibujar_orbitas(cx, cy, radio_max_px)
        self.dibujar_anillos_y_planeta(cx, cy, radio_max_px)
        self.dibujar_lunas(cx, cy, radio_max_px)

        modo = "RADIAL LOGARÍTMICA" if self.escala_logaritmica else "RADIAL LINEAL"
        self.canvas.create_text(
            14, 14, anchor="nw", text=modo,
            fill="#94a3b8", font=("TkDefaultFont", 8, "bold")
        )


def main() -> None:
    ventana = tk.Tk()
    AplicacionSaturno(ventana)
    ventana.mainloop()


if __name__ == "__main__":
    main()
