
import turtle
import math
import colorsys
import random


# ============================================================
# JAVA COFFEE — Animación con Python Turtle
# Humo animado y logotipo con colores cambiantes
# ============================================================

ANCHO = 900
ALTO = 700
FPS_MS = 40

screen = turtle.Screen()
screen.setup(ANCHO, ALTO)
screen.title("Java Coffee | Python Animation")
screen.bgcolor("#101722")
screen.tracer(0)

pen = turtle.Turtle()
pen.hideturtle()
pen.speed(0)
pen.penup()

turtle.colormode(255)

random.seed(7)

ESTRELLAS = [
    (
        random.randint(-430, 430),
        random.randint(-320, 320),
        random.choice([2, 2, 3, 4]),
    )
    for _ in range(65)
]

frame = 0


# ============================================================
# COLORES
# ============================================================

def color_hsv(hue, saturation=0.85, brightness=1.0):
    """Convierte HSV a RGB para animar los colores gradualmente."""
    rgb = colorsys.hsv_to_rgb(
        hue % 1.0,
        saturation,
        brightness,
    )

    return tuple(round(component * 255) for component in rgb)


def color_logo(desfase=0.0):
    """Color animado del logotipo."""
    hue = frame * 0.0015 + desfase
    return color_hsv(hue, 0.82, 1.0)


# ============================================================
# HERRAMIENTAS DE DIBUJO
# ============================================================

def dibujar_linea(puntos, color, grosor=3):
    if len(puntos) < 2:
        return

    pen.penup()
    pen.pencolor(color)
    pen.pensize(grosor)
    pen.goto(puntos[0])
    pen.pendown()

    for punto in puntos[1:]:
        pen.goto(punto)

    pen.penup()


def dibujar_poligono(puntos, relleno, borde=None, grosor=2):
    if borde is None:
        borde = relleno

    pen.penup()
    pen.pencolor(borde)
    pen.fillcolor(relleno)
    pen.pensize(grosor)
    pen.goto(puntos[0])
    pen.pendown()
    pen.begin_fill()

    for punto in puntos[1:]:
        pen.goto(punto)

    pen.goto(puntos[0])
    pen.end_fill()
    pen.penup()


def dibujar_elipse(cx, cy, rx, ry, relleno, borde=None):
    """Dibuja una elipse rellena a partir de puntos."""
    puntos = []

    for i in range(65):
        angulo = 2 * math.pi * i / 64

        x = cx + rx * math.cos(angulo)
        y = cy + ry * math.sin(angulo)

        puntos.append((x, y))

    dibujar_poligono(puntos, relleno, borde)


# ============================================================
# FONDO
# ============================================================

def dibujar_fondo():
    for x, y, tamano in ESTRELLAS:
        pen.goto(x, y)
        pen.dot(tamano, random.choice([
            "#35465A",
            "#62758A",
            "#B7C8D9",
        ]))

    pen.goto(0, 285)
    pen.color("#D8E2F0")
    pen.write(
        "A LITTLE CUP OF JAVA",
        align="center",
        font=("DejaVu Sans", 14, "bold"),
    )


# ============================================================
# HUMO ANIMADO
# ============================================================

def dibujar_humo():
    """Dibuja tres columnas de vapor con movimiento ondulante."""

    posiciones = [-24, 0, 24]

    for indice, origen_x in enumerate(posiciones):
        fase = frame * 0.055 + indice * 2.1
        amplitud = 10 + indice * 2

        puntos = []

        for paso in range(65):
            t = paso / 64

            # El humo asciende y oscila horizontalmente.
            x = origen_x + amplitud * math.sin(
                t * 2.8 * math.pi + fase
            ) * (0.25 + t)

            y = -48 + 128 * t

            # Pequeño desplazamiento adicional para dar fluidez.
            y += 2.5 * math.sin(fase + t * math.pi)

            puntos.append((x, y))

        color = color_logo(indice * 0.025)
        sombra = color_hsv(
            frame * 0.0015 + indice * 0.025,
            0.9,
            0.42,
        )

        # Sombra y línea luminosa del vapor.
        dibujar_linea(puntos, sombra, 7)
        dibujar_linea(puntos, color, 3)


# ============================================================
# TAZA DE CAFÉ
# ============================================================

def dibujar_taza():
    # Platillo, detrás de la taza.
    dibujar_elipse(
        0, -193, 125, 17,
        "#8294A8",
        "#C4D0DD",
    )

    dibujar_elipse(
        0, -190, 102, 9,
        "#344557",
        "#536579",
    )

    # Asa: la taza ocultará una parte de la elipse.
    puntos_asa = []

    for i in range(81):
        angulo = 2 * math.pi * i / 80

        x = 85 + 35 * math.cos(angulo)
        y = -118 + 43 * math.sin(angulo)

        puntos_asa.append((x, y))

    dibujar_linea(puntos_asa, "#A9B8CA", 12)
    dibujar_linea(puntos_asa, "#536A82", 5)

    # Cuerpo de la taza.
    cuerpo = [
        (-88, -57),
        (88, -57),
        (70, -181),
        (-70, -181),
    ]

    dibujar_poligono(
        cuerpo,
        "#E8EDF4",
        "#B7C8D9",
        3,
    )

    # Sombra lateral para dar volumen.
    dibujar_poligono(
        [
            (45, -61),
            (86, -61),
            (69, -178),
            (38, -178),
        ],
        "#C7D2E0",
        "#C7D2E0",
        1,
    )

    # Café visto desde arriba.
    dibujar_elipse(
        0, -58, 87, 12,
        "#4B2819",
        "#B0B9C5",
    )

    # Reflejo sutil sobre la bebida.
    pen.goto(-40, -55)
    pen.dot(5, "#B77B4E")

    # Símbolo J en la taza: también cambia de color.
    pen.goto(0, -135)
    pen.color(color_logo())
    pen.write(
        "J",
        align="center",
        font=("DejaVu Serif", 43, "bold"),
    )


# ============================================================
# LOGOTIPO Y TEXTO
# ============================================================

def dibujar_logo():
    # Palabra JAVA con color animado.
    pen.goto(0, -258)
    pen.color(color_logo(0.02))
    pen.write(
        "JAVA",
        align="center",
        font=("DejaVu Sans", 33, "bold"),
    )

    pen.goto(0, -288)
    pen.color("#94A8BD")
    pen.write(
        "CODE  •  COFFEE  •  REPEAT",
        align="center",
        font=("DejaVu Sans", 10, "normal"),
    )


# ============================================================
# ANIMACIÓN PRINCIPAL
# ============================================================

def animar():
    global frame

    pen.clear()

    dibujar_fondo()
    dibujar_humo()
    dibujar_taza()
    dibujar_logo()

    # Renderiza el fotograma completo.
    screen.update()

    frame += 1

    # Programa el siguiente fotograma sin bloquear la ventana.
    screen.ontimer(animar, FPS_MS)


# Iniciar animación.
animar()
screen.mainloop()
