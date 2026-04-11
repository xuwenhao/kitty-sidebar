# kitty-sidebar

A custom [kitty](https://sw.kovidgoyal.net/kitty/) kitten that provides a side panel for tab management, with keybinding-driven toggle, navigation, and tab lifecycle controls.

## Structure

```
kitty-sidebar/
  kitty/                    # GNU Stow package
    .config/kitty/
      sidebar.py            # sidebar kitten — tab navigation TUI
      sidebar_ctl.py        # sidebar controller — toggle & new-tab helpers
      sidebar.conf          # fragment: remote control + keybindings
```

## Installation

Managed with [GNU Stow](https://www.gnu.org/software/stow/). From this repo's directory:

```bash
stow --no-folding -t "$HOME" kitty
```

Then in your `~/.config/kitty/kitty.conf`, add:

```
include sidebar.conf
```

The `include` path is resolved relative to the kitty config directory, so no absolute path is needed. Restart kitty, or reload config live with `ctrl+shift+F5`.

## Keybindings

| Key | Action |
|-----|--------|
| `ctrl+shift+s` | Toggle sidebar |
| `cmd+t` / `ctrl+shift+t` | New tab with sidebar |

**Inside the sidebar:**

| Key | Action |
|-----|--------|
| `j` / `k` / arrows | Navigate tabs |
| `1`–`9` | Jump to tab by number |
| `enter` | Switch to selected tab |
| `n` | New tab |
| `x` | Close selected tab |
| `q` / `esc` | Close sidebar |

## Behavior

**Width:** The sidebar targets 20% of the terminal width, clamped between 40 and 60 columns. On a normal-sized window it stays at ~40 columns; on a wide or fullscreen monitor it scales up to 60.

**Auto-refresh:** The tab list refreshes every 2 seconds, so new tabs appear without any keypress.

**Tab switching:** When you switch tabs via the sidebar, it automatically spawns a new sidebar in the target tab (if one doesn't already exist) so navigation stays persistent.

## Security note

`sidebar.conf` enables kitty's remote control via unix socket (`allow_remote_control yes` + `listen_on unix:/tmp/kitty.sock`). This allows any local process to send commands to kitty (read terminal content, resize windows, launch processes, etc.). The socket is PID-suffixed (`/tmp/kitty.sock-<PID>`) and protected by filesystem permissions, but if you run untrusted code locally, consider using `allow_remote_control socket-only` or reviewing your socket file permissions.

## Requirements

- [kitty](https://sw.kovidgoyal.net/kitty/)
- Layouts `splits` (enabled by `sidebar.conf`)
- Python 3 (bundled with kitty)
