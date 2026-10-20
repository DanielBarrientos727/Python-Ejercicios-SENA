
import math
import random
import turtle


# ============================================================
# GIRASOL DIGITAL — "TE QUIERO"
# Python + Turtle
# ============================================================

random.seed(12)

# ---------------------- CONFIGURACIÓN ------------------------

ANCHO = 1000
ALTO = 800

CENTRO_X = 0
CENTRO_Y = 90

COLOR_FONDO = "#071321"
COLOR_TALLO = "#246B38"
COLOR_TALLO_LUZ = "#66A65C"
COLOR_HOJA = "#287A43"
COLOR_HOJA_BORDE = "#164E32"

screen = turtle.Screen()
screen.setup(ANCHO, ALTO)
screen.title("Un girasol para ti")
screen.bgcolor(COLOR_FONDO)
screen.tracer(0)

lapiz = turtle.Turtle()
lapiz.hideturtle()
lapiz.speed(0)
lapiz.penup()


# ---------------------- UTILIDADES ---------------------------

def transformar(puntos, centro, angulo, sx=1.0, sy=1.0):
    """Rota y escala puntos locales para ubicarlos en la pantalla."""
    rad = math.radians(angulo)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    cx, cy = centro
    resultado = []

    for x, y in puntos:
        x *= sx
        y *= sy

        px = cx + x * cos_a - y * sin_a
        py = cy + x * sin_a + y * cos_a

        resultado.append((px, py))

    return resultado


def dibujar_poligono(puntos, relleno, borde=None):
    """Dibuja un polígono relleno a partir de sus coordenadas."""
    if not puntos:
        return

    if borde is None:
        borde = relleno

    lapiz.penup()
    lapiz.color(borde, relleno)
    lapiz.goto(puntos[0])
    lapiz.pendown()

    lapiz.begin_fill()

    for punto in puntos[1:]:
        lapiz.goto(punto)

    lapiz.goto(puntos[0])
    lapiz.end_fill()
    lapiz.penup()


def dibujar_linea(inicio, fin, color, grosor=2):
    """Dibuja una línea entre dos puntos."""
    lapiz.penup()
    lapiz.color(color)
    lapiz.pensize(grosor)
    lapiz.goto(inicio)
    lapiz.pendown()
    lapiz.goto(fin)
    lapiz.penup()


def dibujar_estrellas(cantidad=110):
    """Crea un cielo nocturno con pequeñas estrellas."""
    colores = [
        "#FFFFFF",
        "#BFDFFF",
        "#FFE6A3",
        "#8DAFD1",
    ]

    for _ in range(cantidad):
        x = random.randint(-480, 480)
        y = random.randint(-365, 370)
        tamano = random.choice([2, 2, 3, 4])

        lapiz.goto(x, y)
        lapiz.dot(tamano, random.choice(colores))


def dibujar_destello(x, y, tamano, color):
    """Dibuja una estrella decorativa de cuatro puntas."""
    puntos = [
        (x, y + tamano),
        (x + tamano * 0.22, y + tamano * 0.22),
        (x + tamano, y),
        (x + tamano * 0.22, y - tamano * 0.22),
        (x, y - tamano),
        (x - tamano * 0.22, y - tamano * 0.22),
        (x - tamano, y),
        (x - tamano * 0.22, y + tamano * 0.22),
    ]

    dibujar_poligono(puntos, color)


# ---------------------- TALLO Y HOJAS ------------------------

def dibujar_tallo():
    """Dibuja un tallo verde con un pequeño reflejo de luz."""
    dibujar_linea(
        (CENTRO_X, -335),
        (CENTRO_X, CENTRO_Y - 25),
        COLOR_TALLO,
        18,
    )

    dibujar_linea(
        (-3, -320),
        (-3, CENTRO_Y - 35),
        COLOR_TALLO_LUZ,
        3,
    )


def dibujar_hoja(origen, angulo, escala=1.0):
    """Construye una hoja mediante un polígono y su nervadura."""
    forma = [
        (0, 0),
        (20, 18),
        (45, 30),
        (73, 32),
        (105, 12),
        (115, 0),
        (86, -7),
        (55, -6),
        (25, -3),
    ]

    puntos = transformar(
        forma,
        origen,
        angulo,
        escala,
        escala,
    )

    dibujar_poligono(
        puntos,
        COLOR_HOJA,
        COLOR_HOJA_BORDE,
    )

    nervadura = transformar(
        [(5, 0), (35, 5), (70, 8), (104, 7)],
        origen,
        angulo,
        escala,
        escala,
    )

    for inicio, fin in zip(nervadura, nervadura[1:]):
        dibujar_linea(inicio, fin, "#83BE72", 2)


# ---------------------- PÉTALOS ------------------------------

FORMA_PETALO = [
    (16, -8),
    (31, -24),
    (65, -34),
    (101, -29),
    (145, 0),
    (101, 29),
    (65, 34),
    (31, 24),
]

