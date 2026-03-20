#!/usr/bin/env python3
"""Sidebar control script for kitty — toggle and new-tab-with-sidebar.

Runs as plain python3 (no kitty modules needed). Uses `kitty @` remote
control to inspect and manipulate windows.
"""
import glob
import json
import os
import subprocess
import sys

_SIDEBAR_LAUNCH_CMD = (
    "exec(open(__import__('os').path.expanduser("
    "'~/.config/kitty/sidebar.py')).read(), globals())"
)


def _get_kitty_socket() -> str | None:
    """Find the kitty remote control socket.

    Kitty appends the PID to the socket path (e.g. /tmp/kitty.sock-95300).
    In normal windows KITTY_LISTEN_ON is set; in background processes it
    isn't, so we fall back to finding the most recent socket file.
    """
    sock = os.environ.get('KITTY_LISTEN_ON')
    if sock:
        return sock
    sockets = sorted(
        glob.glob('/tmp/kitty.sock-*'),
        key=os.path.getmtime,
        reverse=True,
    )
    return f'unix:{sockets[0]}' if sockets else None


def _kitty_cmd(*args: str) -> subprocess.CompletedProcess:
    """Run a kitty @ remote control command with the correct socket."""
    sock = _get_kitty_socket()
    cmd = ['kitty', '@']
    if sock:
        cmd += ['--to', sock]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def _has_sidebar_in_focused_tab() -> int | None:
    """Return window ID of sidebar in focused tab, or None."""
    cp = _kitty_cmd('ls')
    if cp.returncode != 0:
        return None
    for os_win in json.loads(cp.stdout):
        for tab in os_win['tabs']:
            if tab['is_focused']:
                for win in tab['windows']:
                    if win['title'] == 'sidebar':
                        return win['id']
    return None


def _launch_sidebar() -> None:
    """Launch a sidebar window in the current tab."""
    _kitty_cmd(
        'launch', '--location=vsplit', '--bias=20',
        '--title', 'sidebar',
        'kitty', '+runpy', _SIDEBAR_LAUNCH_CMD,
    )


def toggle() -> None:
    """Close sidebar if it exists in current tab, otherwise open one."""
    sidebar_id = _has_sidebar_in_focused_tab()
    if sidebar_id is not None:
        _kitty_cmd('close-window', '--match', f'id:{sidebar_id}')
    else:
        _launch_sidebar()


def new_tab_with_sidebar() -> None:
    """Create a new tab and immediately open a sidebar in it."""
    _kitty_cmd('launch', '--type=tab')
    _launch_sidebar()


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'toggle'
    if action == 'toggle':
        toggle()
    elif action == 'new_tab':
        new_tab_with_sidebar()
