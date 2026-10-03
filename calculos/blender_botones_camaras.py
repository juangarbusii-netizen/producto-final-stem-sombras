"""Panel "Sombra" (visor 3D > barra lateral N) con botones para mirar por las cámaras de cerca.

Se guarda dentro del .blend como texto "Botones_camaras.py" con "Register" activado, así el panel
aparece al abrir el archivo (Blender pide permitir la ejecución de scripts la primera vez).
Si no aparece: Scripting > abrir ese texto > Run Script (Alt+P).
"""
import bpy

ESCENA = "Scene"
# (texto del botón, cámara, ocultar la malla: tapa los anclajes de pared)
TOMAS = [
    ("Pie del poste", "Cam_Zoom_Piso_Poste", False),
    ("Muerto y tensor", "Cam_Zoom_Piso_Tensor", False),
    ("Cabezal del poste", "Cam_Zoom_Alto_Cabezal", False),
    ("Anclaje pared oeste", "Cam_Zoom_Alto_Pared_Oeste", True),
    ("Anclaje pared este", "Cam_Zoom_Alto_Pared_Este", True),
]


def _usar_camara(context, nombre, ocultar_malla):
    s = bpy.data.scenes[ESCENA]
    context.window.scene = s
    s.camera = bpy.data.objects[nombre]
    malla = bpy.data.objects.get("Malla_mesh")
    if malla:
        malla.hide_viewport = malla.hide_render = ocultar_malla
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces[0].region_3d.view_perspective = "CAMERA"


class SOMBRA_OT_ir_toma(bpy.types.Operator):
    bl_idname = "sombra.ir_toma"
    bl_label = "Ir a la cámara"
    bl_description = "Mira por esta cámara de cerca (el play sigue moviendo el sol)"

    indice: bpy.props.IntProperty()

    def execute(self, context):
        _, cam, ocultar = TOMAS[self.indice]
        _usar_camara(context, cam, ocultar)
        return {"FINISHED"}


class SOMBRA_OT_escena_general(bpy.types.Operator):
    bl_idname = "sombra.escena_general"
    bl_label = "Volver a Cam_General"
    bl_description = "Vuelve a la cámara general y muestra la malla"

    def execute(self, context):
        _usar_camara(context, "Cam_General", False)
        return {"FINISHED"}


class SOMBRA_PT_camaras(bpy.types.Panel):
    bl_label = "Cámaras de cerca"
    bl_idname = "SOMBRA_PT_camaras"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sombra"

    def draw(self, context):
        col = self.layout.column(align=True)
        for i, (texto, _cam, _m) in enumerate(TOMAS):
            col.operator("sombra.ir_toma", text=texto, icon="VIEW_CAMERA").indice = i
        self.layout.separator()
        self.layout.operator("sombra.escena_general", icon="SCENE_DATA")
        self.layout.label(text="Espacio = el sol se mueve (11:30 → 14:30)")


CLASES = (SOMBRA_OT_ir_toma, SOMBRA_OT_escena_general, SOMBRA_PT_camaras)


def register():
    for c in CLASES:
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
        bpy.utils.register_class(c)


register()
