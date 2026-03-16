import bpy


class MBAKER_PT_panel(bpy.types.Panel):
    bl_label = "Material Baker"
    bl_idname = "MBAKER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Baker"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mbaker_props

        layout.use_property_split = True
        layout.use_property_decorate = False

        box = layout.box()
        box.label(text="Target", icon="UV")
        row = box.row(align=True)
        row.prop(props, "uv_map_name", text="UV Map")
        row.operator("mbaker.create_uv", text="", icon="ADD")
        row.operator("mbaker.select_uv", text="", icon="RESTRICT_SELECT_OFF")
        box.prop(props, "material_name")
        box.prop(props, "texture_name")
        box.prop(props, "resolution")

        box = layout.box()
        box.label(text="Bake Passes", icon="RENDERLAYERS")
        col = box.column(align=True)
        col.use_property_split = False
        row = col.row(align=True)
        row.scale_y = 1.2
        row.prop(props, "bake_diffuse", toggle=True)
        row.prop(props, "bake_normal", toggle=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.prop(props, "bake_roughness", toggle=True)
        row.prop(props, "bake_emit", toggle=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.prop(props, "bake_metallic", toggle=True)
        row.prop(props, "bake_ao", toggle=True)

        box = layout.box()
        box.label(text="Quality", icon="SCENE")
        box.prop(props, "samples")
        box.prop(props, "margin")
        box.prop(props, "background_color")
        box.prop(props, "force_rest_pose")

        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mbaker.bake", icon="RENDER_STILL")

        row = layout.row(align=True)
        row.operator("mbaker.cleanup", icon="TRASH")
        row.prop(props, "auto_cleanup", text="", icon="FILE_REFRESH", toggle=True)

        sel_count = sum(1 for o in context.selected_objects if o.type == "MESH")
        layout.label(text=f"Selected meshes: {sel_count}", icon="INFO")

        if sel_count >= 2:
            scales = []
            for o in context.selected_objects:
                if o.type == "MESH":
                    s = o.scale
                    scales.append((abs(s.x) + abs(s.y) + abs(s.z)) / 3.0)

            min_s = min(scales)
            max_s = max(scales)
            if min_s > 1e-6 and max_s / min_s > 1.05:
                box = layout.box()
                box.label(text="Inconsistent scale!", icon="ERROR")
                col = box.column(align=True)
                col.use_property_split = False
                col.scale_y = 0.8
                col.label(text="UV islands may bake at wrong size.")
                col.label(text="Apply scale first: Ctrl+A → Scale")
