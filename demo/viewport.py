"""Window + fullscreen layer for the SecondReality demo.

This module only owns the window: a size that fits the desktop, resize
handling, F11 / Alt+Enter fullscreen and ESC to leave fullscreen. The world
is still drawn 1:1 into its own 1920x1920 canvas; the renderer (virtual_world)
scales that canvas to the map viewport (wheel zoom, fit-to-view default) and
pans a camera, so small windows show the whole island instead of a squeezed
crop. Panel / stat-bar widths adapt to the window in the renderer's relayout.

Env vars:
  SRDEMO_WINDOW=1400x900   force the initial windowed size
  SRDEMO_FULLSCREEN=1      start fullscreen
  SRDEMO_MARGIN=0.92       fraction of the desktop the window may occupy
"""

import os

import os as _os_dpi
_os_dpi.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS","permonitorv2")   # 高DPI 物理像素渲染，避免系统拉伸模糊
import pygame

BG = (8, 10, 16)
MAX_SIZE = (2270, 2160)   # world canvas + panel + stat bar: nothing more to show
MIN_SIZE = (960, 600)


def _desktop_size():
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and sizes[0][0] > 0 and sizes[0][1] > 0:
            return int(sizes[0][0]), int(sizes[0][1])
    except Exception:
        pass
    try:
        info = pygame.display.Info()
        if info.current_w and info.current_h:
            return int(info.current_w), int(info.current_h)
    except Exception:
        pass
    return 1280, 720


def parse_size(text):
    """'1400x900' / '1400*900' -> (1400, 900); anything unusable -> None."""
    if not text:
        return None
    try:
        w, h = str(text).lower().replace("*", "x").split("x")
        w, h = int(w), int(h)
    except Exception:
        return None
    if w < 320 or h < 240:
        return None
    return w, h


def fit_size(desktop, margin=0.92):
    """Window size: 92% of the desktop, clamped to what the layout can use."""
    w = min(MAX_SIZE[0], max(MIN_SIZE[0], int(desktop[0] * margin)))
    h = min(MAX_SIZE[1], max(MIN_SIZE[1], int(desktop[1] * margin)))
    return int(w), int(h)


class Display(object):
    def __init__(self, caption="", fullscreen=False, margin=None):
        if margin is None:
            try:
                margin = float(os.environ.get("SRDEMO_MARGIN") or 0.92)
            except Exception:
                margin = 0.92
        size = parse_size(os.environ.get("SRDEMO_WINDOW")) or fit_size(_desktop_size(), margin)
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        if caption:
            pygame.display.set_caption(caption)
        self.fullscreen = False
        self._windowed = self.screen.get_size()
        if fullscreen or os.environ.get("SRDEMO_FULLSCREEN") == "1":
            self.set_fullscreen(True)

    @property
    def size(self):
        return self.screen.get_size()

    def set_fullscreen(self, on):
        if bool(on) == self.fullscreen:
            return
        if on:
            self._windowed = self.screen.get_size()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self._windowed, pygame.RESIZABLE)
        self.fullscreen = bool(on)

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.fullscreen)

    def handle_event(self, ev, allow_esc=True):
        """True means the window layer consumed the event."""
        if ev.type == pygame.QUIT:
            return True
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F11:
                self.toggle_fullscreen()
                return True
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and (
                getattr(ev, "mod", 0) & pygame.KMOD_ALT
            ):
                self.toggle_fullscreen()
                return True
            if ev.key == pygame.K_ESCAPE and self.fullscreen and allow_esc:
                self.set_fullscreen(False)
                return True
        return False

    def present(self):
        pygame.display.flip()
