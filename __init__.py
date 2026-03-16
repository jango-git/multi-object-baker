bl_info = {
    "name": "Multi-Object Material Baker",
    "author": "",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Baker",
    "description": "Bake multiple materials from multiple objects onto a single atlas material",
    "category": "Material",
}

import bpy
from bpy.props import PointerProperty

from .operators import (
    MBAKER_OT_bake,
    MBAKER_OT_cleanup,
    MBAKER_OT_create_uv,
    MBAKER_OT_select_uv,
)
from .properties import MBAKER_Properties
from .ui import MBAKER_PT_panel

classes = (
    MBAKER_Properties,
    MBAKER_OT_bake,
    MBAKER_OT_create_uv,
    MBAKER_OT_select_uv,
    MBAKER_OT_cleanup,
    MBAKER_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mbaker_props = PointerProperty(type=MBAKER_Properties)


def unregister():
    del bpy.types.Scene.mbaker_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
