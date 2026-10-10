"""
gui.py — Tkinter GUI for the Yahtzee-style dice game.

Screens:
    1. SetupScreen  — configure player count and names
    2. InitRollScreen — each player rolls once to decide turn order
    3. GameScreen   — main gameplay with scoresheet, dice, controls
    4. ResultScreen — final rankings
"""

import tkinter as tk
from tkinter import messagebox

from game_logic import (
    ALL_CATEGORIES,
    CHANCE_BONUS_THRESHOLD,
    CHANCE_BONUS_VALUE,
    LOWER_CATEGORIES,
    MAX_ROLLS,
    NUM_DICE,
    UPPER_CATEGORIES,
    GameState,
    Player,
    calculate_score,
    get_matching_scores,
)
from settings import load_settings, save_settings

# –––– Colour palette
BG = "#1e1e2e"
PANEL = "#2a2a3e"
ACCENT = "#7c5cbf"
ACCENT2 = "#5cb8bf"
TEXT = "#e0e0f0"
TEXT_DIM = "#888aaa"
TEXT_HEADER = "#ffffff"
HELD_BG = "#3a5f3a"
UNHELD_BG = "#3a3a50"
BTN_ROLL = "#5cb85c"
BTN_HOLD = "#4d91f0"
BTN_SCORE = "#6a5acd"
BTN_DANGER = "#d9534f"
SCORE_USED = "#2e2e42"
SCORE_AVAIL = "#35354f"
SCORE_HOVER = "#4a4a70"
WIN_GOLD = "#f5c518"
WIN_SILVER = "#aaaaaa"
WIN_BRONZE = "#cd7f32"
TEXT_DARK = "#1e1e2e"

# –––– Font constants
FONT_FAMILY = ""
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_HEAD = (FONT_FAMILY, 13, "bold")
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_DICE = (FONT_FAMILY, 32, "bold")
FONT_BTN = (FONT_FAMILY, 11, "bold")

# –––– Event bindings
EVENT_ENTER = "<Enter>"
EVENT_LEAVE = "<Leave>"

# –––– Button text constants
BTN_TEXT_ROLL = "🎲  Roll Dice"
BTN_TEXT_BANK = "✔ Bank Scores"


# –––– Dice face drawings (Unicode)
DICE_FACES = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}


def make_button(
    parent,
    text,
    command,
    bg=ACCENT,
    fg=TEXT_HEADER,
    font=FONT_BTN,
    padx=18,
    pady=8,
    **kw,
):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=font,
        activebackground=_lighten(bg),
        activeforeground=fg,
        disabledforeground=fg,
        relief="flat",
        cursor="hand2",
        padx=padx,
        pady=pady,
        **kw,
    )
    btn.bind(
        EVENT_ENTER,
        lambda e: (
            btn.config(bg=_lighten(bg)) if str(btn["state"]) != "disabled" else None
        ),
    )
    btn.bind(
        EVENT_LEAVE,
        lambda e: btn.config(bg=bg) if str(btn["state"]) != "disabled" else None,
    )
    return btn


