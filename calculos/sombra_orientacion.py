"""Cálculo de sombras del patio para el 17 de octubre de 2026 (11:30 a 14:30).

Fuente única de los números de la presentación, de los .docx y del sol en Blender.

Ejes del patio: x hacia el este (desde la pared oeste), y hacia el norte (desde el
borde abierto sur). La pared norte está en y = LARGO_NS.

Orientación: el norte real está NORTE_OFFSET grados girado respecto de la
perpendicular a la pared larga. Positivo = hacia el este (sentido horario).
El dato correcto es +7. Con -7 se reproducen los números viejos (control).

Uso:
    python sombra_orientacion.py            # imprime todo con el norte correcto (+7)
    python sombra_orientacion.py --control  # norte viejo (-7), para comparar
    python sombra_orientacion.py --imagenes # además genera las imágenes del pptx
"""
import datetime as dt
import math
import os
import sys

# ---------------------------------------------------------------- datos
ANCHO_EO = 40.90      # m, pared oeste a pared este
LARGO_NS = 24.43      # m, borde abierto (sur) a pared norte
ALTO_PARED = 19.2     # m, paredes norte, este y oeste
LAT, LON = -34.90, -56.17   # Montevideo
UTC_OFFSET = -3
FECHA = (2026, 10, 17)
HORAS = [(11, 30), (12, 30), (13, 30), (14, 30)]
NORTE_OFFSET = +7.0

POSTES_X = [10.2, 20.5, 30.7]            # filas, desde la pared oeste
POSTES_DESDE_NORTE = [6.1, 12.2, 18.3, 24.4]  # cables 2 a 5, desde la pared norte


# ---------------------------------------------------------------- sol
def posicion_sol(hora, minuto):
    """Altura y azimut (0 = norte real, + hacia el este) con el algoritmo de la NOAA."""
    t = dt.datetime(*FECHA, hora, minuto, tzinfo=dt.timezone(dt.timedelta(hours=UTC_OFFSET)))
    jd = t.timestamp() / 86400 + 2440587.5
    T = (jd - 2451545) / 36525
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    r = math.radians
    C = (math.sin(r(M)) * (1.914602 - T * (0.004817 + 0.000014 * T))
         + math.sin(r(2 * M)) * (0.019993 - 0.000101 * T) + math.sin(r(3 * M)) * 0.000289)
    om = 125.04 - 1934.136 * T
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(r(om))
    eps = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
    eps += 0.00256 * math.cos(r(om))
    dec = math.degrees(math.asin(math.sin(r(eps)) * math.sin(r(lam))))
    y = math.tan(r(eps / 2)) ** 2
    eot = 4 * math.degrees(y * math.sin(2 * r(L0)) - 2 * e * math.sin(r(M))
                           + 4 * e * y * math.sin(r(M)) * math.cos(2 * r(L0))
                           - 0.5 * y * y * math.sin(4 * r(L0)) - 1.25 * e * e * math.sin(2 * r(M)))
    utc = t.astimezone(dt.timezone.utc)
    tst = (utc.hour * 60 + utc.minute + eot + 4 * LON) % 1440
    ha = r(tst / 4 - 180)
    lat, d = r(LAT), r(dec)
    alt = math.degrees(math.asin(math.sin(lat) * math.sin(d) + math.cos(lat) * math.cos(d) * math.cos(ha)))
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(d) * math.cos(lat)))
    az = (az + 360) % 360 - 180   # 0 = norte, + este
    return alt, az


def soles(offset):
    """Por hora: altura, azimut real y rumbo en los ejes del patio (0 = pared norte, + este)."""
    out = []
    for h, m in HORAS:
        alt, az = posicion_sol(h, m)
        out.append(dict(hora=f"{h}:{m:02d}", alt=alt, az=az, rumbo=az + offset))
    return out


