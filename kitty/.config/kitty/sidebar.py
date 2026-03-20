from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from kitty.fast_data_types import Color
from kittens.tui.handler import Handler, result_handler
from kittens.tui.loop import Loop

_SIDEBAR_LAUNCH_CMD = "exec(open(__import__('os').path.expanduser('~/.config/kitty/sidebar.py')).read(), globals())"

# Catppuccin Mocha colors
MAUVE = Color(203, 166, 247)       # #cba6f7
CRUST = Color(30, 30, 46)          # #1e1e2e
TEXT = Color(205, 214, 244)        # #cdd6f4
OVERLAY0 = Color(108, 112, 134)    # #6c7086

# Sidebar width constraints (columns)
SIDEBAR_MIN_COLS = 40
SIDEBAR_MAX_COLS = 60
SIDEBAR_RATIO = 0.20


class Tab:
    """Represents a kitty tab for display."""

    def __init__(self, tab_id: int, title: str, is_focused: bool, windows_count: int):
        self.tab_id = tab_id
        self.title = title
        self.is_focused = is_focused
        self.windows_count = windows_count


class SidebarHandler(Handler):
    use_alternate_screen = True

    def __init__(self, tabs: list[Tab], standalone: bool = False):
        super().__init__()
        self.tabs = tabs
        self.standalone = standalone
        self.selected = 0
        self.result: str = ''
        # Pre-select the currently focused tab
        for i, tab in enumerate(tabs):
            if tab.is_focused:
                self.selected = i
                break

    def initialize(self) -> None:
        self.cmd.set_cursor_visible(False)
        self.cmd.set_line_wrapping(True)
        if self.standalone:
            subprocess.run(['kitty', '@', 'action', '--self', 'move_window', 'left'], capture_output=True)
            # Resize sidebar: 20% of total width, clamped to [MIN, MAX]
            cols, total = self._get_window_geometry()
            if cols and total:
                target = max(SIDEBAR_MIN_COLS, min(SIDEBAR_MAX_COLS, int(total * SIDEBAR_RATIO)))
                if cols != target:
                    subprocess.run([
                        'kitty', '@', 'resize-window', '--self',
                        '--axis', 'horizontal', '--increment', str(target - cols)
                    ], capture_output=True)
        self.draw_screen()
        self._start_auto_refresh()

    def _get_window_geometry(self) -> tuple[int | None, int | None]:
        """Return (sidebar_cols, total_tab_cols) by querying kitty."""
        win_id = os.environ.get('KITTY_WINDOW_ID')
        if not win_id:
            return None, None
        cp = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True)
        if cp.returncode != 0:
            return None, None
        for os_win in json.loads(cp.stdout):
            for tab in os_win['tabs']:
                for win in tab['windows']:
                    if str(win['id']) == win_id:
                        sidebar_cols = win['columns']
                        total_cols = sum(w['columns'] for w in tab['windows'])
                        return sidebar_cols, total_cols
        return None, None

    def _start_auto_refresh(self) -> None:
        self._refresh_handle = self.asyncio_loop.call_later(2, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self._refresh_tabs()
        self._refresh_handle = self.asyncio_loop.call_later(2, self._auto_refresh)

    @Handler.atomic_update
    def draw_screen(self) -> None:
        self.cmd.clear_screen()
        self.cmd.set_cursor_position(0, 0)

        # Header
        self.print(self.cmd.styled(' Tabs ', bold=True, reverse=True))
        self.print('')

        # Tab list
        for i, tab in enumerate(self.tabs):
            is_selected = i == self.selected
            number = str(i + 1) if i < 9 else ' '
            focused_marker = '*' if tab.is_focused else ' '

            if is_selected:
                line = self.cmd.styled(
                    f' \u25b6 {number} {focused_marker} {tab.title} ',
                    fg=CRUST, bg=MAUVE, bold=True
                )
            else:
                line = self.cmd.styled(
                    f'   {number} {focused_marker} {tab.title} ',
                    fg=TEXT
                )
            self.print(line)

        # Footer
        self.print('')
        self.print(self.cmd.styled(
            ' [n]ew  [x]close  [q]uit ',
            fg=OVERLAY0
        ))

    def _has_sidebar_in_tab(self, tab_id: int) -> bool:
        """Check if a sidebar window already exists in the given tab."""
        cp = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True)
        if cp.returncode != 0:
            return False
        for os_win in json.loads(cp.stdout):
            for tab in os_win['tabs']:
                if tab['id'] == tab_id:
                    for win in tab['windows']:
                        if win['title'] == 'sidebar':
                            return True
        return False

    def _execute_action(self, action: dict) -> None:
        cmd = action['action']
        if cmd == 'focus_tab':
            subprocess.run(['kitty', '@', 'focus-tab', '--match', f'id:{action["tab_id"]}'], capture_output=True)
            # Only spawn sidebar if the target tab doesn't already have one
            if not self._has_sidebar_in_tab(action['tab_id']):
                subprocess.run([
                    'kitty', '@', 'launch', '--location=vsplit', '--bias=20', '--title', 'sidebar',
                    'kitty', '+runpy', _SIDEBAR_LAUNCH_CMD
                ], capture_output=True)
        elif cmd == 'close_tab':
            subprocess.run(['kitty', '@', 'close-tab', '--match', f'id:{action["tab_id"]}'], capture_output=True)
        elif cmd == 'new_tab':
            subprocess.run(['kitty', '@', 'launch', '--type=tab'], capture_output=True)

    def _perform_action(self, action: dict) -> None:
        if self.standalone:
            self._execute_action(action)
            if action['action'] == 'focus_tab':
                self.quit_loop(0)
            else:
                self._refresh_tabs()
        else:
            self.result = json.dumps(action)
            self.quit_loop(0)

    def _refresh_tabs(self) -> None:
        cp = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True)
        if cp.returncode == 0:
            self.tabs = parse_tabs(cp.stdout)
            if self.selected >= len(self.tabs):
                self.selected = max(0, len(self.tabs) - 1)
            self.draw_screen()

    def on_text(self, text: str, in_bracketed_paste: bool = False) -> None:
        self._refresh_tabs()
        if text == 'q':
            self.quit_loop(1)
        elif text == 'j':
            self._move_selection(1)
        elif text == 'k':
            self._move_selection(-1)
        elif text == 'n':
            self._perform_action({'action': 'new_tab'})
        elif text == 'x':
            if len(self.tabs) > 1:
                tab = self.tabs[self.selected]
                self._perform_action({'action': 'close_tab', 'tab_id': tab.tab_id})
        elif text.isdigit() and text != '0':
            idx = int(text) - 1
            if 0 <= idx < len(self.tabs):
                tab = self.tabs[idx]
                self._perform_action({'action': 'focus_tab', 'tab_id': tab.tab_id})

    def on_key(self, key_event: Any) -> None:
        self._refresh_tabs()
        if key_event.matches('escape'):
            self.quit_loop(1)
        elif key_event.matches('enter'):
            tab = self.tabs[self.selected]
            self._perform_action({'action': 'focus_tab', 'tab_id': tab.tab_id})
        elif key_event.matches('down'):
            self._move_selection(1)
        elif key_event.matches('up'):
            self._move_selection(-1)

    def on_interrupt(self) -> None:
        self.quit_loop(1)

    def on_eot(self) -> None:
        self.quit_loop(1)

    def on_resize(self, screen_size: Any) -> None:
        super().on_resize(screen_size)
        self.draw_screen()

    def _move_selection(self, delta: int) -> None:
        self.selected = (self.selected + delta) % len(self.tabs)
        self.draw_screen()