def _lighten(hex_color: str) -> str:
    """Return a slightly lighter version of a hex color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r = min(255, r + 30)
    g = min(255, g + 30)
    b = min(255, b + 30)
    return f"#{r:02x}{g:02x}{b:02x}"


# ══════════════════════════════════════════════════════════════════════════════
# App controller
# ══════════════════════════════════════════════════════════════════════════════


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        import tkinter.font as tkfont

        try:
            sys_font = tkfont.nametofont("TkDefaultFont")
            sys_family = sys_font.actual("family")
            if sys_family:
                global \
                    FONT_FAMILY, \
                    FONT_TITLE, \
                    FONT_HEAD, \
                    FONT_NORMAL, \
                    FONT_SMALL, \
                    FONT_DICE, \
                    FONT_BTN
                FONT_FAMILY = sys_family
                FONT_TITLE = (FONT_FAMILY, 22, "bold")
                FONT_HEAD = (FONT_FAMILY, 13, "bold")
                FONT_NORMAL = (FONT_FAMILY, 11)
                FONT_SMALL = (FONT_FAMILY, 9)
                FONT_DICE = (FONT_FAMILY, 32, "bold")
                FONT_BTN = (FONT_FAMILY, 11, "bold")
        except tk.TclError:
            pass

        self.title("🎲 Dice Game")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(1124, 800)

        self.settings = load_settings()
        self._frame: tk.Frame | None = None
        self.show_setup()

    def _switch(self, frame: tk.Frame):
        if self._frame:
            self._frame.destroy()
        self._frame = frame
        frame.pack(fill="both", expand=True)

    def show_setup(self):
        self._switch(SetupScreen(self, self.settings, self._on_start))

    def _on_start(self, settings: dict):
        self.settings = settings
        # Strip internal key before saving
        save_settings({k: v for k, v in settings.items() if k != "_active_names"})
        active_names = settings.get(
            "_active_names", settings["player_names"][: settings["num_players"]]
        )
        players = [Player(name) for name in active_names]
        game = GameState(players, num_rounds=settings["num_rounds"])
        self._switch(InitRollScreen(self, game, self._on_order_decided))

    def _on_order_decided(self, game: GameState):
        self._switch(GameScreen(self, game, self._on_game_over))

    def _on_game_over(self, game: GameState):
        self._switch(ResultScreen(self, game, self.show_setup))


# ══════════════════════════════════════════════════════════════════════════════
# 1. Setup Screen
# ══════════════════════════════════════════════════════════════════════════════


class SetupScreen(tk.Frame):
    def __init__(self, master, settings: dict, on_start):
        super().__init__(master, bg=BG)
        self._settings = dict(settings)
        self._on_start = on_start
        self._name_vars: list[tk.StringVar] = []
        self._build()

    def _build(self):
        tk.Label(
            self, text="🎲  Dice Game Setup", font=FONT_TITLE, bg=BG, fg=TEXT_HEADER
        ).pack(pady=(40, 20))

        # –––– Controls row
        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack()

        tk.Label(ctrl, text="Players:", font=FONT_NORMAL, bg=BG, fg=TEXT).grid(
            row=0, column=0, padx=6
        )
        self._player_count = tk.IntVar(value=self._settings["num_players"])
        sb = tk.Spinbox(
            ctrl,
            from_=2,
            to=8,
            textvariable=self._player_count,
            width=4,
            font=FONT_NORMAL,
            bg=PANEL,
            fg=TEXT,
            buttonbackground=PANEL,
            relief="flat",
            command=self._update_name_rows,
        )
        sb.grid(row=0, column=1, padx=6)

        tk.Label(ctrl, text="  Rounds:", font=FONT_NORMAL, bg=BG, fg=TEXT).grid(
            row=0, column=2, padx=6
        )
        self._rounds = tk.IntVar(value=self._settings["num_rounds"])
        tk.Spinbox(
            ctrl,
            from_=1,
            to=20,
            textvariable=self._rounds,
            width=4,
            font=FONT_NORMAL,
            bg=PANEL,
            fg=TEXT,
            buttonbackground=PANEL,
            relief="flat",
        ).grid(row=0, column=3, padx=6)

        # –––– Name list
        self._names_frame = tk.Frame(self, bg=BG)
        self._names_frame.pack(pady=20)
        self._populate_names()

        make_button(
            self, "▶  Start Game", self._start, bg=BTN_ROLL, padx=30, pady=10
        ).pack(pady=10)

    def _populate_names(self):
        for w in self._names_frame.winfo_children():
            w.destroy()
        self._name_vars.clear()

        n = self._player_count.get()
        saved_names = self._settings.get("player_names", [])

        cols = 4
        for i in range(n):
            default = saved_names[i] if i < len(saved_names) else f"Player {i + 1}"
            var = tk.StringVar(value=default)
            self._name_vars.append(var)
            row, col = divmod(i, cols)
            cell = tk.Frame(self._names_frame, bg=PANEL, padx=8, pady=6)
            cell.grid(row=row, column=col, padx=6, pady=4, sticky="ew")
            tk.Label(
                cell, text=f"P{i + 1}", font=FONT_SMALL, bg=PANEL, fg=TEXT_DIM, width=3
            ).pack(side="left")
            tk.Entry(
                cell,
                textvariable=var,
                font=FONT_NORMAL,
                bg=PANEL,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                width=14,
            ).pack(side="left")

    def _update_name_rows(self):
        self._populate_names()

    def _start(self):
        n = self._player_count.get()
        names = [
            v.get().strip() or f"Player {i + 1}" for i, v in enumerate(self._name_vars)
        ]
        if len(set(names)) < len(names):
            messagebox.showwarning(
                "Duplicate names", "All player names must be unique."
            )
            return
        # Save all 8 name slots so they're remembered, but only use the first n for the game
        all_names = names + [f"Player {i + 1}" for i in range(len(names), 8)]
        self._on_start(
            {
                "num_players": n,
                "num_rounds": self._rounds.get(),
                "player_names": all_names,
                "_active_names": names,  # just the n players actually playing
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Init Roll Screen — determine turn order
# ══════════════════════════════════════════════════════════════════════════════


class InitRollScreen(tk.Frame):
    def __init__(self, master, game: GameState, on_done):
        super().__init__(master, bg=BG)
        self._game = game
        self._on_done = on_done
        self._pending: list[Player] = list(game.players)
        self._roll_index = 0
        self._tiebreak_round = 0
        self._score_boost = 0  # added to tiebreaker rolls to keep them above non-tied
        self._dice_vars: dict[Player, list[tk.StringVar]] = {}
        self._total_vars: dict[Player, tk.StringVar] = {}
        self._row_labels: dict[Player, tk.Label] = {}
        self._build()

    def _build(self):
        tk.Label(
            self,
            text="🎲  Roll to Decide Turn Order",
            font=FONT_TITLE,
            bg=BG,
            fg=TEXT_HEADER,
        ).pack(pady=(40, 10))
        self._subtitle = tk.Label(
            self,
            text="Each player rolls all 5 dice — highest total goes first.",
            font=FONT_NORMAL,
            bg=BG,
            fg=TEXT_DIM,
        )
        self._subtitle.pack(pady=(0, 20))

        self._table_frame = tk.Frame(self, bg=BG)
        self._table_frame.pack()

        self._status = tk.StringVar(value=f"{self._pending[0].name}, press Roll!")
        tk.Label(
            self, textvariable=self._status, font=FONT_NORMAL, bg=BG, fg=ACCENT2
        ).pack(pady=16)

        self._roll_btn = make_button(
            self, "🎲  Roll All 5 Dice", self._do_roll, bg=BTN_ROLL, padx=30, pady=10
        )
        self._roll_btn.pack()

        self._rebuild_table()

    def _rebuild_table(self):
        for w in self._table_frame.winfo_children():
            w.destroy()

        headers = ["Player", "⚀", "⚁", "⚂", "⚃", "⚄", "Total"]
        col_widths = [14, 3, 3, 3, 3, 3, 6]
        for col, (txt, w) in enumerate(zip(headers, col_widths)):
            tk.Label(
                self._table_frame,
                text=txt,
                font=FONT_HEAD,
                bg=BG,
                fg=TEXT_HEADER,
                width=w,
                anchor="center",
            ).grid(row=0, column=col, padx=4, pady=4)

        for i, p in enumerate(self._pending):
            lbl = tk.Label(
                self._table_frame,
                text=p.name,
                font=FONT_NORMAL,
                bg=BG,
                fg=TEXT,
                width=14,
                anchor="w",
            )
            lbl.grid(row=i + 1, column=0, padx=4, pady=3)
            self._row_labels[p] = lbl

            d_vars = []
            for d in range(NUM_DICE):
                var = tk.StringVar(value="·")
                d_vars.append(var)
                tk.Label(
                    self._table_frame,
                    textvariable=var,
                    font=FONT_DICE,
                    bg=BG,
                    fg=TEXT_DIM,
                    width=3,
                    anchor="center",
                ).grid(row=i + 1, column=d + 1, padx=2, pady=3)
            self._dice_vars[p] = d_vars

            total_var = tk.StringVar(value="—")
            self._total_vars[p] = total_var
            tk.Label(
                self._table_frame,
                textvariable=total_var,
                font=FONT_HEAD,
                bg=BG,
                fg=ACCENT2,
                width=6,
                anchor="center",
            ).grid(row=i + 1, column=6, padx=6, pady=3)

    def _do_roll(self):
        player = self._pending[self._roll_index]
        dice, total = self._game.do_init_roll(player)

        # Add boost so tiebreaker players always sort above non-tied players
        if self._score_boost:
            player.init_roll = self._score_boost + total

        for d, val in enumerate(dice):
            self._dice_vars[player][d].set(DICE_FACES[val])
        self._total_vars[player].set(str(total))  # display raw roll, not boosted

        self._roll_index += 1

        if self._roll_index < len(self._pending):
            next_player = self._pending[self._roll_index]
            self._status.set(f"{next_player.name}, press Roll!")
        else:
            self._roll_btn.config(state="disabled")
            self._status.set("All rolled! Checking for ties…")
            self.after(900, self._check_ties)

    def _check_ties(self):
        max_score = max(p.init_roll for p in self._pending)
        winners = [p for p in self._pending if p.init_roll == max_score]

        if len(winners) == 1:
            self._game.finalise_order()
            self._on_done(self._game)
        else:
            names = ", ".join(p.name for p in winners)
            self._tiebreak_round += 1
            self._subtitle.config(
                text=f"🔄  Tiebreaker #{self._tiebreak_round}!  Tied: {names}",
                fg=BTN_HOLD,
            )
            self._status.set(f"{winners[0].name}, press Roll!")

            # Boost = current max so tiebreaker winners always sort above all others
            self._score_boost = (
                max(p.init_roll for p in self._game.players if p.init_roll is not None)
                + 1
            )

            self._pending = winners
            self._roll_index = 0
            self._rebuild_table()
            self._roll_btn.config(state="normal")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Game Screen
# ══════════════════════════════════════════════════════════════════════════════


class GameScreen(tk.Frame):
    def __init__(self, master, game: GameState, on_game_over):
        super().__init__(master, bg=BG)
        self._game = game
        self._on_game_over = on_game_over
        self._dice_buttons: list[tk.Button] = []
        self._score_buttons: dict[str, tk.Button] = {}
        self._build()
        self._refresh()

    # –––– Layout

    def _build(self):
        # Top bar
        top = tk.Frame(self, bg=PANEL, pady=8)
        top.pack(fill="x")
        self._round_var = tk.StringVar()
        self._player_var = tk.StringVar()
        tk.Label(
            top, textvariable=self._round_var, font=FONT_HEAD, bg=PANEL, fg=TEXT_HEADER
        ).pack(side="left", padx=20)
        tk.Label(
            top, textvariable=self._player_var, font=FONT_HEAD, bg=PANEL, fg=ACCENT2
        ).pack(side="left", padx=10)
        self._rolls_var = tk.StringVar()
        tk.Label(
            top, textvariable=self._rolls_var, font=FONT_NORMAL, bg=PANEL, fg=TEXT_DIM
        ).pack(side="right", padx=20)

        # Skip button — shown only in the last round
        self._skip_btn = make_button(
            top,
            "⏭  Skip Remaining Turns",
            self._skip_to_end,
            bg=BTN_DANGER,
            fg=TEXT_HEADER,
            font=FONT_SMALL,
            padx=10,
            pady=4,
        )
        self._skip_btn.pack(side="right", padx=10)
        self._skip_btn.pack_forget()

        # Finish game button — shown when game is over
        self._finish_btn = make_button(
            top,
            "🏆  Finish Game",
            self._finish_game,
            bg=BTN_ROLL,
            fg=TEXT_HEADER,
            font=FONT_SMALL,
            padx=10,
            pady=4,
        )
        self._finish_btn.pack(side="right", padx=10)
        self._finish_btn.pack_forget()

        # Main area: scoresheet (left) + play area (right)
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)

        self._score_canvas_frame = tk.Frame(main, bg=BG)
        self._score_canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_scoresheet(self._score_canvas_frame)

        right = tk.Frame(main, bg=BG, width=350)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        right.pack_propagate(False)
        self._build_play_area(right)

    def _build_scoresheet(self, parent):
        # Scrollable canvas for the scoresheet
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._sheet_inner = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=self._sheet_inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(
                window_id,
                width=max(canvas.winfo_width(), self._sheet_inner.winfo_reqwidth()),
            )

        self._sheet_inner.bind("<Configure>", _on_configure)
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                window_id, width=max(e.width, self._sheet_inner.winfo_reqwidth())
            ),
        )

        def _on_mousewheel(e):
            if e.num == 4:
                canvas.yview_scroll(-1, "units")
            elif e.num == 5:
                canvas.yview_scroll(1, "units")
            elif e.delta:
                canvas.yview_scroll(-1 * (e.delta // 120), "units")

        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self._sheet_inner.bind("<Button-4>", _on_mousewheel)
        self._sheet_inner.bind("<Button-5>", _on_mousewheel)
        self._sheet_inner.bind("<MouseWheel>", _on_mousewheel)

        self._sheet_canvas = canvas
        self._build_sheet_content(self._sheet_inner)

    def _build_sheet_content(self, parent):
        players = self._game.players
        num_players = len(players)

        # Single grid table for aligned columns
        table = tk.Frame(parent, bg=BG)
        table.pack(fill="x", padx=2, pady=2)

        table.columnconfigure(0, weight=0, minsize=165)
        for j in range(num_players):
            table.columnconfigure(j + 1, weight=1, minsize=65, uniform="player_col")

        r = 0

        # –––– Header row
        tk.Label(
            table,
            text="Category",
            font=FONT_HEAD,
            bg=PANEL,
            fg=TEXT_HEADER,
            anchor="w",
            padx=8,
            pady=5,
        ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

        for j, p in enumerate(players):
            lbl = tk.Label(
                table,
                text=p.name,
                font=FONT_SMALL,
                bg=PANEL,
                fg=TEXT_HEADER,
                anchor="center",
                padx=4,
                pady=5,
            )
            lbl.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
            self._score_buttons[f"__name_{j}"] = lbl  # store for later highlight

        r += 1

        # –––– Upper section header
        tk.Label(
            table,
            text="  ─── Upper Section ───",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_DIM,
            anchor="w",
            padx=8,
            pady=3,
        ).grid(row=r, column=0, columnspan=num_players + 1, sticky="ew", pady=(4, 1))

        r += 1

        # Upper category rows
        self._upper_rows: dict[str, list[tk.Label]] = {}
        for cat in UPPER_CATEGORIES:
            tk.Label(
                table,
                text=cat,
                font=FONT_NORMAL,
                bg=SCORE_AVAIL,
                fg=TEXT,
                anchor="w",
                padx=8,
                pady=3,
            ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

            cells = []
            for j in range(num_players):
                cell = tk.Label(
                    table,
                    text="",
                    font=FONT_NORMAL,
                    bg=SCORE_AVAIL,
                    fg=TEXT,
                    anchor="center",
                    padx=4,
                    pady=3,
                )
                cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
                cells.append(cell)
            self._upper_rows[cat] = cells
            r += 1

        # Bonus row
        tk.Label(
            table,
            text=f"  Bonus (Chance ≥ {CHANCE_BONUS_THRESHOLD} → +{CHANCE_BONUS_VALUE})",
            font=FONT_SMALL,
            bg=PANEL,
            fg=ACCENT2,
            anchor="w",
            padx=8,
            pady=3,
        ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

        self._bonus_cells: list[tk.Label] = []
        for j in range(num_players):
            cell = tk.Label(
                table,
                text="—",
                font=FONT_SMALL,
                bg=PANEL,
                fg=ACCENT2,
                anchor="center",
                padx=4,
                pady=3,
            )
            cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
            self._bonus_cells.append(cell)

        r += 1

        # Upper subtotal row
        tk.Label(
            table,
            text="  Upper Subtotal",
            font=FONT_SMALL,
            bg=PANEL,
            fg=TEXT_DIM,
            anchor="w",
            padx=8,
            pady=3,
        ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

        self._upper_sub_cells: list[tk.Label] = []
        for j in range(num_players):
            cell = tk.Label(
                table,
                text="0",
                font=FONT_SMALL,
                bg=PANEL,
                fg=TEXT_DIM,
                anchor="center",
                padx=4,
                pady=3,
            )
            cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
            self._upper_sub_cells.append(cell)

        r += 1

        # –––– Section separator
        tk.Frame(table, bg=ACCENT, height=2).grid(
            row=r, column=0, columnspan=num_players + 1, sticky="ew", pady=(6, 4)
        )

        r += 1

        # –––– Lower section header
        tk.Label(
            table,
            text="  ─── Lower Section ───",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_DIM,
            anchor="w",
            padx=8,
            pady=3,
        ).grid(row=r, column=0, columnspan=num_players + 1, sticky="ew", pady=(4, 1))

        r += 1

        # Lower category rows
        self._lower_rows: dict[str, list[tk.Label]] = {}
        for cat in LOWER_CATEGORIES:
            tk.Label(
                table,
                text=cat,
                font=FONT_NORMAL,
                bg=SCORE_AVAIL,
                fg=TEXT,
                anchor="w",
                padx=8,
                pady=3,
            ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

            cells = []
            for j in range(num_players):
                cell = tk.Label(
                    table,
                    text="",
                    font=FONT_NORMAL,
                    bg=SCORE_AVAIL,
                    fg=TEXT,
                    anchor="center",
                    padx=4,
                    pady=3,
                )
                cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
                cells.append(cell)
            self._lower_rows[cat] = cells
            r += 1

        # Top Score bonus row
        tk.Label(
            table,
            text="  🏆 Top Score (+50/round)",
            font=FONT_SMALL,
            bg=PANEL,
            fg=WIN_GOLD,
            anchor="w",
            padx=8,
            pady=3,
        ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

        self._top_score_cells: list[tk.Label] = []
        for j in range(num_players):
            cell = tk.Label(
                table,
                text="—",
                font=FONT_SMALL,
                bg=PANEL,
                fg=WIN_GOLD,
                anchor="center",
                padx=4,
                pady=3,
            )
            cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=1)
            self._top_score_cells.append(cell)

        r += 1

        # Grand total row
        tk.Label(
            table,
            text="  TOTAL",
            font=FONT_HEAD,
            bg=ACCENT,
            fg=TEXT_HEADER,
            anchor="w",
            padx=8,
            pady=5,
        ).grid(row=r, column=0, sticky="nsew", padx=1, pady=(2, 1))

        self._total_cells: list[tk.Label] = []
        for j in range(num_players):
            cell = tk.Label(
                table,
                text="0",
                font=FONT_HEAD,
                bg=ACCENT,
                fg=TEXT_HEADER,
                anchor="center",
                padx=4,
                pady=5,
            )
            cell.grid(row=r, column=j + 1, sticky="nsew", padx=1, pady=(2, 1))
            self._total_cells.append(cell)

        # –––– Round navigation buttons
        self._current_round_view = 0  # 0 = cumulative totals, 1+ = specific rounds
        self._round_nav_frame = tk.Frame(parent, bg=PANEL, padx=8, pady=6)
        self._round_nav_frame.pack(fill="x", pady=(10, 4))

        title_row = tk.Frame(self._round_nav_frame, bg=PANEL)
        title_row.pack(fill="x", pady=(0, 4))

        self._round_label = tk.Label(
            title_row,
            text="View: Cumulative Totals",
            font=FONT_HEAD,
            bg=PANEL,
            fg=TEXT_HEADER,
        )
        self._round_label.pack(side="left")

        btns_row = tk.Frame(self._round_nav_frame, bg=PANEL)
        btns_row.pack(fill="x", pady=2)

        # Cumulative view button
        self._cumulative_btn = make_button(
            btns_row,
            "Cumulative",
            self._show_cumulative_view,
            bg=ACCENT,
            fg=TEXT_HEADER,
            font=FONT_SMALL,
            padx=8,
            pady=4,
        )
        self._cumulative_btn.pack(side="left", padx=(0, 4))

        # Individual round buttons (created dynamically in chronological order)
        self._round_buttons: list[tk.Button] = []
        self._build_round_buttons(btns_row)

        # Per-round dice history — displayed only when viewing a specific round
        self._round_dice_frame = tk.Frame(parent, bg=PANEL, padx=8, pady=6)
        self._round_dice_frame.pack(fill="x", pady=(6, 8))
        self._round_dice_labels: list[tuple[tk.Label, list[tk.Label]]] = []
        self._build_round_dice_display(self._round_dice_frame)

    def _build_round_buttons(self, parent):
        """Create round buttons dynamically based on number of rounds (chronological order)"""
        for i in range(self._game.num_rounds):
            btn = make_button(
                parent,
                f"R{i + 1}",
                lambda r=i + 1: self._show_round_view(r),
                bg=PANEL,
                fg=TEXT,
                font=FONT_SMALL,
                padx=6,
                pady=4,
            )
            btn.pack(side="left", padx=2)
            btn.config(state="disabled")  # Initially disabled until round is completed
            self._round_buttons.append(btn)

    def _build_round_dice_display(self, parent):
        """
        Build per-player dice rows that are shown only when viewing a specific round.
        Each row looks like:  [Player Name]   ⚁ ⚂ ⚃ ⚄ ⚅  (sum: N)   🏆 +50 Top Score
        """
        tk.Label(
            parent,
            text="🎲  Dice Rolled in Selected Round",
            font=FONT_HEAD,
            bg=PANEL,
            fg=ACCENT2,
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        for j, player in enumerate(self._game.players):
            row = tk.Frame(parent, bg=PANEL)
            row.pack(fill="x", pady=2)

            name_lbl = tk.Label(
                row,
                text=player.name,
                font=FONT_SMALL,
                bg=PANEL,
                fg=TEXT_HEADER,
                width=12,
                anchor="w",
            )
            name_lbl.pack(side="left", padx=(4, 6))

            dice_labels = []
            for _ in range(NUM_DICE):
                dl = tk.Label(
                    row,
                    text="·",
                    font=(FONT_FAMILY, 16, "bold"),
                    bg=PANEL,
                    fg=TEXT_DIM,
                    width=2,
                    anchor="center",
                )
                dl.pack(side="left", padx=1)
                dice_labels.append(dl)

            sum_lbl = tk.Label(
                row,
                text="",
                font=FONT_SMALL,
                bg=PANEL,
                fg=TEXT_DIM,
                anchor="w",
            )
            sum_lbl.pack(side="left", padx=(8, 0))
            dice_labels.append(sum_lbl)

            ts_lbl = tk.Label(
                row,
                text="",
                font=FONT_SMALL,
                bg=PANEL,
                fg=WIN_GOLD,
                anchor="w",
            )
            ts_lbl.pack(side="left", padx=(8, 0))
            dice_labels.append(ts_lbl)

            self._round_dice_labels.append((name_lbl, dice_labels))

    def _build_play_area(self, parent):
        tk.Label(parent, text="Your Dice", font=FONT_HEAD, bg=BG, fg=TEXT_HEADER).pack(
            pady=(0, 8)
        )

        # Dice row
        dice_frame = tk.Frame(parent, bg=BG)
        dice_frame.pack(pady=(0, 4))
        self._dice_buttons.clear()
        for i in range(NUM_DICE):
            dice_frame.columnconfigure(i, weight=1, uniform="dice")
            btn = tk.Button(
                dice_frame,
                text=DICE_FACES[1],
                font=(FONT_FAMILY, 22, "bold"),
                bg=UNHELD_BG,
                fg=TEXT_HEADER,
                activebackground=HELD_BG,
                activeforeground=TEXT_HEADER,
                relief="flat",
                width=2,
                padx=4,
                pady=4,
                cursor="hand2",
                command=lambda idx=i: self._toggle_hold(idx),
            )
            btn.grid(row=0, column=i, padx=3, pady=2, sticky="nsew")
            self._dice_buttons.append(btn)

        self._hold_hint = tk.Label(
            parent,
            text="Click a die to hold/unhold it",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_DIM,
        )
        self._hold_hint.pack(pady=(2, 10))

        # Roll button
        self._roll_btn = make_button(
            parent, BTN_TEXT_ROLL, self._do_roll, bg=BTN_ROLL, padx=20, pady=10
        )
        self._roll_btn.pack(fill="x", padx=10, pady=4)

        # Bank button — always shown, but only active after first roll
        self._bank_btn = make_button(
            parent,
            BTN_TEXT_BANK,
            self._bank_all,
            bg=BTN_HOLD,
            fg=TEXT_DARK,
            padx=20,
            pady=10,
        )
        self._bank_btn.pack(fill="x", padx=10, pady=4)

        # Scoring instructions
        self._score_hint = tk.Label(
            parent,
            text="Roll to see scoring options",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_DIM,
        )
        self._score_hint.pack(pady=(14, 4))

        # Category buttons — plain tk.Button; hover bindings are re-applied in _refresh
        self._cat_frame = tk.Frame(parent, bg=BG)
        self._cat_frame.pack(fill="both", expand=True, padx=6)

        for cat in ALL_CATEGORIES:
            btn = tk.Button(
                self._cat_frame,
                text=cat,
                command=lambda c=cat: self._score_category(c),
                bg=SCORE_AVAIL,
                fg=TEXT_DIM,
                activeforeground=TEXT_HEADER,
                font=FONT_SMALL,
                padx=6,
                pady=5,
                anchor="w",
                relief="flat",
                cursor="hand2",
                state="disabled",
            )
            btn.pack(fill="x", pady=1)
            self._score_buttons[cat] = btn

            # Add separator after upper categories
            if cat == "Sixes":
                separator = tk.Frame(self._cat_frame, bg=ACCENT, height=2)
                separator.pack(fill="x", pady=(4, 4))

        # Spacer
        tk.Frame(parent, bg=BG, height=10).pack()

    # –––– Refresh / update helpers

    def _refresh(self):
        g = self._game
        cp = g.current_player()
        has_rolled = g.rolls_used > 0
        available_cats = {cat for cat in ALL_CATEGORIES if cp.sheet.is_available(cat)}
        scoring_preview = (
            get_matching_scores(g.dice, available_cats) if has_rolled else {}
        )

        self._update_header(g, cp)
        self._update_skip_button(g)
        self._update_dice_display(g)
        self._update_roll_and_bank_buttons(g)
        self._update_score_hint(g)
        self._update_category_buttons(g, cp)
        self._update_scoresheet(scoring_preview)
        self._update_round_view()
        self._highlight_current_player(g)

    def _update_header(self, g, cp):
        self._round_var.set(f"Round {g.current_round} / {g.num_rounds}")
        self._player_var.set(f"🎯 {cp.name}'s turn")
        self._rolls_var.set(f"Rolls: {g.rolls_used} / {MAX_ROLLS}")

    def _update_skip_button(self, g):
        if g.current_round == g.num_rounds:
            self._skip_btn.pack(side="right", padx=10)
        else:
            self._skip_btn.pack_forget()

        # Show finish button when game is over
        if g.phase == "game_over":
            self._finish_btn.pack(side="right", padx=10)
            self._skip_btn.pack_forget()
        else:
            self._finish_btn.pack_forget()

    def _update_dice_display(self, g):
        for i, (val, held) in enumerate(zip(g.dice, g.held)):
            face = DICE_FACES.get(val, str(val))
            bg = HELD_BG if held else UNHELD_BG
            self._dice_buttons[i].config(text=face, bg=bg)

    def _update_roll_and_bank_buttons(self, g):
        can_roll = g.can_roll()
        all_held = g.rolls_used > 0 and all(g.held)
        must_bank = (not can_roll or all_held) and g.rolls_used > 0
        has_rolled = g.rolls_used > 0

        if must_bank:
            self._roll_btn.config(state="disabled", text=BTN_TEXT_ROLL, bg="#555566")
            self._bank_btn.config(
                state="normal", text=BTN_TEXT_BANK, bg=BTN_HOLD, fg=TEXT_DARK
            )
        else:
            self._configure_roll_button(can_roll)
            # Bank button is always visible but only active after first roll
            if has_rolled:
                self._bank_btn.config(
                    state="normal", text=BTN_TEXT_BANK, bg=BTN_HOLD, fg=TEXT_DARK
                )
            else:
                self._bank_btn.config(
                    state="disabled", text=BTN_TEXT_BANK, bg=BTN_HOLD, fg=TEXT_DARK
                )

    def _configure_roll_button(self, can_roll):
        if not can_roll:
            self._roll_btn.config(state="disabled", text=BTN_TEXT_ROLL, bg="#555566")
        else:
            self._roll_btn.config(state="normal", text=BTN_TEXT_ROLL, bg=BTN_ROLL)

    def _update_score_hint(self, g):
        has_rolled = g.rolls_used > 0
        can_roll = g.can_roll()
        all_held = g.rolls_used > 0 and all(g.held)
        must_bank = (not can_roll or all_held) and g.rolls_used > 0

        if not has_rolled:
            self._score_hint.config(text="Roll to see scoring options", fg=TEXT_DIM)
        elif must_bank:
            self._score_hint.config(text="", fg=TEXT_DIM)
        else:
            self._score_hint.config(text="Or choose a single category:", fg=TEXT_DIM)

    def _update_category_buttons(self, g, cp):
        has_rolled = g.rolls_used > 0
        available_cats = {cat for cat in ALL_CATEGORIES if cp.sheet.is_available(cat)}
        scoring_preview = (
            get_matching_scores(g.dice, available_cats) if has_rolled else {}
        )

        for cat in ALL_CATEGORIES:
            btn = self._score_buttons.get(cat)
            if btn is None:
                continue
            self._configure_category_button(btn, cat, cp, has_rolled, scoring_preview)

    def _configure_category_button(self, btn, cat, cp, has_rolled, scoring_preview):
        avail = cp.sheet.is_available(cat)
        if not avail:
            self._configure_unavailable_button(btn, cat, cp)
        elif has_rolled and cat in scoring_preview:
            self._configure_available_scoring_button(btn, cat, scoring_preview[cat])
        elif has_rolled and cat not in scoring_preview:
            self._configure_excluded_button(btn, cat)
        else:
            self._configure_disabled_button(btn, cat)

    def _configure_unavailable_button(self, btn, cat, cp):
        total = cp.sheet.totals[cat]
        btn.config(
            state="disabled",
            bg=SCORE_USED,
            text=f"{cat}  (used — total {total})",
            fg=TEXT_DIM,
            activebackground=SCORE_USED,
        )
        btn.unbind(EVENT_ENTER)
        btn.unbind(EVENT_LEAVE)

    def _configure_available_scoring_button(self, btn, cat, potential):
        btn_bg = BTN_SCORE
        btn.config(
            state="normal",
            bg=btn_bg,
            fg=TEXT_HEADER,
            activebackground=_lighten(btn_bg),
            text=f"{cat}  (+{potential})",
        )
        btn.unbind(EVENT_ENTER)
        btn.unbind(EVENT_LEAVE)
        btn.bind(EVENT_ENTER, lambda e, b=btn, c=btn_bg: b.config(bg=_lighten(c)))
        btn.bind(EVENT_LEAVE, lambda e, b=btn, c=btn_bg: b.config(bg=c))

    def _configure_excluded_button(self, btn, cat):
        potential = calculate_score(cat, self._game.dice)
        if potential > 0:
            label = f"{cat}  (covered by higher combo)"
        else:
            label = f"{cat}  (+0)"
        btn.config(
            state="normal",
            bg=SCORE_AVAIL,
            fg=TEXT_DIM,
            activebackground=SCORE_AVAIL,
            text=label,
        )
        btn.unbind(EVENT_ENTER)
        btn.unbind(EVENT_LEAVE)

    def _configure_disabled_button(self, btn, cat):
        btn.config(
            state="disabled",
            bg=SCORE_AVAIL,
            text=cat,
            fg=TEXT_DIM,
            activebackground=SCORE_AVAIL,
        )
        btn.unbind(EVENT_ENTER)
        btn.unbind(EVENT_LEAVE)

    def _highlight_current_player(self, g):
        for j, p in enumerate(g.players):
            lbl = self._score_buttons.get(f"__name_{j}")
            if lbl:
                lbl.config(fg=WIN_GOLD if j == g.current_player_index else TEXT_HEADER)

    # –––– Round navigation

    def _show_cumulative_view(self):
        self._current_round_view = 0
        self._update_round_view()
        self._update_scoresheet()

    def _show_round_view(self, round_num):
        self._current_round_view = round_num
        self._update_round_view()
        self._update_scoresheet()

    def _update_round_view(self):
        g = self._game
        max_round = (
            max((p.sheet.completed_rounds for p in g.players), default=0)
            if g.players
            else 0
        )

        if self._current_round_view > max_round:
            self._current_round_view = 0

        self._update_round_view_header()
        self._update_round_nav_buttons(max_round)

        if hasattr(self, "_sheet_canvas"):
            self._sheet_canvas.configure(scrollregion=self._sheet_canvas.bbox("all"))

    def _update_round_view_header(self):
        if self._current_round_view == 0:
            self._round_label.config(text="View: Cumulative Totals")
            self._round_dice_frame.pack_forget()
        else:
            self._round_label.config(text=f"View: Round {self._current_round_view}")
            self._round_dice_frame.pack(fill="x", pady=(6, 8))
            self._update_round_dice_display(self._current_round_view)

    def _update_round_nav_buttons(self, max_round: int):
        is_cumul = self._current_round_view == 0
        self._cumulative_btn.config(
            bg=ACCENT if is_cumul else PANEL, fg=TEXT_HEADER if is_cumul else TEXT
        )
        for i, btn in enumerate(self._round_buttons):
            round_num = i + 1
            is_active = self._current_round_view == round_num
            if round_num <= max_round:
                btn.config(
                    state="normal",
                    bg=ACCENT if is_active else PANEL,
                    fg=TEXT_HEADER if is_active else TEXT,
                )
            else:
                btn.config(state="disabled", bg=PANEL, fg=TEXT)

    def _update_round_dice_display(self, view_round: int):
        """Fill in the dice rows for a specific completed round."""
        g = self._game
        ci = g.current_player_index
        for j, (name_lbl, dice_lbls) in enumerate(self._round_dice_labels):
            player = g.players[j]
            name_lbl.config(fg=WIN_GOLD if j == ci else TEXT_HEADER)
            self._render_player_round_dice(player, dice_lbls, view_round)

    def _render_player_round_dice(self, player, dice_lbls, view_round: int):
        sheet = player.sheet
        if view_round <= len(sheet.dice_history):
            dice = sheet.dice_history[view_round - 1]
            self._populate_player_dice_labels(dice_lbls, dice)
            self._populate_round_dice_badges(dice_lbls, sheet, view_round - 1)
        else:
            self._clear_player_dice_labels(dice_lbls)

    def _populate_player_dice_labels(self, dice_lbls, dice: list[int]):
        for di in range(NUM_DICE):
            val = dice[di] if di < len(dice) else 0
            face = DICE_FACES.get(val, str(val)) if val > 0 else "·"
            fg_color = ACCENT2 if val > 0 else TEXT_DIM
            dice_lbls[di].config(text=face, fg=fg_color)
        total = sum(dice)
        dice_lbls[NUM_DICE].config(
            text=f"(sum: {total})" if total > 0 else "", fg=TEXT_DIM
        )

    def _populate_round_dice_badges(self, dice_lbls, sheet, idx: int):
        history = sheet.top_score_bonus_history
        won_ts = idx < len(history) and history[idx] > 0
        dice_lbls[NUM_DICE + 1].config(
            text="🏆 +50 Top Score" if won_ts else "", fg=WIN_GOLD
        )

    def _clear_player_dice_labels(self, dice_lbls):
        for di in range(NUM_DICE):
            dice_lbls[di].config(text="—", fg=TEXT_DIM)
        dice_lbls[NUM_DICE].config(text="", fg=TEXT_DIM)
        dice_lbls[NUM_DICE + 1].config(text="", fg=WIN_GOLD)

    def _update_scoresheet(self, scoring_preview: dict[str, int] | None = None):
        players = self._game.players
        ci = self._game.current_player_index
        preview = scoring_preview or {}
        dice = self._game.dice
        has_rolled = self._game.rolls_used > 0
        view_round = self._current_round_view  # 0 = cumulative, 1+ = specific round

        for j, player in enumerate(players):
            sheet = player.sheet
            is_current = j == ci

            self._update_upper_section(
                sheet, j, is_current, has_rolled, preview, dice, view_round
            )
            self._update_bonus_section(sheet, j, view_round)
            self._update_lower_section(
                sheet, j, is_current, has_rolled, preview, dice, view_round
            )
            self._update_totals(sheet, j, view_round)

    def _update_upper_section(
        self, sheet, j, is_current, has_rolled, preview, dice, view_round
    ):
        for cat in UPPER_CATEGORIES:
            cell = self._upper_rows[cat][j]
            total = sheet.totals[cat]
            avail = sheet.is_available(cat)

            if view_round > 0:
                self._config_round_view_cell(cell, sheet, cat, view_round, is_current)
            else:
                self._config_cumulative_view_cell(
                    cell, cat, total, avail, is_current, has_rolled, preview, dice
                )

    def _config_round_view_cell(self, cell, sheet, cat, view_round, is_current):
        round_scores = sheet.history[cat]
        if view_round <= len(round_scores):
            round_score = round_scores[view_round - 1]
            cell.config(
                text=str(round_score),
                bg=SCORE_AVAIL if not is_current else SCORE_HOVER,
                fg=TEXT if round_score else TEXT_DIM,
            )
        else:
            cell.config(text="—", bg=SCORE_AVAIL, fg=TEXT_DIM)

    def _config_cumulative_view_cell(
        self, cell, cat, total, avail, is_current, has_rolled, preview, dice
    ):
        if not avail:
            self._config_unavailable_cell(cell, total)
        elif is_current and has_rolled:
            self._config_current_preview_cell(cell, cat, total, preview, dice)
        elif total > 0:
            self._config_prior_score_cell(cell, total, is_current)
        else:
            self._config_empty_cell(cell, is_current)

    def _config_unavailable_cell(self, cell, total):
        cell.config(
            text=str(total) if total else "0", bg=SCORE_USED, fg=TEXT_DIM, cursor=""
        )

    def _config_current_preview_cell(self, cell, cat, total, preview, dice):
        pts = preview.get(cat, calculate_score(cat, dice))
        display = self._format_score_display(total, pts)
        cell.config(text=display, bg=SCORE_HOVER, fg=TEXT)

    def _config_prior_score_cell(self, cell, total, is_current):
        cell.config(
            text=str(total), bg=SCORE_AVAIL if not is_current else SCORE_HOVER, fg=TEXT
        )

    def _config_empty_cell(self, cell, is_current):
        cell.config(text="", bg=SCORE_AVAIL if not is_current else SCORE_HOVER, fg=TEXT)

    def _format_score_display(self, total, pts):
        if total and pts:
            return f"{total}+{pts}"
        elif total:
            return str(total)
        else:
            return f"(+{pts})"

    def _update_bonus_section(self, sheet, j, view_round):
        if view_round > 0:
            round_sub = sheet.round_upper_subtotal(view_round)
            self._upper_sub_cells[j].config(text=str(round_sub))
            self._bonus_cells[j].config(text="—")
        else:
            sub = sheet.upper_subtotal()
            chance = sheet.chance_total()
            bonus = sheet.chance_bonus()
            progress_txt = f"{chance}/{CHANCE_BONUS_THRESHOLD}"
            self._bonus_cells[j].config(
                text=f"+{CHANCE_BONUS_VALUE} ✓" if bonus else progress_txt
            )
            self._upper_sub_cells[j].config(text=str(sub))

    def _update_lower_section(
        self, sheet, j, is_current, has_rolled, preview, dice, view_round
    ):
        for cat in LOWER_CATEGORIES:
            cell = self._lower_rows[cat][j]
            total = sheet.totals[cat]
            avail = sheet.is_available(cat)

            if view_round > 0:
                self._config_round_view_cell(cell, sheet, cat, view_round, is_current)
            else:
                self._config_lower_cumulative_cell(
                    cell, cat, total, avail, is_current, has_rolled, preview, dice
                )

    def _config_lower_cumulative_cell(
        self, cell, cat, total, avail, is_current, has_rolled, preview, dice
    ):
        if not avail:
            self._config_unavailable_cell(cell, total)
        elif is_current and has_rolled:
            self._update_lower_current_cell(cell, cat, total, preview, dice, is_current)
        elif total > 0:
            self._config_prior_score_cell(cell, total, is_current)
        else:
            self._config_empty_cell(cell, is_current)

    def _update_lower_current_cell(self, cell, cat, total, preview, dice, is_current):
        if cat in preview:
            self._config_preview_in_cell(cell, cat, total, preview)
        else:
            self._config_covered_cell(cell, cat, total, dice, is_current)

    def _config_preview_in_cell(self, cell, cat, total, preview):
        pts = preview[cat]
        display = f"{total}+{pts}" if total and pts else f"(+{pts})"
        cell.config(text=display, bg=SCORE_HOVER, fg=TEXT)

    def _config_covered_cell(self, cell, cat, total, dice, is_current):
        raw = calculate_score(cat, dice)
        label = self._format_lower_label(total, raw)
        cell.config(
            text=label,
            bg=SCORE_AVAIL if not is_current else SCORE_HOVER,
            fg=TEXT_DIM if raw > 0 else TEXT,
        )

    def _format_lower_label(self, total, raw):
        if raw > 0:
            return f"{total} (covered)"
        elif total:
            return str(total)
        else:
            return "(0)"

    def _update_totals(self, sheet, j, view_round):
        if view_round > 0:
            idx = view_round - 1
            ts = (
                sheet.top_score_bonus_history[idx]
                if idx < len(sheet.top_score_bonus_history)
                else 0
            )
            self._top_score_cells[j].config(text=f"+{ts}" if ts > 0 else "—")
            r_total = sheet.round_total(view_round)
            self._total_cells[j].config(text=str(r_total) if r_total > 0 else "0")
        else:
            ts = sheet.top_score_bonus
            self._top_score_cells[j].config(text=f"+{ts}" if ts else "—")
            self._total_cells[j].config(text=str(sheet.grand_total()))

    # –––– Actions

    def _do_roll(self):
        g = self._game
        # If all dice are held, block the roll — player must bank
        if g.rolls_used > 0 and all(g.held):
            return
        g.roll()
        self._refresh()

    def _bank_all(self):
        """Score all available matching categories at once, then advance turn."""
        g = self._game
        recorded = g.score_all_matching()
        if not recorded:
            messagebox.showinfo(
                "No matches to bank",
                "No categories qualified for auto-banking.\n\n"
                "You can either:\n"
                "  • Re-roll the dice (if rolls remain), or\n"
                "  • Click a single category below to score it (even for 0).",
            )
            self._refresh()
            return
        if g.phase == "game_over":
            self._update_scoresheet()
            winners = g.last_top_score_winners
            if winners:
                names = " & ".join(p.name for p in winners)
                self._show_toast(
                    f"🏆  {names} earned Top Score (+50)!", duration_ms=1800
                )
            self.after(2200, lambda: self._on_game_over(g))
        else:
            winners = g.last_top_score_winners
            if winners and g.current_player_index == 0:
                names = " & ".join(p.name for p in winners)
                self._show_toast(f"🏆  {names} earned Top Score (+50)!")
            self._refresh()

    def _toggle_hold(self, index: int):
        self._game.toggle_hold(index)
        self._refresh()

    def _show_toast(self, message: str, duration_ms: int = 2800):
        """Briefly show a floating message over the game screen."""
        toast = tk.Label(
            self,
            text=message,
            font=FONT_HEAD,
            bg=WIN_GOLD,
            fg="#1e1e2e",
            padx=16,
            pady=8,
            relief="flat",
        )
        toast.place(relx=0.5, rely=0.08, anchor="center")
        self.after(duration_ms, toast.destroy)

    def _skip_to_end(self):
        if messagebox.askyesno(
            "Skip remaining turns", "End the game now and go to final results?"
        ):
            self._game.skip_to_end()
            self._update_scoresheet()
            self._on_game_over(self._game)

    def _finish_game(self):
        self._on_game_over(self._game)

    def _score_category(self, category: str):
        if self._game.rolls_used == 0:
            messagebox.showinfo(
                "Roll first", "You must roll at least once before scoring."
            )
            return
        cp = self._game.current_player()
        if not cp.sheet.is_available(category):
            messagebox.showwarning(
                "Already scored", f"'{category}' is already scored this round."
            )
            return

        self._game.score_and_advance(category)

        if self._game.phase == "game_over":
            self._update_scoresheet()
            winners = self._game.last_top_score_winners
            if winners:
                names = " & ".join(p.name for p in winners)
                self._show_toast(
                    f"🏆  {names} earned Top Score (+50)!", duration_ms=1800
                )
            self.after(2200, lambda: self._on_game_over(self._game))
        else:
            # Check if a round just ended (last player just scored → top score awarded)
            winners = self._game.last_top_score_winners
            if winners and self._game.current_player_index == 0:
                names = " & ".join(p.name for p in winners)
                self._show_toast(f"🏆  {names} earned Top Score (+50)!")
            self._refresh()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Result Screen
# ══════════════════════════════════════════════════════════════════════════════


class ResultScreen(tk.Frame):
    def __init__(self, master, game: GameState, on_restart):
        super().__init__(master, bg=BG)
        self._game = game
        self._on_restart = on_restart
        self._build()

    def _build(self):
        tk.Label(self, text="🏆  Game Over!", font=FONT_TITLE, bg=BG, fg=WIN_GOLD).pack(
            pady=(40, 20)
        )

        rankings = self._game.rankings()

        medal_colors = {1: WIN_GOLD, 2: WIN_SILVER, 3: WIN_BRONZE}
        medal_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

        table = tk.Frame(self, bg=PANEL, padx=20, pady=16)
        table.pack(padx=40, pady=10)

        # Header
        for col, txt in enumerate(["Rank", "Player", "Score"]):
            tk.Label(
                table,
                text=txt,
                font=FONT_HEAD,
                bg=PANEL,
                fg=TEXT_HEADER,
                width=14,
                anchor="center",
            ).grid(row=0, column=col, padx=10, pady=6)

        for i, (rank, player) in enumerate(rankings):
            color = medal_colors.get(rank, TEXT)
            icon = medal_icons.get(rank, "  ")
            tk.Label(
                table,
                text=f"{icon} #{rank}",
                font=FONT_NORMAL,
                bg=PANEL,
                fg=color,
                width=14,
                anchor="center",
            ).grid(row=i + 1, column=0, padx=10, pady=5)
            tk.Label(
                table,
                text=player.name,
                font=FONT_NORMAL,
                bg=PANEL,
                fg=color,
                width=14,
                anchor="center",
            ).grid(row=i + 1, column=1, padx=10, pady=5)
            tk.Label(
                table,
                text=str(player.sheet.grand_total()),
                font=FONT_HEAD,
                bg=PANEL,
                fg=color,
                width=14,
                anchor="center",
            ).grid(row=i + 1, column=2, padx=10, pady=5)

        # Score breakdown for top 3
        if len(rankings) >= 1:
            tk.Label(
                self,
                text="Score Breakdown (Top 3)",
                font=FONT_HEAD,
                bg=BG,
                fg=TEXT_HEADER,
            ).pack(pady=(20, 6))
            for rank, player in rankings[:3]:
                color = medal_colors.get(rank, TEXT)
                s = player.sheet
                detail = (
                    f"  {player.name}:  Upper {s.upper_subtotal()}"
                    f" + Lower {s.lower_total()}"
                    f" + Bonus {s.chance_bonus()}"
                    f" + Top Score {s.top_score_bonus}"
                    f"  =  {s.grand_total()}"
                )
                tk.Label(self, text=detail, font=FONT_NORMAL, bg=BG, fg=color).pack()

        make_button(
            self, "🔄  Play Again", self._on_restart, bg=BTN_ROLL, padx=30, pady=10
        ).pack(pady=30)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