def corrimiento(sol, altura):
    """Corrimiento de la sombra de un objeto a `altura` m: (este +, sur +)."""
    largo = altura / math.tan(math.radians(sol["alt"]))
    b = math.radians(sol["rumbo"])
    return -largo * math.sin(b), largo * math.cos(b)


def rect_sol(sol):
    """Zona con sol directo a esa hora: rectángulo (x0, x1, y0, y1), exacto para 3 paredes."""
    este, sur = corrimiento(sol, ALTO_PARED)
    x0 = max(0.0, este)              # sombra de la pared oeste (sol desde el oeste)
    x1 = ANCHO_EO - max(0.0, -este)  # sombra de la pared este (sol desde el este)
    y1 = LARGO_NS - sur              # sombra de la pared norte
    return x0, x1, 0.0, y1


# ---------------------------------------------------------------- zonas
def zonas(offset):
    ss = soles(offset)
    rects = [rect_sol(s) for s in ss]
    xs = sorted({0.0, ANCHO_EO, *[r[0] for r in rects], *[r[1] for r in rects]})
    ys = sorted({0.0, LARGO_NS, *[r[3] for r in rects]})
    area = {"siempre": 0.0, "a veces": 0.0, "nunca": 0.0}
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            n_sol = sum(r[0] <= cx <= r[1] and cy <= r[3] for r in rects)
            k = "siempre" if n_sol == 0 else "nunca" if n_sol == len(rects) else "a veces"
            area[k] += (xb - xa) * (yb - ya)
    nunca = (max(r[0] for r in rects), min(r[1] for r in rects), 0.0, min(r[3] for r in rects))
    # banda siempre sombra: profundidad desde la pared norte, por tramo de x
    banda = []
    for xa, xb in zip(xs, xs[1:]):
        cx = (xa + xb) / 2
        ymax = max((r[3] for r in rects if r[0] <= cx <= r[1]), default=0.0)
        banda.append((xa, xb, LARGO_NS - ymax))
    return dict(soles=ss, rects=rects, area=area, nunca=nunca, banda=banda)


def zona_de(z, x, desde_norte):
    y = LARGO_NS - desde_norte
    if y <= 0.05:
        return "borde sur"
    n_sol = sum(r[0] <= x <= r[1] and y <= r[3] for r in z["rects"])
    return {0: "zona siempre sombra", len(z["rects"]): "zona nunca sombra"}.get(n_sol, "zona a veces sombra")


def techo_para_zona(z, altura):
    """Rectángulo mínimo de techo a `altura` cuya sombra cubre la zona nunca sombra a todas las horas."""
    x0, x1, y0, y1 = z["nunca"]
    cs = [corrimiento(s, altura) for s in z["soles"]]
    # sombra = techo corrido (este, -sur)  ->  techo debe contener zona corrida (-este, +sur)
    tx0 = x0 - max(c[0] for c in cs)
    tx1 = x1 - min(c[0] for c in cs)
    ty0 = y0 + min(c[1] for c in cs)
    ty1 = y1 + max(c[1] for c in cs)
    return tx0, tx1, ty0, ty1


