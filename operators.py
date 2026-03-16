import bpy

from .bake_utils import (
    cleanup_nodes,
    create_image,
    create_normal_image,
    do_bake,
    ensure_material,
    inject_bake_target,
    pin_source_uvs,
    restore_metallic_swap,
    set_active_uv,
    swap_metallic_to_emission,
    unpin_source_uvs,
)
from .material_builder import build_result_material


class MBAKER_OT_bake(bpy.types.Operator):
    bl_idname = "mbaker.bake"
    bl_label = "Bake Atlas"
    bl_description = (
        "Bake all materials of selected objects into a single atlas material"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mbaker_props
        objects = [o for o in context.selected_objects if o.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        uv_name = props.uv_map_name
        for obj in objects:
            if uv_name not in obj.data.uv_layers:
                self.report({"ERROR"}, f"UV map '{uv_name}' not found on '{obj.name}'")
                return {"CANCELLED"}

        resolution = int(props.resolution)
        mat_name = props.material_name

        original_engine = context.scene.render.engine
        original_samples = context.scene.cycles.samples
        context.scene.render.engine = "CYCLES"
        context.scene.cycles.samples = props.samples
        context.scene.cycles.device = "GPU"

        temp_materials = []
        for obj in objects:
            temp_materials.extend(ensure_material(obj))

        set_active_uv(objects, uv_name)

        pinned_uvs = pin_source_uvs(objects, uv_name)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        context.view_layer.objects.active = objects[0]

        passes_to_bake = []
        if props.bake_diffuse:
            passes_to_bake.append(("diffuse", "DIFFUSE", False))
        if props.bake_roughness:
            passes_to_bake.append(("roughness", "ROUGHNESS", True))
        if props.bake_normal:
            passes_to_bake.append(("normal", "NORMAL", True))
        if props.bake_emit:
            passes_to_bake.append(("emit", "EMIT", False))
        if props.bake_ao:
            passes_to_bake.append(("ao", "AO", True))
        if props.bake_metallic:
            passes_to_bake.append(("metallic", "_METALLIC", True))

        if not passes_to_bake:
            self.report({"WARNING"}, "No bake passes selected")
            context.scene.render.engine = original_engine
            context.scene.cycles.samples = original_samples
            return {"CANCELLED"}

        baked_images = {}
        background_color = tuple(props.background_color)

        for key, bake_type, is_data in passes_to_bake:
            img_name = f"{props.texture_name}_{key}"

            if key == "normal":
                img = create_normal_image(img_name, resolution)
            else:
                img = create_image(
                    img_name,
                    resolution,
                    is_data=is_data,
                    background_color=background_color,
                )

            nodes = inject_bake_target(objects, img)

            try:
                if bake_type == "_METALLIC":
                    rewire = swap_metallic_to_emission(objects)
                    cleanup_nodes(nodes)
                    nodes = inject_bake_target(objects, img)
                    try:
                        do_bake(context, "EMIT")
                    finally:
                        restore_metallic_swap(rewire)
                elif bake_type == "DIFFUSE":
                    do_bake(context, bake_type, use_color_only=True)
                else:
                    do_bake(context, bake_type)
            except RuntimeError as error:
                self.report({"ERROR"}, f"Bake failed for {key}: {error}")
                cleanup_nodes(nodes)
                unpin_source_uvs(pinned_uvs)
                context.scene.render.engine = original_engine
                context.scene.cycles.samples = original_samples
                return {"CANCELLED"}

            cleanup_nodes(nodes)
            baked_images[key] = img
            self.report({"INFO"}, f"Baked: {key}")

        unpin_source_uvs(pinned_uvs)

        new_mat = build_result_material(mat_name, uv_name, baked_images)

        for mat in temp_materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)

        context.scene.render.engine = original_engine
        context.scene.cycles.samples = original_samples

        self.report(
            {"INFO"},
            f"Done — created material '{mat_name}' with {len(baked_images)} maps. Use Cleanup to assign it.",
        )
        return {"FINISHED"}


class MBAKER_OT_create_uv(bpy.types.Operator):
    bl_idname = "mbaker.create_uv"
    bl_label = "Create Atlas UV"
    bl_description = (
        "Add the atlas UV map to all selected mesh objects and set it active"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mbaker_props
        uv_name = props.uv_map_name
        objects = [o for o in context.selected_objects if o.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        created_count = 0
        skipped_count = 0

        for obj in objects:
            if uv_name not in obj.data.uv_layers:
                obj.data.uv_layers.new(name=uv_name)
                created_count += 1
            else:
                skipped_count += 1

            uv = obj.data.uv_layers.get(uv_name)
            if uv:
                obj.data.uv_layers.active = uv

        self.report(
            {"INFO"},
            f"Created '{uv_name}' on {created_count} objects (skipped {skipped_count}), set active on all",
        )
        return {"FINISHED"}


class MBAKER_OT_select_uv(bpy.types.Operator):
    bl_idname = "mbaker.select_uv"
    bl_label = "Select Atlas UV"
    bl_description = "Set the atlas UV map as active on all selected mesh objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mbaker_props
        uv_name = props.uv_map_name
        objects = [o for o in context.selected_objects if o.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        selected_count = 0
        missing_count = 0

        for obj in objects:
            uv = obj.data.uv_layers.get(uv_name)
            if uv:
                obj.data.uv_layers.active = uv
                selected_count += 1
            else:
                missing_count += 1

        if missing_count:
            self.report(
                {"WARNING"},
                f"Set active on {selected_count} objects, missing on {missing_count}",
            )
        else:
            self.report({"INFO"}, f"Set '{uv_name}' active on {selected_count} objects")
        return {"FINISHED"}


class MBAKER_OT_cleanup(bpy.types.Operator):
    bl_idname = "mbaker.cleanup"
    bl_label = "Cleanup"
    bl_description = "Remove all UV maps except the atlas and all materials except the baked one on selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mbaker_props
        uv_name = props.uv_map_name
        mat_name = props.material_name
        objects = [o for o in context.selected_objects if o.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        baked_mat = bpy.data.materials.get(mat_name)
        if baked_mat is None:
            self.report({"ERROR"}, f"Material '{mat_name}' not found — bake first")
            return {"CANCELLED"}

        removed_uv = 0
        removed_mat = 0

        for obj in objects:
            to_remove = [uv for uv in obj.data.uv_layers if uv.name != uv_name]
            for uv in to_remove:
                obj.data.uv_layers.remove(uv)
                removed_uv += 1

            old_count = len(obj.data.materials)
            obj.data.materials.clear()
            obj.data.materials.append(baked_mat)
            removed_mat += max(0, old_count - 1)

        orphans = [m for m in bpy.data.materials if m.users == 0]
        for m in orphans:
            bpy.data.materials.remove(m)

        self.report(
            {"INFO"},
            f"Removed {removed_uv} UV maps, {removed_mat} material slots, {len(orphans)} orphan materials",
        )
        return {"FINISHED"}
