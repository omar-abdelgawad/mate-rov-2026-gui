bl_info = {
    "name": "PVC Frame Generator",
    "author": "ROV Team",
    "version": (2, 0),
    "blender": (3, 0, 0),
    "location": "View3D > N-panel > PVC Tool",
    "description": "Generate a 3-section PVC pipe frame with dimension labels",
    "category": "Object",
}

import bpy
import bmesh
from mathutils import Matrix, Vector


# ==========================================
# 1. Property Group
# ==========================================
class PVC_Properties(bpy.types.PropertyGroup):
    pipe_diameter: bpy.props.FloatProperty(
        name="Pipe Diameter (in)",
        default=0.5,
        min=0.1,
        max=10.0,
        description="Outer diameter of the PVC pipe in inches",
    )
    width: bpy.props.FloatProperty(
        name="Common Width (cm)",
        default=36.0,
        min=1.0,
        description="Width (X-axis) shared across all 3 sections in cm",
    )

    # Simple mode inputs (outer-edge measurements)
    total_height: bpy.props.FloatProperty(
        name="Height — mid section (cm)",
        default=80.0,
        min=1.0,
        description="True outer-edge height of section 2 in cm",
    )
    total_length: bpy.props.FloatProperty(
        name="Total Length (cm)",
        default=110.0,
        min=1.0,
        description="True outer-edge total length (all 3 sections) in cm",
    )

    # Advanced toggle
    use_advanced: bpy.props.BoolProperty(
        name="Advanced Options",
        default=False,
        description="Override individual section dimensions",
    )

    # Advanced / per-section overrides (skeleton cm)
    l1: bpy.props.FloatProperty(name="Sec1 Length (cm)", default=48.32, min=0.1)
    h1: bpy.props.FloatProperty(name="Sec1 Height (cm)", default=47.24, min=0.1)
    l2: bpy.props.FloatProperty(name="Sec2 Length (cm)", default=24.16, min=0.1)
    h2: bpy.props.FloatProperty(name="Sec2 Height (cm)", default=78.73, min=0.1)
    l3: bpy.props.FloatProperty(name="Sec3 Length (cm)", default=36.24, min=0.1)
    h3: bpy.props.FloatProperty(name="Sec3 Height (cm)", default=31.49, min=0.1)

    # Judge reference
    correct_length: bpy.props.FloatProperty(
        name="Correct Length (cm)",
        default=0.0,
        min=0.0,
        description="Judge-provided correct total length in cm. 0 = skip reference model.",
    )


# ==========================================
# 2. Geometry helpers
# ==========================================
def build_pvc_mesh(bm, w, l1, h1, l2, h2, l3, h3):
    def add_box(x0, x1, y0, y1, z0, z1):
        v = [
            bm.verts.new((x0, y0, z0)), bm.verts.new((x1, y0, z0)),
            bm.verts.new((x1, y1, z0)), bm.verts.new((x0, y1, z0)),
            bm.verts.new((x0, y0, z1)), bm.verts.new((x1, y0, z1)),
            bm.verts.new((x1, y1, z1)), bm.verts.new((x0, y1, z1)),
        ]
        for a, b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            bm.edges.new((v[a], v[b]))
    y = 0.0
    add_box(0, w, y, y + l1, 0, h1); y += l1
    add_box(0, w, y, y + l2, 0, h2); y += l2
    add_box(0, w, y, y + l3, 0, h3)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)


def make_curve_from_bm(bm, name, collection, pipe_radius):
    me = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(me)
    obj = bpy.data.objects.new(name, me)
    collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="CURVE")
    curve = bpy.context.active_object
    curve.name = name
    curve.data.dimensions = "3D"
    curve.data.fill_mode = "FULL"
    curve.data.bevel_depth = pipe_radius
    curve.data.bevel_resolution = 6
    return curve


def make_material(name, color_rgba):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color_rgba
    mat.diffuse_color = color_rgba
    return mat


