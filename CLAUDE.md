# CLAUDE.md

## Project overview

Standalone repo for a custom kitty sidebar kitten, extracted from the personal dotfiles repo. Managed as a GNU Stow package (`kitty/` is the only top-level package, mirroring `$HOME`).

## Key files

- `kitty/.config/kitty/sidebar.py` — sidebar kitten TUI (runs inside kitty via `kitty +runpy`). Uses the `kittens.tui.handler.Handler` base class with an asyncio event loop.
- `kitty/.config/kitty/sidebar_ctl.py` — standalone controller for toggle/new-tab. Runs as a background process, talks to kitty via `kitty @` remote control over a unix socket.
- `kitty/.config/kitty/sidebar.conf` — kitty config fragment (remote control + keybindings). Meant to be pulled into the user's main `kitty.conf` via `include sidebar.conf`.

## Architecture notes

### Sidebar dual-mode design

`sidebar.py` operates in two modes:
- **Kitten mode** (`main()` / `handle_result()`): invoked via `kitty +kitten`, actions return to boss via `result_handler`
- **Standalone mode** (`run_standalone()`): invoked via `kitty +runpy`, executes actions directly via `kitty @` remote control. This is the primary mode used by the keybindings.

### Socket discovery

Background processes (launched with `--type=background`) don't inherit `KITTY_LISTEN_ON`. The controller (`sidebar_ctl.py`) uses glob-based socket discovery (`/tmp/kitty.sock-*`) as fallback.

### Width clamping

The sidebar uses `--bias=20` for initial split, then queries actual geometry via `kitty @ ls` and resizes to `total_cols * 0.20` clamped to `[SIDEBAR_MIN_COLS, SIDEBAR_MAX_COLS]`.

### Hardcoded paths

`sidebar.py` and `sidebar_ctl.py` both reference `~/.config/kitty/sidebar.py` as `_SIDEBAR_LAUNCH_CMD`. This assumes stow has placed the file there. Do not rename the path in-repo — keep `kitty/.config/kitty/sidebar.py` so `stow --no-folding -t "$HOME" kitty` drops it at the hardcoded location.

## Stow usage

This repo lives at `~/Codebase/personal/kitty-sidebar`, not `~/kitty-sidebar`, so stow's default parent-directory target won't work. Always specify `$HOME` explicitly:

```bash
stow --no-folding -t "$HOME" kitty
```

`--no-folding` is mandatory if the user also stows a separate dotfiles package into `~/.config/kitty/` — two stow packages can only cohabit a target directory via individual file-level symlinks.

## Conventions

- Catppuccin Mocha color palette in `sidebar.py` (duplicated as hardcoded constants, not imported)
- Chinese comments in `sidebar.conf` are intentional — keep them
- The window title string `'sidebar'` is hardcoded in both `.py` files and is how the controller identifies existing sidebar windows
