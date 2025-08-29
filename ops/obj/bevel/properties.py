import bpy


class Theme(bpy.types.PropertyGroup):
    guide: bpy.props.FloatVectorProperty(
        name="Bevel Guid", 
        description="Color of the guide line", 
        size=4, 
        subtype='COLOR', 
        default=(0.0, 0.0, 0.0, 0.8), 
        min=0.0, 
        max=1.0
    )


class SceneBase(bpy.types.PropertyGroup):
    '''Base scene properties for bevel operators'''
    segments: bpy.props.IntProperty(name='Segments', default=1, min=1, max=32)
    harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=False)
    angle_limit: bpy.props.FloatProperty(
        name='Angle', 
        default=0.523599, 
        min=0, 
        max=3.14159, 
        precision=4,
        step=10,
        subtype='ANGLE',
        description='Angle limit for beveling'
    )


class ScenePinned(bpy.types.PropertyGroup):
    '''Scene properties for pinned bevel operator'''
    segments: bpy.props.IntProperty(name='Segments', default=1, min=1, max=32)
    harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=True)
    angle_limit: bpy.props.FloatProperty(
        name='Angle', 
        default=0.523599, 
        min=0, 
        max=3.14159, 
        precision=4,
        step=10,
        subtype='ANGLE',
        description='Angle limit for beveling'
    )


class Scene(bpy.types.PropertyGroup):
    '''Scene properties container for all bevel operators'''
    base: bpy.props.PointerProperty(type=SceneBase)
    pinned: bpy.props.PointerProperty(type=ScenePinned)