import bpy

PASS_TO_INPUT = {
    "diffuse": ("Base Color", False),
    "roughness": ("Roughness", True),
    "metallic": ("Metallic", True),
    "normal": ("Normal", True),
    "emit": ("Emission Color", False),
    "ao": (None, True),
}


def build_result_material(name, uv_map_name, images):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)

    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    uv_node = tree.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_map_name
    uv_node.location = (-900, 0)

    x_offset = -600
    y_offset = 300
    diffuse_tex_node = None

    for key, img in images.items():
        input_name, is_data = PASS_TO_INPUT.get(key, (None, False))

        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (x_offset, y_offset)
        tree.links.new(uv_node.outputs["UV"], tex.inputs["Vector"])

        if key == "diffuse":
            diffuse_tex_node = tex

        if key == "normal":
            normal_map = tree.nodes.new("ShaderNodeNormalMap")
            normal_map.uv_map = uv_map_name
            normal_map.location = (x_offset + 300, y_offset)
            tree.links.new(tex.outputs["Color"], normal_map.inputs["Color"])
            tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

        elif key == "ao" and diffuse_tex_node is not None:
            mix = tree.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.location = (x_offset + 300, y_offset)
            tree.links.new(diffuse_tex_node.outputs["Color"], mix.inputs[6])
            tree.links.new(tex.outputs["Color"], mix.inputs[7])
            tree.links.new(mix.outputs[2], bsdf.inputs["Base Color"])

        elif key == "emit":
            inp = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            if inp:
                tree.links.new(tex.outputs["Color"], inp)
            emission_strength = bsdf.inputs.get("Emission Strength")
            if emission_strength:
                emission_strength.default_value = 1.0

        elif input_name and input_name in bsdf.inputs:
            tree.links.new(tex.outputs["Color"], bsdf.inputs[input_name])

        y_offset -= 300

    return mat
