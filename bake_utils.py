import bpy

TEMP_NODE_NAME = "__mbaker_target__"
TEMP_UV_NODE_NAME = "__mbaker_source_uv__"


def ensure_material(obj):
    if not obj.data.materials:
        mat = bpy.data.materials.new(name=f"_mbaker_default_{obj.name}")
        mat.use_nodes = True
        obj.data.materials.append(mat)
        return [mat]
    return []


def get_source_uv_name(obj, atlas_uv_name):
    layers = obj.data.uv_layers
    if not layers:
        return None

    for uv in layers:
        if uv.active_render and uv.name != atlas_uv_name:
            return uv.name

    for uv in layers:
        if uv.name != atlas_uv_name:
            return uv.name

    return None


def set_active_uv(objects, atlas_uv_name):
    for obj in objects:
        uv = obj.data.uv_layers.get(atlas_uv_name)
        if uv:
            uv.active = True


_NODES_WITH_VECTOR_INPUT = {
    "ShaderNodeTexImage",
    "ShaderNodeTexEnvironment",
    "ShaderNodeTexNoise",
    "ShaderNodeTexVoronoi",
    "ShaderNodeTexWave",
    "ShaderNodeTexMusgrave",
    "ShaderNodeTexGradient",
    "ShaderNodeTexMagic",
    "ShaderNodeTexChecker",
    "ShaderNodeTexBrick",
}


def create_image(name, resolution, is_data=False, background_color=(0.0, 0.0, 0.0)):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])

    img = bpy.data.images.new(
        name, resolution, resolution, alpha=False, float_buffer=False
    )
    img.colorspace_settings.name = "Non-Color" if is_data else "sRGB"

    r, g, b = background_color
    if is_data:
        r, g, b = 0.5, 0.5, 1.0

    pixels = list(img.pixels)
    for i in range(0, len(pixels), 4):
        pixels[i] = r
        pixels[i + 1] = g
        pixels[i + 2] = b
        pixels[i + 3] = 1.0
    img.pixels[:] = pixels
    return img


def create_normal_image(name, resolution):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])

    img = bpy.data.images.new(
        name, resolution, resolution, alpha=False, float_buffer=False
    )
    img.colorspace_settings.name = "Non-Color"

    pixels = list(img.pixels)
    for i in range(0, len(pixels), 4):
        pixels[i] = 0.5
        pixels[i + 1] = 0.5
        pixels[i + 2] = 1.0
        pixels[i + 3] = 1.0
    img.pixels[:] = pixels
    return img


def pin_source_uvs(objects, atlas_uv_name):
    pinned = []
    processed_materials = set()

    for obj in objects:
        source_uv = get_source_uv_name(obj, atlas_uv_name)
        if source_uv is None:
            continue

        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or not mat.use_nodes:
                continue
            if mat.name in processed_materials:
                continue
            processed_materials.add(mat.name)

            tree = mat.node_tree
            uv_node = None

            for node in tree.nodes:
                if node.bl_idname not in _NODES_WITH_VECTOR_INPUT:
                    continue

                vector_input = node.inputs.get("Vector")
                if vector_input is None:
                    continue
                if vector_input.is_linked:
                    continue

                if uv_node is None:
                    uv_node = tree.nodes.new("ShaderNodeUVMap")
                    uv_node.name = TEMP_UV_NODE_NAME
                    uv_node.label = TEMP_UV_NODE_NAME
                    uv_node.uv_map = source_uv
                    uv_node.location = (-800, 600)
                    pinned.append((tree, uv_node))

                tree.links.new(uv_node.outputs["UV"], vector_input)

    return pinned


def unpin_source_uvs(pinned):
    for tree, uv_node in pinned:
        try:
            tree.nodes.remove(uv_node)
        except Exception:
            pass


def inject_bake_target(objects, image):
    created = []
    for obj in objects:
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or not mat.use_nodes:
                continue
            tree = mat.node_tree

            for node in tree.nodes:
                node.select = False

            node = tree.nodes.new("ShaderNodeTexImage")
            node.name = TEMP_NODE_NAME
            node.label = TEMP_NODE_NAME
            node.image = image
            node.select = True
            tree.nodes.active = node
            created.append((tree, node))
    return created


def cleanup_nodes(entries):
    for tree, node in entries:
        try:
            tree.nodes.remove(node)
        except Exception:
            pass


def do_bake(context, bake_type, use_color_only=False):
    bake = context.scene.render.bake
    bake.use_selected_to_active = False
    bake.use_clear = False
    bake.margin = context.scene.mbaker_props.margin

    if bake_type == "DIFFUSE":
        bake.use_pass_direct = not use_color_only
        bake.use_pass_indirect = not use_color_only
        bake.use_pass_color = True

    bpy.ops.object.bake(type=bake_type)


def swap_metallic_to_emission(objects):
    rewire_data = []
    for obj in objects:
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or not mat.use_nodes:
                continue
            tree = mat.node_tree

            principled = None
            for n in tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    principled = n
                    break
            if principled is None:
                continue

            metallic_input = principled.inputs.get("Metallic")
            emission_input = principled.inputs.get(
                "Emission Color"
            ) or principled.inputs.get("Emission")
            if metallic_input is None or emission_input is None:
                continue

            old_emission_links = [
                (link.from_socket, link.to_socket)
                for link in tree.links
                if link.to_socket == emission_input
            ]

            for link in list(tree.links):
                if link.to_socket == emission_input:
                    tree.links.remove(link)

            metallic_links = [
                link for link in tree.links if link.to_socket == metallic_input
            ]
            if metallic_links:
                src_socket = metallic_links[0].from_socket
                tree.links.new(src_socket, emission_input)
                rewire_data.append(
                    (
                        tree,
                        emission_input,
                        metallic_input,
                        old_emission_links,
                        src_socket,
                        True,
                    )
                )
            else:
                val_node = tree.nodes.new("ShaderNodeValue")
                val_node.name = "__mbaker_metal_val__"
                val_node.outputs[0].default_value = metallic_input.default_value
                tree.links.new(val_node.outputs[0], emission_input)
                rewire_data.append(
                    (
                        tree,
                        emission_input,
                        metallic_input,
                        old_emission_links,
                        val_node,
                        False,
                    )
                )

            emission_strength = principled.inputs.get("Emission Strength")
            if emission_strength:
                rewire_data.append(
                    ("strength", principled, emission_strength.default_value)
                )
                emission_strength.default_value = 1.0

    return rewire_data


def restore_metallic_swap(rewire_data):
    for entry in rewire_data:
        if entry[0] == "strength":
            _, principled, old_val = entry
            emission_strength = principled.inputs.get("Emission Strength")
            if emission_strength:
                emission_strength.default_value = old_val
            continue

        tree, emission_input, metallic_input, old_emission_links, src, is_link = entry
        for link in list(tree.links):
            if link.to_socket == emission_input:
                tree.links.remove(link)
        if not is_link:
            try:
                tree.nodes.remove(src)
            except Exception:
                pass
        for from_sock, to_sock in old_emission_links:
            try:
                tree.links.new(from_sock, to_sock)
            except Exception:
                pass
