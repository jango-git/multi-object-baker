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

        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mbaker.bake", icon="RENDER_STILL")

        row = layout.row(align=True)
        row.operator("mbaker.cleanup", icon="TRASH")

        sel_count = sum(1 for o in context.selected_objects if o.type == "MESH")
        layout.label(text=f"Selected meshes: {sel_count}", icon="INFO")
