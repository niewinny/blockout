import os
import bpy
import gpu

from gpu_extras.batch import batch_for_shader


# Shader Creation Info
shader_info = gpu.types.GPUShaderCreateInfo()
shader_info.push_constant('FLOAT', "lineSize")
shader_info.push_constant('VEC2', "viewportSize")

shader_info.vertex_in(0, 'VEC2', "pos")
shader_info.vertex_in(1, 'VEC4', "color")
shader_info.vertex_in(2, 'FLOAT', "lineLength")

shader_info.fragment_out(0, 'VEC4', "FragColor")

vertex_out = gpu.types.GPUStageInterfaceInfo('v_out')

vertex_out.smooth('VEC4', 'v_Color')
vertex_out.smooth('VEC2', 'v_Pos')
vertex_out.smooth('FLOAT', 'v_Length')

shader_info.vertex_out(vertex_out)

current_script_directory = os.path.dirname(os.path.realpath(__file__))

vertex_shader_path = os.path.join(current_script_directory, "dotted.vert")
fragment_shader_path = os.path.join(current_script_directory, "dotted.frag")

with open(vertex_shader_path, "r", encoding="utf-8") as f:
    vertex_shader_source = f.read()

with open(fragment_shader_path, "r", encoding="utf-8") as f:
    fragment_shader_source = f.read()

shader_info.vertex_source(vertex_shader_source)
shader_info.fragment_source(fragment_shader_source)