def parse_tabs(ls_output: str) -> list[Tab]:
    """Parse `kitty @ ls` JSON output into Tab objects."""
    data = json.loads(ls_output)
    tabs: list[Tab] = []
    for os_win in data:
        for tab_data in os_win['tabs']:
            tabs.append(Tab(
                tab_id=tab_data['id'],
                title=tab_data['title'],
                is_focused=tab_data['is_focused'],
                windows_count=len(tab_data['windows']),
            ))
    return tabs


def main(args: list[str]) -> str | None:
    cp = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True)
    if cp.returncode != 0:
        print(cp.stderr, file=sys.stderr)
        raise SystemExit(cp.returncode)

    tabs = parse_tabs(cp.stdout)
    if not tabs:
        return None

    loop = Loop()
    handler = SidebarHandler(tabs)
    loop.loop(handler)

    if loop.return_code == 0:
        return handler.result
    return None


@result_handler()
def handle_result(args: list[str], answer: str | None, target_window_id: int, boss: Any) -> None:
    if not answer:
        return

    action = json.loads(answer)
    cmd = action['action']

    if cmd == 'focus_tab':
        tab = boss.tab_for_id(action['tab_id'])
        if tab:
            boss.set_active_tab(tab)

    elif cmd == 'close_tab':
        tab = boss.tab_for_id(action['tab_id'])
        if tab:
            boss.close_tab(tab)

    elif cmd == 'new_tab':
        boss.new_tab()


def run_standalone() -> None:
    cp = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True)
    if cp.returncode != 0:
        print(cp.stderr, file=sys.stderr)
        raise SystemExit(cp.returncode)
    tabs = parse_tabs(cp.stdout)
    if not tabs:
        raise SystemExit(0)
    loop = Loop()
    handler = SidebarHandler(tabs, standalone=True)
    loop.loop(handler)
    raise SystemExit(loop.return_code)


# kitty +runpy sets __name__ to 'kitty.entry_points'
if __name__ == 'kitty.entry_points':
    run_standalone()