# ==========================================
# 3. Operator
# ==========================================
class OBJECT_OT_GeneratePVC(bpy.types.Operator):
    bl_idname = "object.generate_pvc"
    bl_label = "Generate PVC Frame"
    bl_description = "Generates the 3-section PVC pipe structure"

    def execute(self, context):
        props = context.scene.pvc_props
        CM = 0.01
        IN = 0.0254

        # Remove default cube and all previously generated objects
        cube = bpy.data.objects.get("Cube")
        if cube:
            bpy.data.objects.remove(cube, do_unlink=True)
        for obj in list(bpy.data.objects):
            if obj.name.startswith(("PVC_", "DIM_", "REF_")):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Resolve skeleton dimensions
        pipe_diam_cm = props.pipe_diameter * 2.54
        if props.use_advanced:
            l1_cm = props.l1; h1_cm = props.h1
            l2_cm = props.l2; h2_cm = props.h2
            l3_cm = props.l3; h3_cm = props.h3
        else:
            h2_cm = props.total_height - pipe_diam_cm
            h1_cm = h2_cm * (3.0 / 5.0)
            h3_cm = h2_cm * (2.0 / 5.0)
            l_tot = props.total_length - pipe_diam_cm
            l1_cm = l_tot * (4.0 / 9.0)
            l2_cm = l_tot * (2.0 / 9.0)
            l3_cm = l_tot * (3.0 / 9.0)

        w  = props.width * CM
        l1 = l1_cm * CM; h1 = h1_cm * CM
        l2 = l2_cm * CM; h2 = h2_cm * CM
        l3 = l3_cm * CM; h3 = h3_cm * CM
        pipe_r = (props.pipe_diameter * IN) / 2.0
        total_l = l1 + l2 + l3

        col = context.collection

        # Main model (grey)
        bm = bmesh.new()
        build_pvc_mesh(bm, w, l1, h1, l2, h2, l3, h3)
        main_curve = make_curve_from_bm(bm, "PVC_Curve", col, pipe_r)
        main_curve.data.materials.clear()
        main_curve.data.materials.append(make_material("PVC_Grey", (0.5, 0.5, 0.5, 1.0)))

        # Reference model (orange, scaled)
        scale = None
        scaled_h2_cm = None
        if props.correct_length > 0.0:
            total_l_cm = l1_cm + l2_cm + l3_cm
            scale = props.correct_length / total_l_cm
            scaled_h2_cm = h2_cm * scale
            sl1 = l1 * scale; sh1 = h1 * scale
            sl2 = l2 * scale; sh2 = h2 * scale
            sl3 = l3 * scale; sh3 = h3 * scale
            sw  = w  * scale; spr = pipe_r * scale

            bm2 = bmesh.new()
            build_pvc_mesh(bm2, sw, sl1, sh1, sl2, sh2, sl3, sh3)
            x_off = w + sw + pipe_r * 6
            for vert in bm2.verts:
                vert.co.x += x_off
            ref_curve = make_curve_from_bm(bm2, "REF_Curve", col, spr)
            ref_curve.data.materials.clear()
            ref_curve.data.materials.append(make_material("PVC_Orange", (1.0, 0.45, 0.05, 1.0)))

        # Dimension labels
        pipe_diam_cm = props.pipe_diameter * 2.54
        font_size = max(total_l, w, h1, h2, h3) * 0.06
        gap = font_size * 0.6
        side_gap = pipe_r + gap * 2.0
        front_gap = pipe_r + gap * 2.0
        cx = w / 2

        def label_rotation(direction, normal):
            x_axis = Vector(direction).normalized()
            z_axis = Vector(normal).normalized()
            if abs(x_axis.dot(z_axis)) > 0.98:
                z_axis = Vector((0, 0, 1))
            y_axis = z_axis.cross(x_axis).normalized()
            z_axis = x_axis.cross(y_axis).normalized()
            rot = Matrix((
                (x_axis.x, y_axis.x, z_axis.x),
                (x_axis.y, y_axis.y, z_axis.y),
                (x_axis.z, y_axis.z, z_axis.z),
            ))
            return rot.to_euler()

        def add_label(name, text, loc, direction=(1, 0, 0), normal=(0, -1, 0)):
            bpy.ops.object.text_add(location=loc)
            t = bpy.context.active_object
            t.name = name
            t.data.body = text
            t.data.size = font_size
            t.data.align_x = "CENTER"
            t.data.align_y = "CENTER"
            t.rotation_euler = label_rotation(direction, normal)
            t.select_set(False)

        length_label_x = w + side_gap
        length_label_z = pipe_r + gap
        add_label("DIM_L1", f"L1={l1_cm:.1f}cm", (length_label_x, l1 / 2,           length_label_z), (0, 1, 0), (0, 0, 1))
        add_label("DIM_L2", f"L2={l2_cm:.1f}cm", (length_label_x, l1 + l2 / 2,      length_label_z), (0, 1, 0), (0, 0, 1))
        add_label("DIM_L3", f"L3={l3_cm:.1f}cm", (length_label_x, l1 + l2 + l3 / 2, length_label_z), (0, 1, 0), (0, 0, 1))

        height_label_x = w + side_gap * 2.4
        add_label("DIM_H1", f"H1={h1_cm + pipe_diam_cm:.1f}cm", (height_label_x, l1 / 2,           h1 / 2), (0, 0, 1), (1, 0, 0))
        add_label("DIM_H2", f"H2={h2_cm + pipe_diam_cm:.1f}cm", (height_label_x, l1 + l2 / 2,      h2 / 2), (0, 0, 1), (1, 0, 0))
        add_label("DIM_H3", f"H3={h3_cm + pipe_diam_cm:.1f}cm", (height_label_x, l1 + l2 + l3 / 2, h3 / 2), (0, 0, 1), (1, 0, 0))

        add_label("DIM_TOTAL",
                  f"Total: {l1_cm + l2_cm + l3_cm + pipe_diam_cm:.1f}cm",
                  (cx, -front_gap * 2.2, pipe_r + gap),
                  (1, 0, 0),
                  (0, -1, 0))

        if scale is not None:
            ref_cx = x_off + sw / 2
            ref_top_z = max(sh1, sh2, sh3)
            add_label("REF_LABEL",
                      f"SCALED  x{scale:.4f}",
                      (ref_cx, (sl1 + sl2 + sl3) / 2, ref_top_z + gap * 3))
            ref_height_label_x = x_off + sw + side_gap * 2.4
            add_label("REF_H1", f"H1={sh1 / CM + pipe_diam_cm:.1f}cm", (ref_height_label_x, sl1 / 2,             sh1 / 2), (0, 0, 1), (1, 0, 0))
            add_label("REF_H2", f"H2={sh2 / CM + pipe_diam_cm:.1f}cm", (ref_height_label_x, sl1 + sl2 / 2,       sh2 / 2), (0, 0, 1), (1, 0, 0))
            add_label("REF_H3", f"H3={sh3 / CM + pipe_diam_cm:.1f}cm", (ref_height_label_x, sl1 + sl2 + sl3 / 2, sh3 / 2), (0, 0, 1), (1, 0, 0))
            add_label("DIM_SCALE",
                      f"Correct: {props.correct_length:.1f}cm  Scaled H2: {scaled_h2_cm + pipe_diam_cm:.2f}cm",
                      (ref_cx, (sl1 + sl2 + sl3) / 2, ref_top_z + gap * 5))

        # Zoom to main pipe
        bpy.ops.object.select_all(action="DESELECT")
        main_curve.select_set(True)
        context.view_layer.objects.active = main_curve
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        with bpy.context.temp_override(area=area, region=region):
                            bpy.ops.view3d.view_selected()
                        break

        self.report({"INFO"}, "PVC frame generated.")
        return {"FINISHED"}


