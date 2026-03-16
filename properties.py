import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)


class MBAKER_Properties(bpy.types.PropertyGroup):
    uv_map_name: StringProperty(
        name="Target UV Map",
        description="Name of the shared UV map present on all selected objects",
        default="UVMapBaked",
    )
    resolution: EnumProperty(
        name="Resolution",
        items=[
            ("512", "512", ""),
            ("1024", "1024", ""),
            ("2048", "2048", ""),
            ("4096", "4096", ""),
            ("8192", "8192", ""),
        ],
        default="2048",
    )
    material_name: StringProperty(
        name="Material Name",
        description="Name for the resulting baked material",
        default="M_Baked",
    )
    texture_name: StringProperty(
        name="Texture Name",
        description="Base name for baked textures (suffixes like _diffuse, _normal appended automatically)",
        default="T_Baked",
    )
    samples: IntProperty(
        name="Samples",
        description="Cycles bake samples (lower = faster, noisier)",
        default=32,
        min=1,
        max=4096,
    )
    margin: IntProperty(
        name="Margin (px)",
        description="Pixel margin around UV islands to prevent seam bleeding",
        default=16,
        min=0,
        max=256,
    )

    bake_diffuse: BoolProperty(name="Base Color", default=True)
    bake_roughness: BoolProperty(name="Roughness", default=True)
    bake_metallic: BoolProperty(name="Metallic", default=False)
    bake_normal: BoolProperty(name="Normal", default=True)
    bake_emit: BoolProperty(name="Emission", default=False)
    bake_ao: BoolProperty(name="AO", default=False)

    background_color: FloatVectorProperty(
        name="Background",
        description="Background fill color for baked textures",
        subtype="COLOR",
        default=(0.0, 0.0, 0.0),
        min=0.0,
        max=1.0,
        size=3,
    )
