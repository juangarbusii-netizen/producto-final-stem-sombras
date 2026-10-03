"""Detalle de anclajes + cámaras con zoom para entrega-final/Idea final.blend.

Uso (desde la raíz del proyecto):
    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b "entrega-final/Idea final.blend" --python calculos/blender_detalle_anclajes.py

Es idempotente: borra lo que generó en una corrida anterior y lo vuelve a crear.
No mueve ni borra nada de la estructura original (postes, bases, cables, malla):
solo agrega geometría de detalle, oculta en render los 10 cubos genéricos de
"Anclaje_*_cable_*" (reemplazados por el herraje detallado) y crea la escena
"Zoom_Anclajes" con cámaras que se acercan a los anclajes.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))

COL_PISO = "Detalle_anclajes_piso"
COL_ALTO = "Detalle_anclajes_alto"
COL_CAMS = "Zoom_Camaras"
ESCENA_ZOOM = "Zoom_Anclajes"


# --------------------------------------------------------------------------
# Materiales
# --------------------------------------------------------------------------
def material(nombre, base, metal, rugosidad):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rugosidad
    m.diffuse_color = (*base, 1)
    return m


def mejorar_hormigon():
    """Agrega relieve de ruido al material Hormigon existente (bases y muertos)."""
    m = bpy.data.materials["Hormigon"]
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if nt.nodes.get("Hormigon_ruido"):
        return
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.name = "Hormigon_ruido"
    ruido.inputs["Scale"].default_value = 60
    ruido.inputs["Detail"].default_value = 10
    ruido.inputs["Roughness"].default_value = 0.7
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(ruido.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.92


# --------------------------------------------------------------------------
# Constructor de piezas (bmesh con índice de material)
# --------------------------------------------------------------------------
def rot_a(eje):
    """Rotación 4x4 que lleva +Z al vector `eje`."""
    return Z.rotation_difference(eje.normalized()).to_matrix().to_4x4()


class Pieza:
    def __init__(self, mats):
        self.bm = bmesh.new()
        self.mats = mats
        self.mi = 0

    def _marcar(self, n0, suave):
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[n0:]:
            f.material_index = self.mi
            if suave and len(f.verts) == 4:
                f.smooth = True

    def cil(self, p0, p1, r, seg=16, r2=None, suave=True):
        p0, p1 = Vector(p0), Vector(p1)
        n0 = len(self.bm.faces)
        eje = p1 - p0
        M = Matrix.Translation((p0 + p1) / 2) @ rot_a(eje)
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=r if r2 is None else r2,
                              depth=eje.length, matrix=M, calc_uvs=False)
        self._marcar(n0, suave)

    def hexa(self, p0, p1, r):
        self.cil(p0, p1, r, seg=6, suave=False)

    def caja(self, c, tam, rot=None):
        n0 = len(self.bm.faces)
        M = Matrix.Translation(c) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal(Vector((*tam, 1)))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=M, calc_uvs=False)
        self._marcar(n0, False)

    def prisma(self, pts2d, espesor, M):
        """Prisma triangular/poligonal: pts2d en el plano (a, z) del local, extruido en y."""
        n0 = len(self.bm.faces)
        h = espesor / 2
        a = [self.bm.verts.new(M @ Vector((p[0], -h, p[1]))) for p in pts2d]
        b = [self.bm.verts.new(M @ Vector((p[0], h, p[1]))) for p in pts2d]
        n = len(pts2d)
        self.bm.faces.new(a[::-1])
        self.bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((a[i], a[j], b[j], b[i]))
        self._marcar(n0, False)

    def tubo(self, pts, r, seg=10, cerrado=False, suave=True):
        n0 = len(self.bm.faces)
        pts = [Vector(p) for p in pts]
        N = len(pts)
        tans = []
        for i in range(N):
            a = pts[(i - 1) % N] if cerrado else pts[max(i - 1, 0)]
            b = pts[(i + 1) % N] if cerrado else pts[min(i + 1, N - 1)]
            tans.append((b - a).normalized())
        ref = tans[0].cross(Z)
        if ref.length < 1e-4:
            ref = tans[0].cross(X)
        nrm = ref.normalized()
        anillos = []
        for i in range(N):
            t = tans[i]
            nrm = (nrm - t * nrm.dot(t)).normalized()
            b2 = t.cross(nrm)
            anillos.append([
                self.bm.verts.new(pts[i] + (nrm * math.cos(2 * math.pi * k / seg)
                                            + b2 * math.sin(2 * math.pi * k / seg)) * r)
                for k in range(seg)])
        for i in range(N if cerrado else N - 1):
            r0, r1 = anillos[i], anillos[(i + 1) % N]
            for k in range(seg):
                self.bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
        if not cerrado:
            self.bm.faces.new(anillos[0][::-1])
            self.bm.faces.new(anillos[-1])
        self._marcar(n0, suave)

    def toro(self, c, normal, R, r, n=28, seg=10):
        c, normal = Vector(c), Vector(normal).normalized()
        u = normal.cross(Z)
        if u.length < 1e-4:
            u = normal.cross(X)
        u.normalize()
        v = normal.cross(u)
        pts = [c + (u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n)) * R
               for k in range(n)]
        self.tubo(pts, r, seg=seg, cerrado=True)

    def transformar_desde(self, n_caras, M):
        """Aplica M a los vértices de las caras agregadas desde n_caras."""
        self.bm.faces.ensure_lookup_table()
        vs = {v for f in self.bm.faces[n_caras:] for v in f.verts}
        bmesh.ops.transform(self.bm, matrix=M, verts=list(vs))

    def a_malla(self, nombre):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(nombre)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        return me


# --------------------------------------------------------------------------
# Herrajes
# --------------------------------------------------------------------------
def herraje_vaina(galv, interior):
    """Boca de la vaina (tubo cuadrado 200x200x4,75 mm) a ras del piso, con el poste entrando.
    Origen: centro de la vaina, a nivel del piso. El pasador y el resto quedan dentro del hormigón."""
    P = Pieza([galv, interior])
    t, h, z0 = 0.00475, 0.012, 0.02
    P.caja((0, 0.1 - t / 2, z0 + h / 2), (0.2, t, h))
    P.caja((0, -0.1 + t / 2, z0 + h / 2), (0.2, t, h))
    P.caja((0.1 - t / 2, 0, z0 + h / 2), (t, 0.2 - 2 * t, h))
    P.caja((-0.1 + t / 2, 0, z0 + h / 2), (t, 0.2 - 2 * t, h))
    P.mi = 1
    P.caja((0, 0, z0 + 0.0005), (0.19, 0.19, 0.001))
    return P.a_malla("Vaina_modelo")


def herraje_orejas(galv, perno):
    """Orejas soldadas al costado sur del poste para el tensor. Origen: el pasador (eje X);
    el poste queda hacia +Y (su superficie está a +0.053)."""
    P = Pieza([galv, perno])
    P.caja((0, 0.06, 0), (0.09, 0.02, 0.11))
    for cx in (-0.03, 0.03):
        P.caja((cx, 0.035, 0), (0.012, 0.07, 0.10))
        P.cil((cx - 0.006, 0, 0), (cx + 0.006, 0, 0), 0.05, seg=32)
    P.mi = 1
    P.cil((-0.085, 0, 0), (0.085, 0, 0), 0.011, seg=14)
    P.cil((-0.087, 0, 0), (-0.070, 0, 0), 0.022, seg=20)
    P.cil((0.040, 0, 0), (0.046, 0, 0), 0.028, seg=20)
    P.hexa((0.046, 0, 0), (0.066, 0, 0), 0.021)
    return P.a_malla("Orejas_tensor_modelo")


def herraje_abrazaderas(galv, perno, dy, dz):
    """Dos prensacables sobre el cabezal que fijan el cable. Origen: centro del cabezal a z=7.
    El cable pasa en (dy, dz) relativo a ese origen."""
    P = Pieza([galv, perno])
    for sx in (-0.11, 0.11):
        P.caja((sx, dy, dz + 0.018), (0.04, 0.07, 0.012))
        P.mi = 1
        for sy in (-1, 1):
            P.cil((sx, dy + 0.025 * sy, 0.0), (sx, dy + 0.025 * sy, dz + 0.034), 0.006, seg=10)
            P.hexa((sx, dy + 0.025 * sy, dz + 0.024), (sx, dy + 0.025 * sy, dz + 0.034), 0.011)
        P.mi = 0
    return P.a_malla("Abrazaderas_modelo")


def _grillete_u(P, perno):
    """Grillete en U (patas en +-X, arco hacia +Z). Origen: el pasador."""
    P.mi = 0
    pts = [(-0.045, 0, 0), (-0.045, 0, 0.07)]
    for i in range(1, 16):
        a = math.pi - math.pi * i / 16
        pts.append((0.045 * math.cos(a), 0, 0.07 + 0.045 * math.sin(a)))
    pts += [(0.045, 0, 0.07), (0.045, 0, 0)]
    P.tubo(pts, 0.0075, seg=10)
    if perno:
        P.mi = 1
        P.cil((-0.06, 0, 0), (0.06, 0, 0), 0.011, seg=14)
        P.cil((-0.062, 0, 0), (-0.048, 0, 0), 0.020, seg=18)
        P.hexa((0.048, 0, 0), (0.066, 0, 0), 0.019)


def _gancho(P, zc, R=0.025, r=0.008):
    """Gancho abierto (arco de 320 grados) en el plano XZ, apoyado en z = zc - R."""
    pts = [(R * math.cos(math.radians(-90 + k * 16)), 0, zc + R * math.sin(math.radians(-90 + k * 16)))
           for k in range(21)]
    P.tubo(pts, r, seg=10)


def _apretacables(P, z0, n=3, sep=0.07):
    """Apretacables (silleta + 2 tuercas) a lo largo del cable, a partir de z0."""
    for k in range(n):
        z = z0 + k * sep
        P.mi = 0
        P.caja((0, 0, z), (0.05, 0.03, 0.02))
        P.mi = 1
        for sx in (-1, 1):
            P.hexa((0.027 * sx, 0, z), (0.040 * sx, 0, z), 0.011)


# Distancia desde el pasador hasta el centro del guardacabo donde termina el cable (ver cadena_cable)
GUARDACABO_CON_TENSOR = 0.48
GUARDACABO_SIN_TENSOR = 0.135
ESCALA_PARED = 1.4
PIN_PARED = 0.13


def cadena_cable(P, perno, tensor):
    """Grillete + guardacabo + (tensor ojo y gancho) + 3 apretacables, a lo largo de +Z local desde el pasador."""
    _grillete_u(P, perno)
    P.mi = 0
    P.toro((0, 0, 0.135), X, 0.03, 0.008)  # ojo del tensor / guardacabo, enlazado con el arco del grillete
    if tensor:
        z = 0.165
        P.mi = 1
        P.cil((0, 0, z), (0, 0, z + 0.05), 0.010, seg=12)
        P.mi = 0
        P.cil((0, 0, z + 0.05), (0, 0, z + 0.21), 0.020, seg=18)
        P.mi = 1
        P.hexa((0, 0, z + 0.05), (0, 0, z + 0.065), 0.025)
        P.hexa((0, 0, z + 0.195), (0, 0, z + 0.21), 0.025)
        P.cil((0, 0, z + 0.20), (0, 0, z + 0.26), 0.010, seg=12)
        P.mi = 0
        _gancho(P, z + 0.285)
        zt = z + 0.285 + 0.03  # guardacabo del cable, enganchado en el gancho
        P.toro((0, 0, zt), X, 0.03, 0.008)
        _apretacables(P, zt + 0.06)
    else:
        _apretacables(P, 0.135 + 0.06)


def herraje_grillete(galv, perno):
    """Extremo del tensor en el poste (el pasador lo pone `herraje_orejas`)."""
    P = Pieza([galv, perno])
    cadena_cable(P, False, False)
    return P.a_malla("Grillete_modelo")


def herraje_muerto(galv, perno, d):
    """Argolla empotrada en el bloque de hormigón + cadena hacia el cable.
    Origen: centro de la cara superior del bloque. `d` = dirección de tensión (hacia el poste)."""
    P = Pieza([galv, perno])
    pin = Vector((0, 0, 0.13)) - d * 0.05  # sobre la línea del cable, que arranca en z=0.13 local
    P.toro((0, pin.y, 0.04), X, 0.065, 0.009, n=32)  # argolla de barra de 16 mm
    n0 = len(P.bm.faces)
    cadena_cable(P, True, True)
    P.transformar_desde(n0, Matrix.Translation(pin) @ rot_a(d))
    return P.a_malla("Muerto_herraje_modelo")


def herraje_pared(galv, perno, tilt):
    """Planchuela 5/8" x 5" x 0,30 m con 4 varillas de 1/2" en línea, oreja soldada y cadena hacia el cable
    (grillete 7/8", tensor ojo y gancho 22 mm, 3 apretacables). Origen: punto del cable sobre la pared; +X al patio."""
    P = Pieza([galv, perno])
    P.caja((0.008, 0, 0), (0.016, 0.127, 0.30))
    P.mi = 1
    for z in (-0.12, -0.06, 0.06, 0.12):
        P.cil((0.016, 0, z), (0.040, 0, z), 0.0064, seg=10)
        P.cil((0.016, 0, z), (0.020, 0, z), 0.020, seg=18)
        P.hexa((0.020, 0, z), (0.036, 0, z), 0.012)
    P.mi = 0
    P.cil((0.016, 0, 0), (0.075, 0, 0), 0.014, seg=14)
    P.toro((0.125, 0, 0), Y, 0.05, 0.011, n=36)  # oreja soldada (plano XZ)
    n0 = len(P.bm.faces)
    cadena_cable(P, True, True)
    ejes = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_4x4()  # X_l->Y, Y_l->Z, Z_l->X
    P.transformar_desde(n0, Matrix.Rotation(tilt, 4, "Y") @ Matrix.Translation((PIN_PARED, 0, 0))
                        @ ejes @ Matrix.Scale(ESCALA_PARED, 4))
    return P.a_malla("Pared_herraje_modelo")


# --------------------------------------------------------------------------
# Escena
# --------------------------------------------------------------------------
def limpiar():
    for nombre in (COL_PISO, COL_ALTO, COL_CAMS):
        col = bpy.data.collections.get(nombre)
        if col:
            for o in list(col.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(col)
    z = bpy.data.scenes.get(ESCENA_ZOOM)
    if z:
        bpy.data.scenes.remove(z)
    for n in ("Malla_mesh_zoom",):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    malla = bpy.data.objects.get("Malla_mesh")
    if malla:
        malla.hide_render = False
        malla.hide_viewport = False
    for c in [c for c in bpy.data.collections if c.name.endswith("_zoom")]:
        bpy.data.collections.remove(c)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)
    for c in [c for c in bpy.data.cameras if c.users == 0]:
        bpy.data.cameras.remove(c)
    for l in [l for l in bpy.data.lights if l.users == 0]:
        bpy.data.lights.remove(l)


def nueva_col(nombre, escena):
    col = bpy.data.collections.new(nombre)
    escena.collection.children.link(col)
    return col


def instancia(nombre, malla, matriz, col):
    o = bpy.data.objects.new(nombre, malla)
    o.matrix_world = matriz
    col.objects.link(o)
    return o


def puntos_cable(cable_obj):
    """Puntos del cable tal como estaban antes de recortarlo (se guardan en el dato la primera vez)."""
    cd = cable_obj.data
    if "pts_originales" not in cd:
        cd["pts_originales"] = [c for p in cd.splines[0].points for c in p.co[:3]]
    flat = list(cd["pts_originales"])
    return [Vector(flat[i:i + 3]) for i in range(0, len(flat), 3)]


def curva_z(cable_obj):
    """Devuelve (xs, y, zs) de la polilínea original del cable."""
    pts = puntos_cable(cable_obj)
    return [p.x for p in pts], pts[0].y, [p.z for p in pts]


def z_y_pendiente(xs, zs, x):
    i = min(max(int(round((x - xs[0]) / (xs[1] - xs[0]))), 1), len(xs) - 2)
    return zs[i], (zs[i + 1] - zs[i - 1]) / (xs[i + 1] - xs[i - 1])


def recortar_cables(cables, tilt, d_ten, postes_sur):
    """Los cables terminan en el guardacabo del herraje, no en la pared ni en el tope del poste.
    Principales: se descartan los puntos entre la pared y el guardacabo. Tensores sur: se desplazan los dos extremos."""
    L = PIN_PARED + GUARDACABO_CON_TENSOR * ESCALA_PARED
    dx, dz = L * math.cos(tilt), L * math.sin(tilt)
    for i in range(1, 6):
        obj = bpy.data.objects["Cable_%d" % i]
        cd = obj.data
        pts = puntos_cable(obj)
        x0, x1 = pts[0].x, pts[-1].x
        z_ext = pts[0].z
        nuevos = [p for p in pts if dx - 1e-4 <= p.x - x0 <= (x1 - x0) - dx + 1e-4]
        nuevos[0] = Vector((x0 + dx, pts[0].y, z_ext - dz))
        nuevos[-1] = Vector((x1 - dx, pts[0].y, z_ext - dz))
        cd.splines.clear()
        ns = cd.splines.new("POLY")
        ns.points.add(len(nuevos) - 1)
        for p, v in zip(ns.points, nuevos):
            p.co = (v.x, v.y, v.z, 1.0)
    # tensores sur
    for n, (cx, _) in enumerate(postes_sur, start=1):
        me = bpy.data.objects["Tensor_sur_%d" % n].data
        sup = [v for v in me.vertices if v.co.z > 3.5]
        inf = [v for v in me.vertices if v.co.z <= 3.5]
        pin_sup = Vector((cx, -0.3 * d_ten.y / d_ten.z, 6.70))
        meta_sup = pin_sup - d_ten * GUARDACABO_SIN_TENSOR
        meta_inf = Vector((cx, -3.5, 0.15)) + d_ten * (GUARDACABO_CON_TENSOR - 0.05)
        for grupo, meta in ((sup, meta_sup), (inf, meta_inf)):
            c = sum((v.co for v in grupo), Vector()) / len(grupo)
            for v in grupo:
                v.co += meta - c
        me.update()


def construir_detalle(sc):
    galv = material("Acero_galvanizado", (0.62, 0.64, 0.66), 0.9, 0.32)
    perno = material("Bulon_acero", (0.30, 0.31, 0.33), 0.85, 0.42)
    interior = material("Vaina_interior", (0.02, 0.02, 0.02), 0.0, 0.9)
    mejorar_hormigon()

    col_p = nueva_col(COL_PISO, sc)
    col_a = nueva_col(COL_ALTO, sc)

    # Bevel no destructivo en hormigón
    for o in bpy.data.objects:
        if o.name.startswith(("Base_", "Muerto_tensor_")) and not o.modifiers:
            b = o.modifiers.new("Bisel", "BEVEL")
            b.width = 0.02
            b.segments = 2
            b.limit_method = "ANGLE"

    # Datos de cada cable y de cada poste
    cables = {i: curva_z(bpy.data.objects["Cable_%d" % i]) for i in range(1, 6)}
    fila_cable = {18.323: 2, 12.215: 3, 6.108: 4, 0.0: 5}

    postes = []
    for i in range(1, 13):
        o = bpy.data.objects["Poste_%02d" % i]
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx = sum(p.x for p in pts) / 8
        cy = sum(p.y for p in pts) / 8
        postes.append((i, cx, cy))

    pie = herraje_vaina(galv, interior)
    orejas = herraje_orejas(galv, perno)
    grillete = herraje_grillete(galv, perno)

    d_ten = Vector((0, 3.5, 6.85)).normalized()   # del muerto al cabezal
    muerto = herraje_muerto(galv, perno, d_ten)

    for i, cx, cy in postes:
        instancia("Vaina_poste_%02d" % i, pie, Matrix.Translation((cx, cy, 0)), col_p)
        tensado = abs(cy) < 0.01
        # prensacables: el cable apoya sobre el cabezal en z≈7
        k = min(fila_cable, key=lambda y: abs(y - cy))
        xs, ycable, zs = cables[fila_cable[k]]
        zc, _ = z_y_pendiente(xs, zs, cx)
        abraz = herraje_abrazaderas(galv, perno, ycable - cy, zc - 7.0)
        instancia("Abrazaderas_cable_%02d" % i, abraz, Matrix.Translation((cx, cy, 7.0)), col_a)
        if tensado:
            # el tensor sale por el costado sur del poste, donde la línea del tensor deja el fuste (z=6.70)
            pin = Vector((cx, cy - 0.3 * d_ten.y / d_ten.z, 6.70))
            instancia("Orejas_poste_%02d" % i, orejas, Matrix.Translation(pin), col_a)
            instancia("Grillete_poste_%02d" % i, grillete,
                      Matrix.Translation(pin) @ rot_a(-d_ten), col_a)
            instancia("Muerto_herraje_%d" % (i // 4), muerto,
                      Matrix.Translation((cx, -3.5, 0.02)), col_p)

    # Anclajes de pared: 5 cables, oeste (x=0) y este (x=40.9)
    xs, _, zs = cables[1]
    z0, pend0 = z_y_pendiente(xs, zs, xs[0] + (xs[1] - xs[0]))
    tilt = math.atan(abs(pend0))
    pared = herraje_pared(galv, perno, tilt)
    for n in range(1, 6):
        _, yc, zs_n = cables[n]
        z_ini = zs_n[0]
        instancia("Pared_anclaje_oeste_%d" % n, pared, Matrix.Translation((0.0, yc, z_ini)), col_a)
        instancia("Pared_anclaje_este_%d" % n, pared,
                  Matrix.Translation((40.9, yc, z_ini)) @ Matrix.Rotation(math.pi, 4, "Z"), col_a)
        for lado in ("oeste", "este"):
            viejo = bpy.data.objects.get("Anclaje_%s_cable_%d" % (lado, n))
            if viejo:
                viejo.hide_render = True
                viejo.hide_viewport = True

    recortar_cables(cables, tilt, d_ten,
                    [(cx, cy) for i, cx, cy in postes if abs(cy) < 0.01])


# --------------------------------------------------------------------------
# Cámaras de cerca (fijas, sin animación: el play sigue siendo el del sol)
# --------------------------------------------------------------------------
def crear_camaras_cerca(sc):
    cam_col = nueva_col(COL_CAMS, sc)
    P6 = Vector((20.45, 12.215, 0.10))
    M2 = Vector((20.45, -3.5, 0.14))
    H8 = Vector((20.45, -0.05, 6.88))
    AO = Vector((0.0, 12.22, 7.02))
    AE = Vector((40.9, 12.22, 7.02))
    # (nombre, objetivo, posición, focal)
    tomas = [
        ("Cam_Zoom_Piso_Poste", P6, P6 + Vector((0.95, -1.15, 0.6)), 50),
        ("Cam_Zoom_Piso_Tensor", M2, M2 + Vector((1.1, -1.5, 0.85)), 50),
        ("Cam_Zoom_Alto_Cabezal", H8, H8 + Vector((0.9, -1.45, 0.25)), 42),
        ("Cam_Zoom_Alto_Pared_Oeste", AO, AO + Vector((1.3, -1.2, -0.6)), 42),
        ("Cam_Zoom_Alto_Pared_Este", AE, AE + Vector((-1.3, -1.2, -0.6)), 42),
    ]
    for nombre, objetivo, pos, lente in tomas:
        vacio = bpy.data.objects.new("Objetivo_" + nombre[4:], None)
        vacio.empty_display_type = "SPHERE"
        vacio.empty_display_size = 0.1
        vacio.location = objetivo
        cam_col.objects.link(vacio)
        cd = bpy.data.cameras.new(nombre)
        cd.lens = lente
        cd.clip_start = 0.05
        cd.clip_end = 500
        cd.dof.use_dof = True
        cd.dof.focus_object = vacio
        cd.dof.aperture_fstop = 4.0
        co = bpy.data.objects.new(nombre, cd)
        co.location = pos
        cam_col.objects.link(co)
        con = co.constraints.new("TRACK_TO")
        con.target = vacio
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"


def instalar_botones():
    """Guarda calculos/blender_botones_camaras.py dentro del .blend como texto que se registra al abrir."""
    ruta = bpy.path.abspath("//../calculos/blender_botones_camaras.py")
    nombre = "Botones_camaras.py"
    viejo = bpy.data.texts.get(nombre)
    if viejo:
        bpy.data.texts.remove(viejo)
    t = bpy.data.texts.new(nombre)
    with open(ruta, encoding="utf-8") as f:
        t.from_string(f.read())
    t.use_module = True


def main():
    sc = bpy.data.scenes["Scene"] if "Scene" in bpy.data.scenes else bpy.context.scene
    limpiar()
    construir_detalle(sc)
    crear_camaras_cerca(sc)
    instalar_botones()
    bpy.ops.wm.save_mainfile()
    print("OK detalle + zoom")


main()