# ---------------------------------------------------------------- informe
def f(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def lado(este):
    return f"{f(abs(este))} m al {'este' if este >= 0 else 'oeste'}"


def desde(rumbo):
    if abs(rumbo) < 10:
        return "norte"
    return "noreste" if rumbo > 0 else "noroeste"


def informe(offset):
    z = zonas(offset)
    tot = ANCHO_EO * LARGO_NS
    print(f"== Norte real {abs(offset):.0f}° hacia el {'este' if offset > 0 else 'oeste'} ==\n")
    print("Sol (17/10):")
    for s, r in zip(z["soles"], z["rects"]):
        sombra = 1 - (r[1] - r[0]) * r[3] / tot
        print(f"  {s['hora']}  altura {s['alt']:.1f}°  azimut real {s['az']:+.1f}°  rumbo patio {s['rumbo']:+.1f}°"
              f"  sombra {sombra*100:.0f}%  sol en x {f(r[0])}-{f(r[1])}, y <= {f(r[3])}")
    print("\nZonas:")
    for k, v in z["area"].items():
        print(f"  {k:8s} {v:6.0f} m²  {v/tot*100:3.0f}%")
    x0, x1, _, y1 = z["nunca"]
    print(f"  nunca sombra: {f(x1-x0)} × {f(y1)} m = {(x1-x0)*y1:.0f} m², a {f(x0)} m de la pared oeste"
          f" y {f(ANCHO_EO-x1)} m de la este; borde norte a {f(LARGO_NS-y1)} m de la pared norte")
    prof = [b[2] for b in z["banda"]]
    print(f"  banda siempre sombra: mínima {f(min(prof))} m, máxima {f(max(prof))} m")
    for xa, xb, p in z["banda"]:
        print(f"     x {f(xa):>5}-{f(xb):>5}: {f(p)} m")
    print(f"  prioridad 2 (todo el frente sin sombra fija): {f(ANCHO_EO)} × {f(LARGO_NS-min(prof))} m"
          f" = {ANCHO_EO*(LARGO_NS-min(prof)):.0f} m²")
    for h in (4, 6, 7):
        print(f"\nCorrimientos de una cubierta a {h} m:")
        for s in z["soles"]:
            e, su = corrimiento(s, h)
            print(f"  {s['hora']}  {s['alt']:.0f}°  sol desde {desde(s['rumbo']):8s}  {f(su)} m al sur  {lado(e)}")
    for h in (4, 6):
        t = techo_para_zona(z, h)
        print(f"\nTecho a {h} m para cubrir la zona nunca sombra: {f(t[1]-t[0])} × {f(t[3]-t[2])} m,"
              f" a {f(t[0])} m de la pared oeste, {f(ANCHO_EO-t[1])} m de la este y {f(t[2])} m desde el borde abierto")
    print("\nPostes:")
    n = 1
    for x in POSTES_X:
        for d in POSTES_DESDE_NORTE:
            print(f"  {n:2d}  x {f(x)}  a {f(d)} m de la pared norte  {zona_de(z, x, d)}")
            n += 1
    return z


# ---------------------------------------------------------------- imágenes del pptx
AZUL, AMARILLO, NARANJA, CLARO = "#3d5a80", "#f2b84b", "#e8623c", "#fbe9b0"
PARED, TINTA, PISO, SOL = "#6b5b4e", "#1f2a44", "#ede7da", "#e0a020"


def imagenes(z, carpeta, offset):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrow, Polygon

    os.makedirs(carpeta, exist_ok=True)
    W, L, P = ANCHO_EO, LARGO_NS, 1.6  # P = espesor dibujado de la pared

    def base(ax, piso=PISO):
        ax.add_patch(Rectangle((-P, 0), P, L + P, color=PARED, lw=0))
        ax.add_patch(Rectangle((W, 0), P, L + P, color=PARED, lw=0))
        ax.add_patch(Rectangle((-P, L), W + 2 * P, P, color=PARED, lw=0))
        ax.add_patch(Rectangle((0, 0), W, L, color=piso, lw=0))

    def borde(ax):
        ax.add_patch(Rectangle((0, 0), W, L, fill=False, ec=TINTA, lw=2.5, zorder=5))

    def flecha_norte(ax, x, y, largo=5.0):
        b = math.radians(offset)
        dx, dy = largo * math.sin(b), largo * math.cos(b)
        ax.add_patch(FancyArrow(x, y, dx, dy, width=0.45, head_width=1.9, head_length=1.8,
                                length_includes_head=True, color=TINTA, lw=0))
        ax.text(x + dx * 1.1, y + dy + 1.4, "N", ha="center", va="bottom", fontsize=17,
                fontweight="bold", color=TINTA)

    def zonas_dibujo(ax):
        x0, x1, _, y1 = z["nunca"]
        ax.add_patch(Rectangle((0, 0), W, L, color=AMARILLO, lw=0))
        for xa, xb, p in z["banda"]:
            ax.add_patch(Rectangle((xa, L - p), xb - xa, p, color=AZUL, lw=0))
        ax.add_patch(Rectangle((x0, 0), x1 - x0, y1, color=NARANJA, lw=0))

    def lienzo(px, dpi, xlim, ylim):
        fig = plt.figure(figsize=(px[0] / dpi, px[1] / dpi), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")
        return fig, ax

    lim_x, lim_y = (-3.9, 46.3), (-12.4, 30.8)  # mismo encuadre que las imágenes originales

    # image1: zonas sin texto (diapositivas 1 y 4)
    fig, ax = lienzo((1157, 994), 200, lim_x, lim_y)
    base(ax); zonas_dibujo(ax); borde(ax); flecha_norte(ax, 39.3, -11.0)
    fig.savefig(os.path.join(carpeta, "image1.png"), dpi=200); plt.close(fig)

    # image2: el patio
    fig, ax = lienzo((1157, 994), 200, lim_x, lim_y)
    base(ax); borde(ax)
    ax.text(W / 2, L + P / 2, "pared norte · 19,2 m de alto", ha="center", va="center", color="white", fontsize=10.5)
    ax.text(-P / 2, L / 2, "pared oeste · 19,2 m", ha="center", va="center", color="white", fontsize=10.5, rotation=90)
    ax.text(W + P / 2, L / 2, "pared este · 19,2 m", ha="center", va="center", color="white", fontsize=10.5, rotation=-90)
    ax.text(W / 2, L / 2 + 2.2, "PATIO", ha="center", va="center", color=TINTA, fontsize=22, fontweight="bold")
    ax.text(W / 2, L / 2 - 2.2, "40,90 m × 24,43 m", ha="center", va="center", color=TINTA, fontsize=22, fontweight="bold")
    ax.text(W / 2, -2.2, "LADO ABIERTO (sur)", ha="center", va="center", color=TINTA, fontsize=13, fontweight="bold")
    flecha_norte(ax, 39.3, -11.0)
    fig.savefig(os.path.join(carpeta, "image2.png"), dpi=200); plt.close(fig)

    # image3: hora por hora
    fig = plt.figure(figsize=(1765 / 170, 1411 / 170), dpi=170)
    tot = W * L
    for i, (s, r) in enumerate(zip(z["soles"], z["rects"])):
        ax = fig.add_axes([0.0 + (i % 2) * 0.533, 0.5 - (i // 2) * 0.497, 0.467, 0.5])
        ax.set_xlim(-2, W + 2); ax.set_ylim(-14.5, L + 6.0); ax.set_aspect("equal"); ax.axis("off")
        base(ax, AZUL)
        ax.add_patch(Rectangle((r[0], 0), r[1] - r[0], r[3], color=CLARO, lw=0))
        borde(ax)
        ax.text(W / 2, L + 3.4, f"{s['hora']} h", ha="center", va="center", fontsize=15, fontweight="bold", color=TINTA)
        b = math.radians(s["rumbo"])
        dx, dy = -math.sin(b) * 5.5, -math.cos(b) * 5.5   # flecha = hacia dónde cae la sombra
        cx, cy = 10.5, -5.5
        ax.add_patch(FancyArrow(cx - dx / 2, cy - dy / 2, dx, dy, width=0.45, head_width=1.6, head_length=1.6,
                                length_includes_head=True, color=SOL, lw=0))
        ax.text(W / 2 + 4.5, -5.0, f"☀ sol a {s['alt']:.0f}° de altura", ha="center", va="center", fontsize=12.5, color=TINTA)
        sombra = 1 - (r[1] - r[0]) * r[3] / tot
        ax.text(W / 2, -10.0, f"sombra {sombra*100:.0f}% del patio", ha="center", va="center", fontsize=10.5, color=TINTA)
    fig.savefig(os.path.join(carpeta, "image3.png"), dpi=170); plt.close(fig)

    # image4: qué techar, con cotas
    x0, x1, _, y1 = z["nunca"]
    pmin = min(b[2] for b in z["banda"])
    fig, ax = lienzo((1578, 1054), 220, (-3.9, 64.5), (-16.1, 29.5))
    base(ax); zonas_dibujo(ax); borde(ax)
    ax.plot([0, W], [L - pmin, L - pmin], color="white", lw=3, ls=(0, (4, 2)), zorder=6)
    ax.text(W / 2, L - pmin / 2 + 1.0, "SIEMPRE SOMBRA", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(W / 2, L - pmin / 2 - 1.6, f"banda de {f(pmin)} m junto a la pared norte · no se techa",
            ha="center", va="center", color="white", fontsize=11)
    ax.text((x0 + x1) / 2, y1 * 0.62, "NUNCA SOMBRA", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text((x0 + x1) / 2, y1 * 0.45, f"{f(x1-x0)} × {f(y1)} m", ha="center", va="center", color="white", fontsize=18, fontweight="bold")
    ax.text((x0 + x1) / 2, y1 * 0.28, f"{(x1-x0)*y1:.0f} m²", ha="center", va="center", color="white", fontsize=14)
    ancho_izq, ancho_der = x0, W - x1
    xv = x0 / 2 if ancho_izq >= ancho_der else (x1 + W) / 2
    ax.text(xv, y1 * 0.5, "A VECES\n(intermitente)", ha="center", va="center", color=TINTA, fontsize=10,
            fontweight="bold", linespacing=1.2)

    def cota(xa, ya, xb, yb, texto, color=TINTA, rot=0, off=(0, 0)):
        ax.annotate("", (xa, ya), (xb, yb), arrowprops=dict(arrowstyle="<->", color=color, lw=2.2,
                                                           shrinkA=0, shrinkB=0, mutation_scale=16))
        ax.text((xa + xb) / 2 + off[0], (ya + yb) / 2 + off[1], texto, ha="center", va="center", color=color,
                fontsize=13, fontweight="bold", rotation=rot)

    yc = -2.4
    cota(0.2, yc, x0 - 0.2, yc, f(x0), off=(0, -1.8))
    cota(x0 + 0.2, yc, x1 - 0.2, yc, f(x1 - x0), off=(0, -1.8))
    cota(x1 + 0.2, yc, W - 0.2, yc, f(W - x1), off=(0, -1.8))
    cota(0.2, -9.0, W - 0.2, -9.0, "40,9 m (largo del patio = ancho del toldo)", off=(0, -1.8))
    ax.text(W / 2, -13.6, "Medidas desde el lado abierto (sur) y desde la pared oeste", ha="center", va="center",
            color=TINTA, fontsize=11)
    cota(46.6, 0.2, 46.6, y1, f"{f(y1)} m", color="#c0442a", rot=90, off=(-1.6, 0))
    cota(53.2, 0.2, 53.2, L - pmin, f"{f(L - pmin)} m (toldo)", rot=90, off=(-1.6, 0))
    cota(59.8, 0.2, 59.8, L + 0.4, "24,43 m (patio)", rot=90, off=(-1.6, 0))
    fig.savefig(os.path.join(carpeta, "image4.png"), dpi=220); plt.close(fig)


def imagen_planta_postes(z, ruta, offset):
    """Vista en planta de Recomendacion_postes_Idea2.docx: zonas, cables y los 12 postes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D

    W, L = ANCHO_EO, LARGO_NS
    fig = plt.figure(figsize=(2180 / 200, 1329 / 200), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-12.4, 50.6); ax.set_ylim(33.0, -5.4); ax.set_aspect("equal"); ax.axis("off")

    def d(y):  # y de los ejes del patio -> distancia desde la pared norte
        return L - y

    P = 0.6
    ax.add_patch(Rectangle((-P, -P), W + 2 * P, L + P, color="#555555", lw=0))
    ax.add_patch(Rectangle((0, 0), W, L, color="#f2e2b8", lw=0))
    for xa, xb, p in z["banda"]:
        ax.add_patch(Rectangle((xa, 0), xb - xa, p, color="#c9d6e2", lw=0))
    x0, x1, _, y1 = z["nunca"]
    ax.add_patch(Rectangle((x0, d(y1)), x1 - x0, y1, fc="#f0a37c", ec="#c0442a", lw=1.6, ls="--"))
    pmin = min(b[2] for b in z["banda"])
    ax.text(W / 2, 2.0, f"Siempre sombra (banda de {f(pmin)} m)", ha="center", va="center", color="#2c4766", fontsize=11)
    ax.text((x0 + x1) / 2, 15.25, f"Nunca sombra\n{f(x1-x0)} × {f(y1)} m", ha="center", va="center",
            color="#7a2b12", fontsize=11, fontweight="bold", linespacing=1.3)
    ax.text(x0 / 2, 15.25, "A veces\nsombra", ha="center", va="center", color="#7a5a1a", fontsize=11, linespacing=1.3)

    for i, dn in enumerate([0.0] + POSTES_DESDE_NORTE):
        ax.plot([0, W], [dn, dn], color="#2a6f97", lw=2, zorder=3)
        ax.text(W - 0.3, dn + (1.0 if i in (0, 4) else -0.7), f"Cable {i+1}", ha="right", va="center", color="#2a6f97", fontsize=9)
        ax.text(-3.5, dn, ("0 m" if dn == 0 else f"{f(dn)} m"), ha="right", va="center", color="#c0392b", fontsize=11)
    for x in POSTES_X:
        ax.plot([x, x], [0, L + 0.5], color="#999999", lw=0.8, ls=":", zorder=2)
        ax.text(x, L + 4.1, f"{f(x)} m", ha="center", va="center", color="#c0392b", fontsize=11)
        for dn in POSTES_DESDE_NORTE:
            ax.plot(x, dn, "o", ms=12, mfc="#c0392b", mec="white", mew=1.8, zorder=5)
    ax.text(W / 2, -2.4, "Pared norte (19,2 m de alto)", ha="center", va="center", fontsize=11)
    ax.text(-1.9, L / 2, "Pared oeste (19,2 m de alto)", ha="center", va="center", fontsize=11, rotation=90)
    ax.text(W + 1.9, L / 2, "Pared este (19,2 m de alto)", ha="center", va="center", fontsize=11, rotation=90)
    ax.text(W / 2, L + 2.1, "Lado sur abierto", ha="center", va="center", fontsize=11, style="italic")

    b = math.radians(offset)
    bx, by, largo = 46.5, 10.5, 5.6
    ax.annotate("", (bx + largo * math.sin(b), by - largo * math.cos(b)), (bx, by),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=2, mutation_scale=14))
    ax.text(bx + (largo + 1.8) * math.sin(b), by - largo - 1.8, "N", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(bx, by + 1.6, f"{abs(offset):.0f}°", ha="center", va="center", fontsize=10)

    ax.text(W / 2, L + 6.2, "Distancias en rojo: abajo, desde la pared oeste; a la izquierda, desde la pared norte."
            " Zonas de sombra según la presentación del 17 de octubre.", ha="center", va="center", fontsize=8.5, color="#666666")
    h = [Line2D([], [], marker="o", ls="", ms=10, mfc="#c0392b", mec="white", label="Poste de 7 m (12 en total)"),
         Line2D([], [], color="#2a6f97", lw=2, label="Cable de acero este-oeste")]
    fig.legend(handles=h, loc="lower center", ncol=2, frameon=False, fontsize=11, bbox_to_anchor=(0.5, 0.005))
    fig.savefig(ruta, dpi=200); plt.close(fig)


def imagen_toldo(z, ruta, altura=4.0):
    """Ubicación del techo a `altura` m (Ideas_para_techar_el_patio.docx)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    W, L, P = ANCHO_EO, LARGO_NS, 1.6
    fig = plt.figure(figsize=(1489 / 200, 1056 / 200), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-6.2, 47.0); ax.set_ylim(-13.0, 26.7); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((-P, 0), W + 2 * P, L + P, color=PARED, lw=0))
    ax.add_patch(Rectangle((0, 0), W, L, color=AMARILLO, lw=0))
    for xa, xb, p in z["banda"]:
        ax.add_patch(Rectangle((xa, L - p), xb - xa, p, color=AZUL, lw=0))
    x0, x1, _, y1 = z["nunca"]
    ax.add_patch(Rectangle((x0, 0), x1 - x0, y1, color=NARANJA, lw=0))
    t = techo_para_zona(z, altura)
    ax.add_patch(Rectangle((t[0], t[2]), t[1] - t[0], t[3] - t[2], color="white", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((t[0], t[2]), t[1] - t[0], t[3] - t[2], fill=False, ec=TINTA, lw=3.5, ls=(0, (4, 3))))
    ax.add_patch(Rectangle((0, 0), W, L, fill=False, ec=TINTA, lw=2, zorder=5))
    cx, cy = (t[0] + t[1]) / 2, (t[2] + t[3]) / 2
    ax.text(cx, cy + 2.0, f"TOLDO a {altura:.0f} m de altura", ha="center", va="center", color=TINTA, fontsize=13, fontweight="bold")
    ax.text(cx, cy - 1.7, f"{f(t[1]-t[0])} × {f(t[3]-t[2])} m", ha="center", va="center", color=TINTA, fontsize=17, fontweight="bold")

    def cota(xa, xb, texto):
        ax.annotate("", (xa, -2.0), (xb, -2.0), arrowprops=dict(arrowstyle="<->", color=TINTA, lw=2, shrinkA=0, shrinkB=0))
        ax.text((xa + xb) / 2, -3.9, texto, ha="center", va="center", color=TINTA, fontsize=11.5, fontweight="bold")

    cota(0.2, t[0] - 0.2, f(t[0])); cota(t[0] + 0.2, t[1] - 0.2, f(t[1] - t[0])); cota(t[1] + 0.2, W - 0.2, f(W - t[1]))
    ax.annotate("", (W - 2.0, 0.1), (W - 2.0, t[2] - 0.1), arrowprops=dict(arrowstyle="<->", color=TINTA, lw=1.6, shrinkA=0, shrinkB=0,
                                                                          mutation_scale=8))
    ax.text(W - 1.4, t[2] / 2, f(t[2]), ha="left", va="center", color=TINTA, fontsize=11, fontweight="bold")
    cs = [corrimiento(s, altura) for s in z["soles"]]
    sur = sum(c[1] for c in cs) / len(cs)
    ax.text(W / 2, -8.6, f"Su sombra cae ~{f(sur, 0)} m al sur, hasta {f(max(c[0] for c in cs))} m al este (tarde)"
            f" y {f(-min(c[0] for c in cs))} m al oeste (mañana)", ha="center", va="center", color=TINTA, fontsize=10.5)
    fig.savefig(ruta, dpi=200); plt.close(fig)


if __name__ == "__main__":
    off = -7.0 if "--control" in sys.argv else NORTE_OFFSET
    z = informe(off)
    if "--imagenes" in sys.argv:
        dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagenes" + ("_control" if off < 0 else ""))
        imagenes(z, dest, off)
        imagen_planta_postes(z, os.path.join(dest, "planta_postes.png"), off)
        imagen_toldo(z, os.path.join(dest, "toldo_4m.png"))
        print(f"\nImágenes en {dest}")