# ==========================================
# 4. UI Panel
# ==========================================
class VIEW3D_PT_PVCPanel(bpy.types.Panel):
    bl_label = "PVC Generator"
    bl_idname = "VIEW3D_PT_pvc_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PVC Tool"

    def draw(self, context):
        layout = self.layout
        props = context.scene.pvc_props

        box = layout.box()
        box.label(text="Global Settings", icon="SETTINGS")
        box.prop(props, "pipe_diameter")
        box.prop(props, "width")
        layout.separator()

        box = layout.box()
        box.label(text="Dimensions  (outer edge)", icon="ARROW_LEFTRIGHT")
        box.prop(props, "total_height")
        box.prop(props, "total_length")
        layout.separator()

        layout.prop(props, "use_advanced")
        if props.use_advanced:
            box = layout.box()
            box.label(text="Advanced Overrides", icon="SETTINGS")
            box.prop(props, "l1"); box.prop(props, "h1")
            box.prop(props, "l2"); box.prop(props, "h2")
            box.prop(props, "l3"); box.prop(props, "h3")
            layout.separator()

        # Info readout
        pipe_diam_cm = props.pipe_diameter * 2.54
        if props.use_advanced:
            total_cm = props.l1 + props.l2 + props.l3
            h2_cm = props.h2
        else:
            l_tot = props.total_length - pipe_diam_cm
            total_cm = l_tot
            h2_cm = props.total_height - pipe_diam_cm

        info = layout.box()
        info.label(text="Info", icon="INFO")
        info.label(text=f"Total skeleton L:  {total_cm:.2f} cm")
        info.label(text=f"Skeleton H2:       {h2_cm:.2f} cm")
        layout.separator()

        ref = layout.box()
        ref.label(text="Judge Reference", icon="MODIFIER")
        ref.prop(props, "correct_length")
        if props.correct_length > 0.0 and total_cm > 0.0:
            s = props.correct_length / total_cm
            ref.label(text=f"Scale Factor:  {s:.4f}")
            ref.label(text=f"Scaled H2:     {h2_cm * s:.2f} cm")
            ref.label(text="Orange model placed beside main")
        layout.separator()

        layout.operator("object.generate_pvc", text="Generate / Update Frame", icon="MOD_WIREFRAME")


# ==========================================
# 5. Registration
# ==========================================
classes = (PVC_Properties, OBJECT_OT_GeneratePVC, VIEW3D_PT_PVCPanel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pvc_props = bpy.props.PointerProperty(type=PVC_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.pvc_props
