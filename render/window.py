"""Window and OpenGL rendering setup."""

import numpy as np
from pathlib import Path

try:
    import moderngl
    import moderngl_window as mglw
    from moderngl_window.conf import settings
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False
    moderngl = None
    mglw = None


VERTEX_SHADER = """
#version 330 core

in vec2 in_position;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""


def run_game(runtime):
    """Run the game with the given runtime."""
    if not HAS_MODERNGL:
        raise ImportError("moderngl and moderngl_window required. Install with: pip install moderngl moderngl-window pyglet")

    # Store runtime in closure
    _runtime = runtime

    class GameWindow(mglw.WindowConfig):
        """Main game window."""

        title = "Blitz Shooter"
        window_size = (800, 600)
        aspect_ratio = None
        resizable = False

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

            self.runtime = _runtime

            # Load fragment shader
            shader_path = Path(__file__).parent / "shader.glsl"
            fragment_shader = shader_path.read_text()

            # Create shader program
            self.prog = self.ctx.program(
                vertex_shader=VERTEX_SHADER,
                fragment_shader=fragment_shader,
            )

            # Fullscreen quad
            vertices = np.array([
                -1.0, -1.0,
                 1.0, -1.0,
                -1.0,  1.0,
                 1.0,  1.0,
            ], dtype='f4')

            self.vbo = self.ctx.buffer(vertices)
            self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_position')

            # Entity data texture (512 x 1, RGBA32F)
            self.entity_texture = self.ctx.texture((512, 1), 4, dtype='f4')
            self.entity_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

            # Get uniform locations
            self.uniforms = {}
            for name in ['u_resolution', 'u_time', 'u_player_pos', 'u_score',
                         'u_lives', 'u_entity_count', 'u_entities']:
                if name in self.prog:
                    self.uniforms[name] = self.prog[name]

            # Bind entity texture to texture unit 0
            if 'u_entities' in self.uniforms:
                self.uniforms['u_entities'].value = 0

        def on_render(self, time: float, frametime: float):
            """Render a frame."""
            if self.runtime:
                # Update game
                self.runtime.update(frametime)

                # Get uniform values
                uniforms = self.runtime.get_render_uniforms()

                # Calculate scale factor for Retina/HiDPI displays
                buffer_size = self.wnd.buffer_size
                window_size = self.wnd.size
                scale_x = buffer_size[0] / window_size[0]
                scale_y = buffer_size[1] / window_size[1]

                # Update uniforms - use actual framebuffer size for resolution
                if 'u_resolution' in self.uniforms:
                    self.uniforms['u_resolution'].value = buffer_size
                if 'u_time' in self.uniforms:
                    self.uniforms['u_time'].value = uniforms['u_time']
                if 'u_player_pos' in self.uniforms:
                    # Scale player position to framebuffer coordinates
                    px, py = uniforms['u_player_pos']
                    self.uniforms['u_player_pos'].value = (px * scale_x, py * scale_y)
                if 'u_score' in self.uniforms:
                    self.uniforms['u_score'].value = uniforms['u_score']
                if 'u_lives' in self.uniforms:
                    self.uniforms['u_lives'].value = uniforms['u_lives']
                if 'u_entity_count' in self.uniforms:
                    self.uniforms['u_entity_count'].value = uniforms['u_entity_count']

                # Update entity texture - scale positions for HiDPI
                entity_data = self.runtime.get_entity_data().copy()
                # Scale x and y positions (columns 0 and 1)
                entity_data[:, 0] *= scale_x
                entity_data[:, 1] *= scale_y
                self.entity_texture.write(entity_data.tobytes())
                self.entity_texture.use(0)

            # Clear and render
            self.ctx.clear(0.0, 0.0, 0.0)
            self.vao.render(moderngl.TRIANGLE_STRIP)

        def on_key_event(self, key, action, modifiers):
            """Handle key events."""
            if not self.runtime:
                return

            # Map keys
            key_map = {
                self.wnd.keys.LEFT: 'left',
                self.wnd.keys.RIGHT: 'right',
                self.wnd.keys.UP: 'up',
                self.wnd.keys.DOWN: 'down',
                self.wnd.keys.SPACE: 'fire',
                self.wnd.keys.Z: 'fire',
            }

            if key in key_map:
                key_name = key_map[key]
                if action == self.wnd.keys.ACTION_PRESS:
                    self.runtime.key_down(key_name)
                elif action == self.wnd.keys.ACTION_RELEASE:
                    self.runtime.key_up(key_name)

            # Escape to quit
            if key == self.wnd.keys.ESCAPE and action == self.wnd.keys.ACTION_PRESS:
                self.wnd.close()

    # Configure settings
    settings.WINDOW['class'] = 'moderngl_window.context.pyglet.Window'
    settings.WINDOW['size'] = GameWindow.window_size
    settings.WINDOW['title'] = GameWindow.title

    # Run
    mglw.run_window_config(GameWindow, args=['--window', 'pyglet'])
