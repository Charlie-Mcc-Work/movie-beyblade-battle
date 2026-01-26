#!/usr/bin/env python3
"""
Web server wrapper for Movie Beyblade Battle.
Streams the pygame display to web browsers and handles input from them.
"""

import os
import sys
import io
import base64
import time
import threading

# Must set SDL environment BEFORE importing pygame
if sys.platform.startswith('linux'):
    if not os.environ.get('DISPLAY'):
        print("Warning: No DISPLAY set. Run with 'xvfb-run -a python web_server.py'")

import pygame
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from src.game import Game
from src.constants import WINDOW_WIDTH, WINDOW_HEIGHT

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'beyblade-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
game = None
web_mouse_pos = [WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2]

# Store original pygame.mouse.get_pos
_original_get_pos = pygame.mouse.get_pos

def _patched_get_pos():
    """Return web client mouse position."""
    return tuple(web_mouse_pos)


def frame_to_base64(surface):
    """Convert pygame surface to base64 JPEG."""
    try:
        from PIL import Image
        data = pygame.image.tobytes(surface, 'RGB')
        img = Image.frombytes('RGB', surface.get_size(), data)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=70)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Frame conversion failed: {e}")
        return None


# Frame rate limiting
last_frame_time = 0
STREAM_FPS = 30

def on_frame(surface):
    """Callback called after each frame is drawn."""
    global last_frame_time

    current_time = time.time()
    if current_time - last_frame_time < 1.0 / STREAM_FPS:
        return
    last_frame_time = current_time

    frame_data = frame_to_base64(surface)
    if frame_data:
        socketio.emit('frame', {'data': frame_data})


def run_game():
    """Run the game loop."""
    global game

    # Patch mouse.get_pos for web mode
    pygame.mouse.get_pos = _patched_get_pos

    game = Game(web_mode=True)
    game.frame_callback = on_frame
    game.run()


# Flask routes
@app.route('/')
def index():
    print("[WEB] Serving index page")
    return render_template('index.html', width=WINDOW_WIDTH, height=WINDOW_HEIGHT)


@app.route('/test')
def test():
    return f"Server OK. Game ready: {game is not None}"


# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print(f"[WEB] Client connected")
    emit('status', {'msg': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    print(f"[WEB] Client disconnected")


@socketio.on('mouse')
def handle_mouse(data):
    global web_mouse_pos

    if not game:
        return

    x = data.get('x', 0)
    y = data.get('y', 0)
    web_mouse_pos[0] = x
    web_mouse_pos[1] = y
    game._web_mouse_pos = (x, y)

    event_type = data.get('type')
    if event_type == 'mousedown':
        print(f"[WEB] Click at ({x}, {y})")
        game.inject_event({
            'type': 'mousedown',
            'button': data.get('button', 1),
            'x': x,
            'y': y
        })
    elif event_type == 'mouseup':
        game.inject_event({
            'type': 'mouseup',
            'button': data.get('button', 1),
            'x': x,
            'y': y
        })


@socketio.on('key')
def handle_key(data):
    if not game:
        return

    js_key = data.get('jsKey', '')

    # Skip Ctrl+V
    if js_key.lower() == 'v' and data.get('ctrl'):
        return

    # Key mapping
    key_map = {
        'Backspace': pygame.K_BACKSPACE,
        'Delete': pygame.K_DELETE,
        'Enter': pygame.K_RETURN,
        'ArrowUp': pygame.K_UP,
        'ArrowDown': pygame.K_DOWN,
        'ArrowLeft': pygame.K_LEFT,
        'ArrowRight': pygame.K_RIGHT,
        'Home': pygame.K_HOME,
        'End': pygame.K_END,
        'Tab': pygame.K_TAB,
        'Escape': pygame.K_ESCAPE,
        ' ': pygame.K_SPACE,
    }

    if js_key in key_map:
        pygame_key = key_map[js_key]
    elif len(js_key) == 1:
        pygame_key = ord(js_key.lower())
    else:
        pygame_key = 0

    mod = 0
    if data.get('ctrl'): mod |= pygame.KMOD_CTRL
    if data.get('shift'): mod |= pygame.KMOD_SHIFT
    if data.get('alt'): mod |= pygame.KMOD_ALT

    game.inject_event({
        'type': data.get('type', 'keydown'),
        'key': pygame_key,
        'mod': mod,
        'unicode': data.get('unicode', js_key if len(js_key) == 1 else '')
    })


@socketio.on('wheel')
def handle_wheel(data):
    if not game:
        return

    delta_y = data.get('deltaY', 0)
    scroll_y = -1 if delta_y > 0 else (1 if delta_y < 0 else 0)

    game.inject_event({
        'type': 'mousewheel',
        'x': 0,
        'y': scroll_y
    })


@socketio.on('paste')
def handle_paste(data):
    if not game:
        return

    text = data.get('text', '')
    for char in text:
        if char == '\n':
            game.inject_event({
                'type': 'keydown',
                'key': pygame.K_RETURN,
                'mod': 0,
                'unicode': '\n'
            })
        elif char.isprintable():
            game.inject_event({
                'type': 'keydown',
                'key': ord(char.lower()) if char.isalpha() else ord(char),
                'mod': pygame.KMOD_SHIFT if char.isupper() else 0,
                'unicode': char
            })


def main():
    global game

    PORT = 8080

    print("\n" + "=" * 50)
    print("  Movie Beyblade Battle - Web Server")
    print("=" * 50)
    print(f"\n  Open in browser: http://localhost:{PORT}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    # Start game thread
    print("[SERVER] Starting game thread...")
    game_thread = threading.Thread(target=run_game, daemon=True)
    game_thread.start()

    # Wait for game to initialize
    time.sleep(1)
    print(f"[SERVER] Game initialized: {game is not None}")

    # Start Flask server
    print(f"[SERVER] Starting web server on port {PORT}...")
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