COLORES_PETALOS = [
    "#FFD447",
    "#FFC52F",
    "#FFE36B",
    "#FFB91F",
    "#FFDA4A",
]


def dibujar_petalo(centro, angulo, escala=1.0,
                   escala_ancho=1.0, color=None):
    """Dibuja un pétalo individual con forma de lágrima."""
    if color is None:
        color = random.choice(COLORES_PETALOS)

    puntos = transformar(
        FORMA_PETALO,
        centro,
        angulo,
        escala,
        escala * escala_ancho,
    )

    dibujar_poligono(
        puntos,
        color,
        "#E6A525",
    )


def dibujar_petalo_capa_exterior():
    """Distribuye los pétalos grandes alrededor del centro."""
    cantidad = 28

    for i in range(cantidad):
        angulo = i * 360 / cantidad
        escala = random.uniform(0.94, 1.06)
        ancho = random.uniform(0.91, 1.05)

        dibujar_petalo(
            (CENTRO_X, CENTRO_Y),
            angulo,
            escala,
            ancho,
        )


def dibujar_petalo_capa_interior():
    """Añade una segunda capa para dar profundidad a la flor."""
    cantidad = 22

    for i in range(cantidad):
        angulo = i * 360 / cantidad + 360 / (cantidad * 2)

        dibujar_petalo(
            (CENTRO_X, CENTRO_Y),
            angulo,
            escala=random.uniform(0.68, 0.79),
            escala_ancho=random.uniform(0.85, 1.0),
            color=random.choice([
                "#FFE36B",
                "#FFD447",
                "#FFC52F",
            ]),
        )


# ---------------------- CENTRO DE LA FLOR --------------------

def dibujar_centro():
    """Dibuja el disco central y sus semillas en espiral."""
    lapiz.goto(CENTRO_X, CENTRO_Y)
    lapiz.dot(130, "#5A2C18")
    lapiz.dot(118, "#84451F")
    lapiz.dot(105, "#67351C")

    # Ángulo áureo: aproximadamente 137,5 grados.
    angulo_aureo = math.radians(137.507764)

    colores_semillas = [
        "#2C180F",
        "#3A2012",
        "#4B2815",
        "#B97935",
        "#D39A47",
    ]

    cantidad = 430

    for i in range(cantidad):
        radio = 2.25 * math.sqrt(i)
        angulo = i * angulo_aureo

        x = CENTRO_X + radio * math.cos(angulo)
        y = CENTRO_Y + radio * math.sin(angulo)

        tamano = random.choice([3, 3, 4, 4, 5])
        color = random.choices(
            colores_semillas,
            weights=[30, 30, 24, 11, 5],
            k=1,
        )[0]

        lapiz.goto(x, y)
        lapiz.dot(tamano, color)


# ---------------------- TEXTO Y DECORACIÓN -------------------

def dibujar_mensaje():
    """Escribe el mensaje con una sombra sutil."""
    # Sombra del título.
    lapiz.goto(2, 317)
    lapiz.color("#633C29")
    lapiz.write(
        "Te quiero",
        align="center",
        font=("DejaVu Serif", 32, "bold"),
    )

    # Texto principal.
    lapiz.goto(0, 320)
    lapiz.color("#FFE5A3")
    lapiz.write(
        "Te quiero",
        align="center",
        font=("DejaVu Serif", 32, "bold"),
    )

    # Frase secundaria.
    lapiz.goto(0, 286)
    lapiz.color("#AFC6D9")
    lapiz.write(
        "Mi mundo florece contigo",
        align="center",
        font=("DejaVu Sans", 12, "normal"),
    )


def dibujar_suelo():
    """Añade una base discreta para cerrar la composición."""
    dibujar_linea(
        (-490, -350),
        (490, -350),
        "#193A32",
        3,
    )

    for x in range(-450, 451, 30):
        altura = random.randint(4, 12)

        dibujar_linea(
            (x, -350),
            (x + random.randint(-5, 5), -350 + altura),
            "#28563B",
            2,
        )


# ---------------------- PROGRAMA PRINCIPAL -------------------

def crear_girasol():
    dibujar_estrellas()

    # Decoración del cielo.
    dibujar_destello(-365, 220, 12, "#FFE7A1")
    dibujar_destello(365, 205, 15, "#BFDFFF")
    dibujar_destello(-330, -40, 8, "#FFE7A1")
    dibujar_destello(360, -105, 10, "#BFDFFF")

    # Elementos vegetales, del fondo hacia el frente.
    dibujar_suelo()
    dibujar_tallo()

    dibujar_hoja((0, -160), 34, 1.0)
    dibujar_hoja((0, -235), 148, 0.82)

    # Flor en capas.
    dibujar_petalo_capa_exterior()
    dibujar_petalo_capa_interior()
    dibujar_centro()

    # El mensaje se coloca al final para que quede visible.
    dibujar_mensaje()

    # Mostrar todo de una sola vez.
    screen.update()


if __name__ == "__main__":
    crear_girasol()
    screen.mainloop()
