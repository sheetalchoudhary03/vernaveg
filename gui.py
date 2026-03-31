# gui.py (fixed version with Enter key, Profile data, and Result popup)
import customtkinter as ctk
import numpy as np
from tkinter import messagebox, ttk
import tkinter as tk
from logic import TypingLogic
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from datetime import datetime
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import random
import threading
import time
from pathlib import Path

class TypingGUI(ctk.CTk):
    """Professional layout: sidebar navigation + content area with Test/History/Stats/Profile/Settings."""

    def __init__(self, sentences=None, db_path=None):
        super().__init__()
        # appearance - default to "default" mode (very light purple)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("वर्ण वेग — Typing Beyond Limits")
        try:
            self.iconbitmap(str(Path("assets/varna.ico")))
        except Exception:
            pass
        # --- UI style tokens (centralized for consistent look) ---
        # Initialize with default theme (very light purple)
        self._current_theme_mode = "default"
        self._update_color_scheme("default")
        # Font size state (default base size)
        self._base_font_size = 16
        self._font_size_multiplier = 1.0
        self._original_label_fonts = {}
        # On-screen keyboard state
        self._on_screen_keyboard_visible = False
        self._on_screen_keyboard = None
        # Remembered user support
        self._last_user_file = Path("last_user.txt")
        self._last_user = None
        self._load_last_user()
        
        self.fonts = {
            "header": ("Segoe UI", 34, "bold"),
            "subheader": ("Segoe UI", 20, "bold"),
            "normal": ("Segoe UI", 16),
            "large": ("Segoe UI", 24),
            "button": ("Segoe UI", 16, "bold"),
            "mono": ("Consolas", 18),
            "stats": ("Segoe UI", 18),
            "small": ("Segoe UI", 12)
        }
        
        # Font family for style application
        self.font_family = "Segoe UI"
        self.font_size = 16

        # logic
        self.logic = TypingLogic(db_path=db_path)

        # Audio mode variable
        self.audio_mode = ctk.StringVar(value="word")

        # state
        self._test_running = False
        self.current_user = None
        self._after_jobs = []
        
        # Practice mode state
        self.practice_total = 0
        self.practice_correct = 0

        # UI build
        self._build_ui()
        # Ensure the window is maximized once the UI is ready
        self.after(0, self._maximize_window)

    def _cancel_all_jobs(self):
        """Cancel all pending .after() jobs."""
        for job_id in self._after_jobs:
            self.after_cancel(job_id)
        self._after_jobs = []

    def _maximize_window(self):
        """Try several methods to open the window maximized (works across platforms)."""
        try:
            self.state("zoomed")
            return
        except Exception:
            pass

        try:
            self.attributes("-zoomed", True)
            return
        except Exception:
            pass

        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                pass

    def _build_ui(self):
        # App shell with outer border to frame the entire app area
        self.app_shell = ctk.CTkFrame(self, fg_color=self.bg_color, corner_radius=12, border_width=2, border_color=self.accent)
        self.app_shell.pack(fill="both", expand=True, padx=10, pady=10)

        # Sidebar with subtle border
        self.sidebar = ctk.CTkFrame(self.app_shell, width=280, corner_radius=8, fg_color=self.sidebar_bg, border_width=2, border_color=self.accent)
        self.sidebar.pack(side="left", fill="y", padx=(10, 6), pady=10)
        
        # Main content area with border
        self.content = ctk.CTkFrame(self.app_shell, fg_color=self.bg_color, corner_radius=8, border_width=2, border_color=self.accent)
        self.content.pack(side="right", fill="both", expand=True, padx=(6, 10), pady=10)

        # Top header bar (fixed) for better organization
        self.topbar = ctk.CTkFrame(self.content, height=56, fg_color=self.sidebar_bg, corner_radius=0, border_width=0)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)

        # subtle separator under the header
        try:
            sep = ctk.CTkFrame(self.content, height=1, fg_color=self.accent)
            sep.pack(side="top", fill="x")
        except Exception:
            pass

        # Body area under the header to host all pages
        self.content_body = ctk.CTkFrame(self.content, fg_color=self.bg_color)
        self.content_body.pack(side="top", fill="both", expand=True)
        
        # Add chalk dust effect to bottom of sidebar
        dust_frame = ctk.CTkFrame(self.sidebar, height=40, fg_color="transparent")
        dust_frame.pack(side="bottom", fill="x")
        for _ in range(5):
            x = random.randint(10, 270)
            w = random.randint(20, 60)
            h = random.randint(2, 4)
            mark = ctk.CTkFrame(dust_frame, width=w, height=h, fg_color=self.muted)
            mark.place(x=x, y=random.randint(0, 30))

        # Sidebar contents
        self.user_label = ctk.CTkLabel(self.sidebar, text="", font=self.fonts.get('normal'), text_color=self.muted)
        self.user_label.pack(padx=16, pady=(0, 10))

        # full sidebar navigation
        nav_buttons = [
            ("Test", lambda: self._sidebar_navigate('test')),
            ("Practice", lambda: self._sidebar_navigate('practice')),
            ("Listen & Type", lambda: self._sidebar_navigate('audio')),
            ("Game", lambda: self._sidebar_navigate('game')),
            ("Profile", lambda: self._sidebar_navigate('profile')),
            ("Last Results", lambda: self._sidebar_navigate('history')),
            ("Progress Chart", lambda: self._sidebar_navigate('stats')),
            ("Settings", lambda: self._sidebar_navigate('settings')),
        ]
        self.nav_buttons = {}
        for text, cmd in nav_buttons:
            b = ctk.CTkButton(self.sidebar, text=text, width=180, command=cmd, state="disabled")
            try:
                b.configure(fg_color=self.sidebar_bg, hover_color=self.accent_hover, corner_radius=8, text_color='black')
            except Exception:
                pass
            b.pack(pady=6, anchor='w', padx=12)
            self.nav_buttons[text.lower()] = b

        # logout/back button
        self.sidebar_back_btn = ctk.CTkButton(self.sidebar, text="Logout", width=180, command=self._back_to_welcome)
        self._hide_sidebar_nav()
        try:
            self.sidebar.pack_forget()
        except Exception:
            pass

        # quick stats box in sidebar
        self.sidebar_stats = ctk.CTkLabel(self.sidebar, text="No data", anchor="w")
        self.sidebar_stats.pack(side="bottom", fill="x", padx=12, pady=12)

        # build content frames
        self.frames = {}
        for name in ("menu", "welcome", "test", "practice", "game", "history", "stats", "profile", "settings", "audio"):
            f = ctk.CTkFrame(self.content_body, fg_color=self.bg_color)
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.frames[name] = f

        # build each frame
        self._build_welcome_frame(self.frames["welcome"])
        self._build_menu_frame(self.frames["menu"])
        self._build_test_frame(self.frames["test"])
        self._build_history_frame(self.frames["history"])
        self._build_results_frame(self.frames["stats"])
        self._build_profile_frame(self.frames["profile"])
        self._build_settings_frame(self.frames["settings"])
        self._build_practice_frame(self.frames["practice"])
        self._build_game_frame(self.frames["game"])
        self._build_audio_frame(self.frames["audio"])

        # show welcome overlay first
        self.frames["welcome"].lift()
        try:
            self._apply_global_styles()
        except Exception:
            pass

    # Layout helpers
    def _make_header(self, parent, title, back_command=None, pady=(18,10)):
        """Create a standard header row with title and optional Back button plus a thin separator."""
        header_row = ctk.CTkFrame(parent, fg_color=self.sidebar_bg)
        header_row.pack(fill="x", pady=pady, padx=20)
        header = ctk.CTkLabel(header_row, text=title, font=self.fonts.get('header'), text_color=self.text_color)
        header.pack(side="left")
        if back_command is not None:
            try:
                ctk.CTkButton(header_row, text="Back", width=100, command=back_command).pack(side="right")
            except Exception:
                pass
        try:
            sep = ctk.CTkFrame(parent, height=2, fg_color=self.accent)
            sep.pack(fill="x", padx=20, pady=(0,10))
        except Exception:
            pass
        return header_row, header

    def _build_test_frame(self, parent):
        header_row, header = self._make_header(parent, "Typing Test", back_command=self._back_to_menu)

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=40, pady=20)

        # Sentence card
        sentence_card = ctk.CTkFrame(body, corner_radius=10, border_width=2, border_color=self.accent)
        sentence_card.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(sentence_card, text="Sentence", font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 6))
        self.test_sentence_box = ctk.CTkTextbox(sentence_card, height=120, wrap="word", font=self.fonts["large"])
        self.test_sentence_box.pack(fill="x", padx=16, pady=(0, 16))
        self.test_sentence_box.configure(state="disabled", fg_color=self.card_bg, text_color=self.text_color)
        try:
            self.test_sentence_box.tag_config("target_current", background="#FFF3A3", foreground="black")
        except Exception:
            pass

        # Row: typing card + run card
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="both", expand=True)

        typing_card = ctk.CTkFrame(row, corner_radius=10, border_width=2, border_color=self.accent)
        typing_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(typing_card, text="Type here", font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 6))
        self.test_typing_box = ctk.CTkTextbox(typing_card, height=240, font=self.fonts["mono"])
        self.test_typing_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.test_typing_box.configure(state="disabled", fg_color=self.card_bg, text_color=self.text_color)
        self.test_typing_box.bind("<KeyRelease>", self._on_keypress)
        try:
            self.test_typing_box.tag_config("correct", foreground=self.success)
            self.test_typing_box.tag_config("incorrect", foreground=self.error)
            self.test_typing_box.tag_config("current", underline=1)
        except Exception:
            pass
        # controls
        btns = ctk.CTkFrame(typing_card, fg_color="transparent")
        btns.pack(pady=(0, 12))
        self.start_btn = ctk.CTkButton(btns, text="Start", width=120, command=self.start_test)
        self.start_btn.grid(row=0, column=0, padx=6)
        self.end_btn = ctk.CTkButton(btns, text="End", width=120, command=self.end_test)
        self.end_btn.grid(row=0, column=1, padx=6)

        run_card = ctk.CTkFrame(row, width=320, corner_radius=10, border_width=2, border_color=self.accent)
        run_card.pack(side="right", fill="y", padx=(10, 0))
        self.result_label = ctk.CTkLabel(run_card, text="Ready", font=("Segoe UI", 18, "bold"), text_color=self.text_color)
        self.result_label.pack(pady=(16, 8))
        self.run_stats = ctk.CTkLabel(run_card, text="WPM: -\nAccuracy: -\nTime: -", anchor="w", font=self.fonts["normal"], text_color=self.text_color)
        self.run_stats.pack(padx=16, pady=(0, 12))

    def _build_history_frame(self, parent):
        header_row, header = self._make_header(parent, "History", back_command=self._back_to_menu)

        # Filter frame
        filter_frame = ctk.CTkFrame(parent, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(10, 0), padx=20)
        ctk.CTkLabel(filter_frame, text="Filter by Test Type:", font=self.fonts["normal"]).pack(side="left", padx=(0, 10))
        self.history_filter_var = ctk.StringVar(value="all")
        self.history_filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["all", "test", "practice", "game", "audio"],
            variable=self.history_filter_var,
            command=self._on_history_filter_change
        )
        self.history_filter_menu.pack(side="left")

        # Table view
        columns = ("#", "Name", "WPM", "Accuracy", "Time")
        table_frame = ctk.CTkFrame(parent)
        table_frame.pack(fill="both", expand=True, padx=20, pady=8)

        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background="purple", foreground="white")
        style.map("Treeview.Heading", background=[('active', '#6a0dad')])

        self.history_table = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.history_table.heading(col, text=col)
            self.history_table.column(col, anchor="center")

        ysb = ttk.Scrollbar(table_frame, orient='vertical', command=self.history_table.yview)
        self.history_table.configure(yscroll=ysb.set)
        ysb.pack(side='right', fill='y')
        self.history_table.pack(fill='both', expand=True)

        ctk.CTkButton(parent, text="Refresh", command=self._refresh_history, fg_color="purple", text_color="white").pack(pady=(0,8))

    def _build_practice_frame(self, parent):
        header_row, header = self._make_header(parent, "Practice", back_command=self._back_to_menu)
        
        content_split = ctk.CTkFrame(parent)
        content_split.pack(fill="both", expand=True, padx=20, pady=8)
        
        practice_area = ctk.CTkFrame(content_split)
        practice_area.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        history_sidebar = ctk.CTkFrame(content_split, width=200)
        history_sidebar.pack(side="right", fill="y", padx=(10, 0))
        history_sidebar.pack_propagate(False)
        
        ctk.CTkLabel(history_sidebar, text="Word History", font=("Arial", 16, "bold")).pack(pady=(10, 5))
        history_scroll = ctk.CTkScrollableFrame(history_sidebar)
        history_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.practice_history = history_scroll
        
        word_container = ctk.CTkFrame(practice_area, fg_color=self.card_bg,
                                    border_width=1, border_color=self.accent)
        word_container.pack(pady=(40, 20), padx=40, fill="x")
        self.practice_word_label = ctk.CTkLabel(word_container, text="Click 'Start Practice' to begin", 
                                               font=("Segoe UI", 38, "bold"),
                                               text_color=self.highlight)
        self.practice_word_label.pack(pady=30)
        
        self.practice_entry = ctk.CTkEntry(practice_area, width=400, 
                                         font=self.fonts["large"],
                                         height=45)
        self.practice_entry.pack(pady=20)
        self.practice_entry.bind("<KeyRelease>", self._on_practice_type)
        
        self.practice_stats = ctk.CTkLabel(practice_area, 
                                         text="Words: 0 | Correct: 0 | Accuracy: 0%", 
                                         font=self.fonts["stats"])
        self.practice_stats.pack(pady=20)
        
        btn_frame = ctk.CTkFrame(practice_area)
        btn_frame.pack(pady=20)
        self.practice_start_btn = ctk.CTkButton(btn_frame, text="Start Practice", command=self._start_practice)
        self.practice_start_btn.pack(side="left", padx=10)
        self.practice_next_btn = ctk.CTkButton(btn_frame, text="Skip Word", command=lambda: self._next_practice_word(skipped=True))
        self.practice_next_btn.pack(side="left", padx=10)
        self.practice_next_btn.configure(state="disabled")
        self.practice_end_btn = ctk.CTkButton(btn_frame, text="End Session", command=self._end_practice_session, fg_color="#ff6b6b")
        self.practice_end_btn.pack(side="left", padx=10)
        self.practice_end_btn.configure(state="disabled")
        
        instructions = ("Type the word exactly as shown - it will automatically check and advance.\n"
                      "Words include both uppercase and lowercase characters.\n"
                      "Green = correct, Red = incorrect, Grey = skipped")
        ctk.CTkLabel(practice_area, text=instructions, font=("Arial", 12)).pack(pady=20)

    def _build_game_frame(self, parent):
        header_row, header = self._make_header(parent, "Typing Game", back_command=self._back_to_menu)

        game_area = ctk.CTkFrame(parent)
        game_area.pack(fill="both", expand=True, padx=40, pady=20)

        left = ctk.CTkFrame(game_area)
        left.pack(side="left", fill="both", expand=True, padx=(0,20))

        canvas_container = ctk.CTkFrame(left, fg_color=self.card_bg,
                                      border_width=1, border_color=self.accent)
        canvas_container.pack(fill="both", expand=True, pady=(0, 16))
        
        self.game_canvas = tk.Canvas(canvas_container, 
                                   bg=self.card_bg, 
                                   highlightthickness=1,
                                   highlightbackground=self.accent)
        self.game_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        def draw_grid():
            w = self.game_canvas.winfo_width()
            h = self.game_canvas.winfo_height()
            grid_color = self.sidebar_bg
            for x in range(0, w, 40):
                self.game_canvas.create_line(x, 0, x, h, fill=grid_color, width=1)
            for y in range(0, h, 40):
                self.game_canvas.create_line(0, y, w, h, fill=grid_color, width=1)
        
        self.game_canvas.bind('<Configure>', lambda e: draw_grid())

        bottom_bar = ctk.CTkFrame(left, height=100)
        bottom_bar.pack(side="bottom", fill="x")
        center_container = ctk.CTkFrame(bottom_bar)
        center_container.pack(pady=12)

        # Right panel
        right = ctk.CTkFrame(game_area, width=320, corner_radius=8)
        right.pack(side="right", fill="y", padx=(10,0))
        right.pack_propagate(False)

        status_card = ctk.CTkFrame(right, corner_radius=8, fg_color="#111318")
        status_card.pack(pady=(12,12), padx=12, fill="x")
        self.game_score_label = ctk.CTkLabel(status_card, text="Score: 0", font=("Arial", 18, "bold"), text_color=self.text_color)
        self.game_score_label.pack(pady=(12,2))
        self.game_lives_label = ctk.CTkLabel(status_card, text="Lives: ", font=("Arial", 14), text_color=self.text_color)
        self.game_lives_label.pack(pady=(0,12))
        self._render_lives_icons(status_card)

        ctk.CTkLabel(right, text="Difficulty (speed)", font=("Arial", 12)).pack(pady=(8,4))
        self.game_speed = tk.DoubleVar(value=1.0)
        self.game_speed_scale = tk.Scale(right, from_=0.5, to=3.0, resolution=0.1, orient='horizontal', variable=self.game_speed)
        self.game_speed_scale.pack(padx=12)

        ctk.CTkLabel(right, text="Type word and press Enter", font=("Arial", 11)).pack(pady=(12,4))
        self.game_entry = ctk.CTkEntry(center_container, width=520, placeholder_text="Type here", font=("Arial", 18))
        self.game_entry.pack()
        self.game_entry.bind("<Return>", self._on_game_type)

        self.use_overlay_entry = tk.BooleanVar(value=False)
        self.overlay_switch = ctk.CTkSwitch(right, text="Overlay Entry", variable=self.use_overlay_entry, command=self._on_toggle_overlay)
        self.overlay_switch.pack(pady=(6,6))

        self.game_overlay_entry = ctk.CTkEntry(self, width=520, placeholder_text="Type here", font=("Arial", 20))

        btns = ctk.CTkFrame(right)
        btns.pack(pady=12)
        self.game_start_btn = ctk.CTkButton(btns, text="Start Game", width=140, command=self.start_game, fg_color="#2b8cff")
        self.game_start_btn.pack(side="left", padx=6)
        self.game_stop_btn = ctk.CTkButton(btns, text="End Session", width=100, command=self.end_game, fg_color="#ff6b6b")
        self.game_stop_btn.pack(side="left", padx=6)

        ctk.CTkLabel(right, text="Game rules:", font=("Arial", 12, "bold")).pack(pady=(18,4))
        rules = "Words appear from the right and move left. Type a word and press Enter to remove it before it reaches the left edge. Lose a life if a word reaches the left."
        ctk.CTkLabel(right, text=rules, wraplength=260, justify="left", font=("Arial", 10)).pack(padx=8, pady=(0,6))

        # Game state
        self._game_running = False
        self._game_words = []
        self._game_move_job = None
        self._game_spawn_job = None
        self._game_score = 0
        self._game_lives = 5
        self._game_spawn_interval_ms = 2000

    def _build_audio_frame(self, parent):
        # Create a main frame to hold both content and side panel
        main_audio_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_audio_frame.pack(fill="both", expand=True)

        # --- Side Panel for Word Lists ---
        side_panel = ctk.CTkFrame(main_audio_frame, width=250, fg_color=self.sidebar_bg, corner_radius=8, border_width=2, border_color=self.accent)
        side_panel.pack(side="right", fill="y", padx=(10, 0), pady=10)

        ctk.CTkLabel(side_panel, text="Word Lists", font=self.fonts["subheader"]).pack(pady=(15, 10))

        ctk.CTkLabel(side_panel, text="Skipped", font=self.fonts["normal"]).pack(pady=(10, 2))
        self.skipped_words_list = tk.Listbox(side_panel, height=4, bg=self.bg_color, fg="#FFC107", 
                                            selectbackground=self.accent, borderwidth=1, highlightthickness=1, relief="solid")
        self.skipped_words_list.pack(fill="x", padx=15)

        ctk.CTkLabel(side_panel, text="Correct", font=self.fonts["normal"]).pack(pady=(10, 2))
        self.correct_words_list = tk.Listbox(side_panel, height=4, bg=self.bg_color, fg="#4CAF50", 
                                            selectbackground=self.accent, borderwidth=1, highlightthickness=1, relief="solid")
        self.correct_words_list.pack(fill="x", padx=15)

        ctk.CTkLabel(side_panel, text="Seen", font=self.fonts["normal"]).pack(pady=(10, 2))
        self.seen_words_list = tk.Listbox(side_panel, height=4, bg=self.bg_color, fg="#2196F3", 
                                         selectbackground=self.accent, borderwidth=1, highlightthickness=1, relief="solid")
        self.seen_words_list.pack(fill="x", padx=15)

        ctk.CTkLabel(side_panel, text="Wrong", font=self.fonts["normal"]).pack(pady=(10, 2))
        self.wrong_words_list = tk.Listbox(side_panel, height=4, bg=self.bg_color, fg="#F44336", 
                                          selectbackground=self.accent, borderwidth=1, highlightthickness=1, relief="solid")
        self.wrong_words_list.pack(fill="x", padx=15, pady=(0, 15))

        # --- Main Content Area ---
        content_frame = ctk.CTkFrame(main_audio_frame, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True)

        header_row, header = self._make_header(content_frame, "Listen & Type", back_command=self._back_to_menu)

        # Initialize audio session state
        self.audio_start_time = None
        self.audio_correct_words = 0
        self.audio_total_words = 0
        self.audio_done_words = 0
        self.ready_for_next = False

        # Control buttons frame
        control_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        control_frame.pack(pady=15)

        self.play_word_btn = ctk.CTkButton(control_frame, text="▶️ Play Word", command=lambda: self._play_mode('word'), width=120,
                                           font=("Segoe UI", 14, "bold"), fg_color="#4CAF50", hover_color="#45a049")
        self.play_word_btn.pack(side="left", padx=5)

        
        self.replay_audio_btn = ctk.CTkButton(control_frame, text="🔁 Replay", command=self._replay_audio, width=100,
                                             state="disabled", font=("Segoe UI", 14, "bold"), fg_color="#2196F3", hover_color="#1976D2")
        self.replay_audio_btn.pack(side="left", padx=5)
        
        self.stop_audio_btn = ctk.CTkButton(control_frame, text="⏹️ Stop", command=self._stop_audio, width=100,
                                           state="disabled", font=("Segoe UI", 14, "bold"), fg_color="#FF9800", hover_color="#F57C00")
        self.stop_audio_btn.pack(side="left", padx=5)

        # Audio speed control
        speed_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        speed_frame.pack(side="left", padx=15)
        
        ctk.CTkLabel(speed_frame, text="Speed:", font=("Segoe UI", 12)).pack(side="left", padx=5)
        self.audio_speed_var = ctk.StringVar(value="150")
        self.audio_speed_label = ctk.CTkLabel(speed_frame, text="150 WPM", font=("Segoe UI", 12), width=60)
        self.audio_speed_label.pack(side="left", padx=5)
        
        self.audio_speed_slider = ctk.CTkSlider(speed_frame, from_=50, to=250, number_of_steps=20,
                                               command=self._on_audio_speed_change, width=120)
        self.audio_speed_slider.set(150)
        self.audio_speed_slider.pack(side="left", padx=5)

        # Right-aligned buttons
        right_control_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        right_control_frame.pack(side="right", padx=5)
        
        self.show_text_btn = ctk.CTkButton(right_control_frame, text="👁️ Show Text", command=self._show_audio_text, width=120,
                                          font=("Segoe UI", 14, "bold"), fg_color="#607D8B", hover_color="#455A64")
        self.show_text_btn.pack(side="left", padx=5)


        # Audio text display
        self.audio_text_label = ctk.CTkLabel(content_frame, text="", font=self.fonts["large"], wraplength=600, 
                                           fg_color=self.card_bg, corner_radius=10, height=80, justify="center",
                                           text_color=self.text_color)
        self.audio_text_label.pack(pady=15, padx=20, fill="x")

        count_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        count_row.pack(pady=(0, 4), fill="x")
        count_inner = ctk.CTkFrame(count_row, fg_color="transparent")
        count_inner.pack()
        self.skip_btn = ctk.CTkButton(count_inner, text="⏭️ Skip", width=140,
                                      font=("Segoe UI", 14, "bold"), fg_color="#9C27B0", hover_color="#7B1FA2",
                                      text_color="#FFFFFF", command=self._skip_audio_word)
        self.skip_btn.pack(side="left", padx=(0, 10))
        self.audio_count_label = ctk.CTkLabel(count_inner, text="Words done: 0 | Correct: 0/0", font=("Segoe UI", 14, "bold"))
        self.audio_count_label.pack(side="left")

        # Input section
        input_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        input_frame.pack(pady=20)

        self.audio_entry = ctk.CTkEntry(input_frame, width=500, font=self.fonts["large"], height=60,
                                       placeholder_text="Type what you hear and press Enter...",
                                       corner_radius=15, border_width=2)
        self.audio_entry.pack(pady=10)
        self.audio_entry.bind("<Return>", self._check_audio_input)
        self.audio_entry.bind("<KeyRelease>", self._on_audio_entry_change)
        
        # Submit button
        self.submit_btn = ctk.CTkButton(input_frame, text="✅ Submit Answer", command=lambda: self._check_audio_input(None),
                                       width=180, height=45, font=("Segoe UI", 14, "bold"), fg_color="#4CAF50", hover_color="#45a049")
        self.submit_btn.pack(pady=10)

        self.finish_audio_btn = ctk.CTkButton(input_frame, text="🏁 Finish Session", command=self._finish_audio_session,
                                             width=180, height=45, font=("Segoe UI", 14, "bold"), fg_color="#F44336", hover_color="#D32F2F")
        self.finish_audio_btn.pack(pady=(0, 10))

        # Result display
        self.audio_result_label = ctk.CTkLabel(content_frame, text="", font=("Segoe UI", 16, "bold"), height=40,
                                             corner_radius=8, fg_color="transparent")
        self.audio_result_label.pack(pady=10)

        # Progress info
        self.audio_progress_label = ctk.CTkLabel(content_frame, text="🎯 Ready to start! Click ▶ Play Audio to begin.", 
                                              font=self.fonts["normal"], text_color="gray")
        self.audio_progress_label.pack(pady=5)
        
        # Audio status indicator
        self.audio_status_label = ctk.CTkLabel(content_frame, text="🎵 Audio Ready", 
                                              font=("Segoe UI", 18, "bold"), text_color="#4CAF50")
        self.audio_status_label.pack(pady=(0, 15))

    def _update_audio_counts_label(self):
        try:
            self.audio_count_label.configure(text=f"Words done: {getattr(self, 'audio_done_words', 0)} | Correct: {self.audio_correct_words}/{self.audio_total_words}")
        except Exception:
            pass

    def _on_audio_speed_change(self, value):
        """Handle audio speed slider change"""
        speed = int(value)
        self.audio_speed_label.configure(text=f"{speed} WPM")
        self.logic.set_audio_speed(speed)

    def _on_audio_entry_change(self, event):
        """Handle audio entry text changes"""
        # Enable submit button when there's text
        text = self.audio_entry.get().strip()
        if text:
            self.submit_btn.configure(state="normal", fg_color="#4CAF50")
        else:
            self.submit_btn.configure(state="normal", fg_color="#4CAF50")

    def _on_audio_mode_change(self):
        """Handle mode change between word and sentence"""
        # Stop any current audio first
        self._stop_audio()
        # Clear all current state
        self.audio_text_label.configure(text="")
        self.audio_result_label.configure(text="")
        self.audio_entry.delete(0, "end")
        self.current_audio_sentence = None
        self.text_shown = False  # Reset text shown flag
        self.audio_progress_label.configure(text=f"Mode changed to {self.audio_mode.get()}. Click Play Audio to begin.")
        self.audio_status_label.configure(text="🎵 Audio Ready", text_color="#4CAF50")
        # Reset button states
        self.replay_audio_btn.configure(state="disabled")
        # Clear correct words list when manually advancing
        self.correct_words_list.delete(0, tk.END)

    def _play_mode(self, mode):
        self.audio_mode.set(mode)
        self._play_audio()

    def _play_audio(self):
        """Play audio with proper state management and speed control"""
        if not self.audio_start_time:
            self.audio_start_time = time.time()
        try:
            # Cancel any pending auto-play
            if hasattr(self, '_autoplay_id') and self._autoplay_id:
                self.after_cancel(self._autoplay_id)
                self._autoplay_id = None
            
            # Always play word mode
            self.audio_mode.set("word")
            if getattr(self, 'current_audio_sentence', None) and not getattr(self, 'ready_for_next', False):
                text = self.current_audio_sentence
            else:
                text = self.logic.pick_audio_text("word")
                self.current_audio_sentence = text
                self.ready_for_next = False
            
            # Update UI state
            try:
                self.play_word_btn.configure(state="disabled", fg_color="#757575")
            except Exception:
                pass
            self.replay_audio_btn.configure(state="normal" if self.current_audio_sentence else "disabled")
            self.stop_audio_btn.configure(state="normal", fg_color="#FF9800")
            self.audio_entry.delete(0, "end")
            self.audio_entry.configure(state="normal", border_color="#4CAF50")
            self.audio_result_label.configure(text="")
            self.audio_text_label.configure(text="", fg_color=self.card_bg)  # Hide text initially
            self.text_shown = False  # Track if text has been shown
            
            # Update progress
            self.audio_progress_label.configure(text=f"🔊 Playing word: Listen carefully...")
            
            self.audio_status_label.configure(text="🔊 Playing Audio...", text_color="#FF9800")
            
            # Set speaking state and play audio in a separate thread to avoid UI freezing
            self.logic.set_speaking_state(True)
            audio_thread = threading.Thread(target=self._speak_audio, args=(text,), daemon=True)
            audio_thread.start()
        
        except Exception as e:
            self.audio_progress_label.configure(text=f"❌ Error playing audio: {str(e)}")
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
            except Exception:
                pass
            self.stop_audio_btn.configure(state="disabled", fg_color="#FF9800")
            self.audio_status_label.configure(text="❌ Audio Error", text_color="#F44336")

    def _speak_audio(self, text):
        """Speak the audio text in a background thread; marshal UI updates to the main thread."""
        try:
            success = self.logic.speak(text)
            def _on_done():
                if not success:
                    self.audio_progress_label.configure(text="❌ Audio playback failed. Please check your system audio.")
                    self.audio_status_label.configure(text="❌ Playback Failed", text_color="#F44336")
                else:
                    self.audio_status_label.configure(text="✅ Audio Complete", text_color="#4CAF50")
                    self.audio_progress_label.configure(text="🎯 Audio finished! Type what you heard and press Enter or click Submit.")
                # Reset UI state after speaking
                self.logic.set_speaking_state(False)
                try:
                    self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
                except Exception:
                    pass
                self.replay_audio_btn.configure(state="normal" if self.current_audio_sentence else "disabled")
                self.stop_audio_btn.configure(state="disabled", fg_color="#FF9800")
                self.audio_entry.configure(state="normal", border_color="#4CAF50")
                
            self.after(0, _on_done)
        except Exception as e:
            def _on_err():
                self.audio_progress_label.configure(text=f"❌ Audio error: {str(e)}")
                self.audio_status_label.configure(text="❌ Audio Error", text_color="#F44336")
                self.logic.set_speaking_state(False)
                try:
                    self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
                except Exception:
                    pass
                self.replay_audio_btn.configure(state="normal" if self.current_audio_sentence else "disabled")
                self.stop_audio_btn.configure(state="disabled", fg_color="#FF9800")
                self.audio_entry.configure(state="normal", border_color="#4CAF50")
            self.after(0, _on_err)

    def _replay_audio(self):
        """Replay the current audio with improved functionality"""
        if hasattr(self, 'current_audio_sentence') and self.current_audio_sentence:
            # Cancel any pending auto-play
            if hasattr(self, '_autoplay_id') and self._autoplay_id:
                self.after_cancel(self._autoplay_id)
                self._autoplay_id = None
            
            # Stop any current audio first
            self.logic.stop_speaking()
            
            # Update UI state
            try:
                self.play_word_btn.configure(state="disabled", fg_color="#757575")
            except Exception:
                pass
            self.replay_audio_btn.configure(state="disabled", fg_color="#757575")
            self.stop_audio_btn.configure(state="normal", fg_color="#FF9800")
            self.audio_progress_label.configure(text="🔁 Replaying audio... Listen carefully...")
            self.audio_status_label.configure(text="🔁 Replaying...", text_color="#FF9800")
            
            # Clear entry and result for fresh attempt
            self.audio_entry.delete(0, "end")
            self.audio_entry.configure(state="normal", border_color="#4CAF50")
            self.audio_result_label.configure(text="")
            if not self.text_shown:
                self.audio_text_label.configure(text="", fg_color=self.card_bg)
            
            # Set speaking state and replay audio in a separate thread
            self.logic.set_speaking_state(True)
            audio_thread = threading.Thread(target=self._speak_audio, args=(self.current_audio_sentence,), daemon=True)
            audio_thread.start()
        else:
            self.audio_progress_label.configure(text="⚠️ No audio to replay. Click 'Play Audio' first.")
            self.audio_status_label.configure(text="⚠️ Nothing to replay", text_color="#FF9800")

    def _stop_audio(self):
        """Stop the current audio playback with improved state management"""
        try:
            # Stop the audio engine
            self.logic.stop_speaking()
            self.logic.set_speaking_state(False)
            
            # Update UI state
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
            except Exception:
                pass
            self.replay_audio_btn.configure(state="normal" if self.current_audio_sentence else "disabled")
            self.stop_audio_btn.configure(state="disabled", fg_color="#FF9800")
            self.audio_progress_label.configure(text="⏹️ Audio stopped. Click Play Audio to try again.")
            self.audio_status_label.configure(text="⏹️ Stopped", text_color="#757575")
            
            # Enable entry field
            self.audio_entry.configure(state="normal", border_color="#4CAF50")
            
            # Cancel any pending auto-play
            if hasattr(self, '_autoplay_id') and self._autoplay_id:
                self.after_cancel(self._autoplay_id)
                self._autoplay_id = None
                
        except Exception as e:
            self.audio_progress_label.configure(text=f"❌ Error stopping audio: {str(e)}")
            self.audio_status_label.configure(text="❌ Stop Error", text_color="#F44336")

    def _show_audio_text(self):
        """Show the current audio text with improved functionality"""
        if hasattr(self, 'current_audio_sentence') and self.current_audio_sentence:
            # Stop any current audio first
            self.logic.stop_speaking()
            
            # Add to seen list
            self.logic.add_to_seen(self.current_audio_sentence)
            self.seen_words_list.insert(tk.END, self.current_audio_sentence)
            
            # Show the text with better formatting
            self.text_shown = True
            self.audio_text_label.configure(
                text=f"📄 Text: {self.current_audio_sentence}", 
                fg_color="#E3F2FD"
            )
            self.audio_progress_label.configure(text="📄 Text revealed! You can still type what you heard.")
            self.audio_status_label.configure(text="📄 Text Shown", text_color="#2196F3")
            
            # Cancel any pending auto-play
            if hasattr(self, '_autoplay_id') and self._autoplay_id:
                self.after_cancel(self._autoplay_id)
                self._autoplay_id = None
            
            # User may submit; on submit we mark ready_for_next
            
            # Enable entry field for typing
            self.audio_entry.configure(state="normal", border_color="#4CAF50")
            
        else:
            self.audio_text_label.configure(text="⚠️ No audio played yet. Click 'Play Audio' first.")
            self.audio_progress_label.configure(text="⚠️ Click Play Audio to hear the text first.")
            self.audio_status_label.configure(text="⚠️ No Audio", text_color="#FF9800")

    def _skip_audio_word(self):
        """Skip to the next word/sentence with improved functionality"""
        # Cancel any pending auto-play
        if hasattr(self, '_autoplay_id') and self._autoplay_id:
            self.after_cancel(self._autoplay_id)
            self._autoplay_id = None
        
        # Add to skipped list if we have a current word
        if hasattr(self, 'current_audio_sentence') and self.current_audio_sentence:
            self.logic.add_to_skipped(self.current_audio_sentence)
            self.skipped_words_list.insert(tk.END, self.current_audio_sentence)
            self.audio_status_label.configure(text="⏭️ Skipped", text_color="#FF9800")
        
        # Clear UI elements
        self.audio_text_label.configure(text="", fg_color=self.card_bg)
        self.audio_result_label.configure(text="")
        self.audio_entry.delete(0, "end")
        self.audio_progress_label.configure(text="⏭️ Skipped. Loading next...")
        
        # Stop any current audio before skipping
        self._stop_audio()
        self.ready_for_next = True
        try:
            self.audio_done_words += 1
        except Exception:
            self.audio_done_words = 1
        self._update_audio_counts_label()
        self.audio_progress_label.configure(text="⏭️ Skipped. Ready for next. Click ▶ Play Audio.")
        try:
            self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
            self.play_word_btn.focus_set()
        except Exception:
            pass

    def _next_audio_word(self):
        """Move to the next word/sentence with improved functionality"""
        # Cancel any pending auto-play
        if hasattr(self, '_autoplay_id') and self._autoplay_id:
            self.after_cancel(self._autoplay_id)
            self._autoplay_id = None
        
        try:
            self.audio_done_words += 1
        except Exception:
            self.audio_done_words = 1
        self._update_audio_counts_label()

        # Clear current state
        self.audio_text_label.configure(text="", fg_color=self.card_bg)
        self.audio_result_label.configure(text="")
        self.audio_entry.delete(0, "end")
        self.audio_entry.configure(state="normal", border_color="#4CAF50")
        self.text_shown = False
        
        # Reset button states
        self.replay_audio_btn.configure(state="normal" if self.current_audio_sentence else "disabled")
        
        # Update status
        self.audio_status_label.configure(text="🎯 Next Word", text_color="#4CAF50")
        self.audio_progress_label.configure(text="🎯 Loading next word...")
        
        # Play next audio
        self._play_audio()

    def _check_audio_input(self, event):
        """Check audio input with improved feedback and functionality"""
        typed_text = self.audio_entry.get().strip()
        
        if not hasattr(self, 'current_audio_sentence') or not self.current_audio_sentence:
            self.audio_result_label.configure(text="🔊 Play audio first!", text_color="#FF9800", font=("Segoe UI", 14, "bold"))
            self.audio_status_label.configure(text="⚠️ No Audio", text_color="#FF9800")
            return
            
        if not typed_text:
            self.audio_result_label.configure(text="⚠️ Please type something first!", text_color="#FF9800", font=("Segoe UI", 14, "bold"))
            return
        
        # Count this attempt
        self.audio_total_words += 1
        self._update_audio_counts_label()
        
        if typed_text.lower() == self.current_audio_sentence.lower():
            # Correct answer
            self.audio_correct_words += 1
            self.audio_result_label.configure(
                text="🎉 Correct! Well done! 🎉", 
                text_color="#4CAF50", 
                font=("Segoe UI", 16, "bold")
            )
            self.audio_status_label.configure(text="✅ Correct!", text_color="#4CAF50")
            
            # Add to correct list
            self.logic.add_to_seen(self.current_audio_sentence)
            self.correct_words_list.insert(tk.END, self.current_audio_sentence)
            
            self.ready_for_next = True
            try:
                self.audio_done_words += 1
            except Exception:
                self.audio_done_words = 1
            self._update_audio_counts_label()
            self.audio_progress_label.configure(text="✅ Ready for next. Click ▶ Play Audio.")
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
                self.play_word_btn.focus_set()
            except Exception:
                pass
            
        else:
            # Incorrect answer
            self.audio_result_label.configure(
                text="❌ Incorrect! Try again!", 
                text_color="#F44336", 
                font=("Segoe UI", 16, "bold")
            )
            self.audio_status_label.configure(text="❌ Try Again", text_color="#F44336")
            
            # Add to wrong list
            self.logic.add_to_wrong(self.current_audio_sentence)
            self.wrong_words_list.insert(tk.END, self.current_audio_sentence)
            
            # Show correct answer after incorrect attempt
            self.audio_text_label.configure(
                text=f"✏️ Correct: {self.current_audio_sentence}", 
                fg_color="#FFEBEE"
            )
            self.text_shown = True
            
            self.ready_for_next = True
            try:
                self.audio_done_words += 1
            except Exception:
                self.audio_done_words = 1
            self._update_audio_counts_label()
            self.audio_progress_label.configure(text="✅ Ready for next. Click ▶ Play Audio.")
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
                self.play_word_btn.focus_set()
            except Exception:
                pass

    def _finish_audio_session(self):
        """Finish audio session with improved results display"""
        # Cancel any pending auto-play
        if hasattr(self, '_autoplay_id') and self._autoplay_id:
            self.after_cancel(self._autoplay_id)
            self._autoplay_id = None
        
        # Stop any current audio
        self.logic.stop_speaking()
        
        if self.audio_start_time and self.audio_total_words > 0:
            time_taken = time.time() - self.audio_start_time
            wpm = (self.audio_correct_words / (time_taken / 60)) if time_taken > 0 else 0
            accuracy = (self.audio_correct_words / self.audio_total_words) * 100 if self.audio_total_words > 0 else 0

            # Save results
            self.logic.save_result(
                name=self.current_user,
                wpm=wpm,
                accuracy=accuracy,
                time_taken=time_taken,
                test_type='audio'
            )
            self._update_sidebar_stats()
            self._refresh_stats()
            
            # Show results summary
            result_text = f"🎉 Session Complete! 🎉\n"
            result_text += f"📊 Accuracy: {accuracy:.1f}%\n"
            result_text += f"⚡ WPM: {wpm:.1f}\n"
            result_text += f"⏱️ Time: {time_taken:.1f}s\n"
            result_text += f"✅ Correct: {self.audio_correct_words}/{self.audio_total_words}"
            
            self.audio_progress_label.configure(text=result_text)
            self.audio_status_label.configure(text="🎉 Session Complete!", text_color="#4CAF50")
            try:
                messagebox.showinfo("Audio Session Results", result_text)
            except Exception:
                pass
            try:
                self._autoplay_id = self.after(1000, self._prepare_new_audio_session)
                self._after_jobs.append(self._autoplay_id)
            except Exception:
                pass
        else:
            self.audio_progress_label.configure(text="🎯 Session finished. Click Play Audio to start a new one.")
            self.audio_status_label.configure(text="🎵 Audio Ready", text_color="#2196F3")

        # Reset audio session
        self.audio_start_time = None
        self.audio_correct_words = 0
        self.audio_total_words = 0
        self.current_audio_sentence = None
        self.text_shown = False
        self.audio_done_words = 0
        self._update_audio_counts_label()
        
        self._prepare_new_audio_session()

    def _prepare_new_audio_session(self):
        """Reset UI and controls to ready state for a new audio session"""
        try:
            self.audio_text_label.configure(text="", fg_color=self.card_bg)
            self.audio_result_label.configure(text="")
            self.audio_entry.delete(0, "end")
            self.audio_entry.configure(state="normal", border_color="#4CAF50")
            self._update_audio_counts_label()
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
            except Exception:
                pass
            self.replay_audio_btn.configure(state="disabled")
            self.stop_audio_btn.configure(state="disabled", fg_color="#FF9800")
            try:
                self.play_word_btn.configure(state="normal", fg_color="#4CAF50")
            except Exception:
                pass
            
            self.audio_progress_label.configure(text="🎯 Ready to start! Click ▶ Play Word to begin.")
            self.audio_status_label.configure(text="🎵 Audio Ready", text_color="#4CAF50")
            try:
                self.audio_entry.focus_set()
            except Exception:
                pass
            self.ready_for_next = False
        except Exception:
            pass



    def _build_menu_frame(self, parent):
        parent.configure(fg_color=self.bg_color)
        
        header_row, header = self._make_header(parent, "Main Menu", back_command=None, pady=(40,12))

        try:
            header.pack_forget()
            header.pack(side="top")
        except Exception:
            pass

        center_frame = ctk.CTkFrame(parent, fg_color="transparent")
        center_frame.pack(expand=True)

        self.menu_user_label = ctk.CTkLabel(center_frame, text="", font=("Segoe UI", 20, "bold"), text_color=self.text_color)
        self.menu_user_label.pack(pady=(0, 16))

        btns = [
            ("🚀 Start Test", lambda: self.show_test()),
            ("📚 Practice", lambda: self._enter_from_menu('practice')),
            ("🎵 Listen & Type", lambda: self._enter_from_menu('audio')),
            ("🎮 Game", lambda: self._enter_from_menu('game')),
            ("👤 Profile", lambda: self._enter_from_menu('profile')),
            ("⚙️ Settings", lambda: self._enter_from_menu('settings')),
            ("📊 Last Results", lambda: self._enter_from_menu('history')),
            ("📈 Progress Chart", lambda: self._enter_from_menu('stats')),
            ("🚪 Logout", self._handle_logout),
        ]
        for text, cmd in btns:
            if text == "🚪 Logout":
                b = ctk.CTkButton(center_frame, text=text, width=320, command=cmd,
                                   fg_color="#D32F2F", hover_color="#B71C1C", text_color="#FFFFFF")
            else:
                b = ctk.CTkButton(center_frame, text=text, width=320, command=cmd)
            b.pack(pady=10)
        spacer = ctk.CTkFrame(parent, height=20, fg_color="transparent")
        spacer.pack()

    def _build_welcome_frame(self, parent):
        try:
            parent.configure(fg_color=self.bg_color)
        except Exception:
            parent.configure(fg_color="#571E7C")

        # Compact centered container (no scrolling) so the page fits without overflow
        center_container = ctk.CTkFrame(parent, fg_color="transparent")
        center_container.pack(fill="both", expand=True)

        # Header area (outside the login box)
        welcome_card = ctk.CTkFrame(
            center_container,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            border_color=self.accent
        )
        try:
            welcome_card.configure(width=720)
        except Exception:
            pass
        # Compact padding so header sits above the login box
        welcome_card.pack(padx=12, pady=(12, 4), fill="x")

        # Remove large illustration to save vertical space

        header_frame = ctk.CTkFrame(welcome_card, fg_color="transparent")
        header_frame.pack(pady=(10, 6))

        ctk.CTkLabel(header_frame,
                    text="Welcome",
                    font=("Segoe UI", 30, "bold"),
                    text_color="#63258D").pack()

        ctk.CTkLabel(header_frame,
                    text="वर्ण वेग — Typing Beyond Limits",
                    font=("Segoe UI", 20,"bold"),
                    text_color="#63258D").pack(pady=(6,0))

        stars = "｡⁠◕⁠‿⁠◕⁠｡"
        ctk.CTkLabel(header_frame,
                    text=stars,
                    font=("Segoe UI", 18),
                    text_color=self.text_color).pack()

        try:
            ctk.CTkFrame(welcome_card, height=1, fg_color=self.accent).pack(fill="x", padx=12, pady=(6, 10))
        except Exception:
            pass

        # Centered, fixed-width login box (like the reference)
        login_frame = ctk.CTkFrame(
            center_container,
            fg_color= "#571E7C",
            corner_radius=12,
            border_width=1,
            border_color=self.accent
        )
        try:
            login_frame.configure(width=520)
        except Exception:
            pass
        try:
            login_frame.pack_propagate(False)
        except Exception:
            pass
        login_frame.pack(pady=8)

        ctk.CTkLabel(login_frame,
                     text="LOGIN",
                     font=("Segoe UI", 18, "bold"),
                     text_color=self.text_color).pack(pady=(8, 4))
        ctk.CTkLabel(login_frame,
                     text="Enter username and password to log in.",
                     font=("Segoe UI", 12),
                     text_color=self.text_color).pack(padx=12, pady=(0, 6))

        # Inner content area to keep consistent spacing
        inner = ctk.CTkFrame(login_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 8))

        # Form rows with icons (reference-style)
        form = ctk.CTkFrame(inner, fg_color="transparent")
        form.pack(fill="x")
        try:
            form.grid_columnconfigure(1, weight=1)
        except Exception:
            pass

        # Username row
        user_icon = ctk.CTkLabel(form, text="👤", width=30, font=("Segoe UI", 16))
        user_icon.grid(row=0, column=0, padx=(0, 10), pady=(0, 8), sticky="w")
        self.login_username = ctk.CTkEntry(
            form, height=36,
            placeholder_text="Enter username",
            font=("Segoe UI", 13)
        )
        self.login_username.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        try:
            if getattr(self, "_last_user", None):
                self.login_username.insert(0, self._last_user)
        except Exception:
            pass
        
        # Password row
        lock_icon = ctk.CTkLabel(form, text="🔒", width=30, font=("Segoe UI", 16))
        lock_icon.grid(row=1, column=0, padx=(0, 10), pady=(0, 8), sticky="w")
        self.login_password = ctk.CTkEntry(
            form, height=36,
            placeholder_text="Enter password",
            show="*",
            font=("Segoe UI", 13)
        )
        self.login_password.grid(row=1, column=1, sticky="ew", pady=(0, 8))
        self.login_password.bind("<Return>", lambda e: self._login_submit())

        # Options row
        options_row = ctk.CTkFrame(inner, fg_color="transparent")
        options_row.pack(fill="x", pady=(0, 2))
        self.remember_me = ctk.CTkCheckBox(options_row, text="Remember me", font=("Segoe UI", 12))
        self.remember_me.pack(side="left", padx=(0, 8))
        ctk.CTkButton(options_row,
                      text="Forgot Password",
                      width=140,
                      font=("Segoe UI", 12),
                      fg_color=self.sidebar_bg,
                      hover_color=self.accent_hover,
                      command=self._forgot_password).pack(side="right")

        ctk.CTkButton(inner,
                      text="Log In",
                      width=360,
                      font=("Segoe UI", 13, "bold"),
                      fg_color=self.accent,
                      hover_color=self.accent_hover,
                      command=self._login_submit).pack(pady=(6, 4))

        ctk.CTkButton(center_container,
                      text="Log In",
                      width=180,
                      font=("Segoe UI", 12, "bold"),
                      fg_color=self.accent,
                      hover_color=self.accent_hover,
                      text_color="#FFFFFF",
                      command=self._login_submit).pack(pady=(6, 6))

        # Create user dialog trigger placed outside the login box
        ctk.CTkButton(center_container,
                      text="Create new user",
                      width=180,
                      font=("Segoe UI", 12),
                      fg_color=self.sidebar_bg,
                      hover_color=self.accent_hover,
                      text_color=self.text_color,
                      command=self._open_create_account_dialog).pack(pady=(6, 10))

        ctk.CTkButton(center_container,
                      text="Admin Login",
                      width=180,
                      font=("Segoe UI", 12),
                      fg_color="#D32F2F",
                      hover_color="#B71C1C",
                      text_color="#FFFFFF",
                      command=self._open_admin_login).pack(pady=(0, 10))

    def _populate_existing_profiles(self):
        self._existing_listbox.delete(0, tk.END)
        try:
            names = self.logic.get_all_users()
        except Exception:
            rows = self.logic.get_history(limit=1000)
            names = []
            for r in rows:
                if r[0] not in names:
                    names.append(r[0])
        for n in names:
            self._existing_listbox.insert(tk.END, n)

    def _welcome_continue(self):
        name = self.welcome_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name required", "Please enter your name or choose an existing profile.")
            return
        self._set_active_user(name)

    def _welcome_use_selected(self):
        sel = self._existing_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Please select a profile from the list.")
            return
        name = self._existing_listbox.get(sel[0])
        self._set_active_user(name)

    def _login_submit(self):
        """Verify login credentials and proceed to the app."""
        username = (self.login_username.get() if hasattr(self, 'login_username') else '').strip()
        password = (self.login_password.get() if hasattr(self, 'login_password') else '').strip()
        if not username or not password:
            messagebox.showwarning("Login", "Please enter username and password.")
            return
        # Check if user exists
        exists = False
        try:
            exists = self.logic.get_pass_key(username) is not None
        except Exception:
            exists = False

        if not exists:
            messagebox.showinfo("Login", "User not found. Please use Create Account.")
            return

        ok = False
        try:
            ok = self.logic.verify_user(username, password)
        except Exception:
            ok = False
        if ok:
            try:
                if hasattr(self, 'remember_me') and self.remember_me.get():
                    self._save_last_user(username)
                else:
                    self._clear_last_user()
            except Exception:
                pass
            self._set_active_user(username)
        else:
            messagebox.showerror("Login", "Invalid username or password.")

    def _open_create_account_dialog(self):
        """Open a compact modal to create a new user without cluttering the page."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create User")
        try:
            dialog.geometry("420x260")
        except Exception:
            pass
        dialog.transient(self)
        dialog.grab_set()

        container = ctk.CTkFrame(dialog, corner_radius=12, border_width=1, border_color=self.accent)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(container, text="Create Account", font=("Segoe UI", 18, "bold"), text_color=self.text_color).pack(pady=(10, 6))

        form = ctk.CTkFrame(container, fg_color="transparent")
        form.pack(fill="x", padx=12, pady=(6, 6))
        try:
            form.grid_columnconfigure(1, weight=1)
        except Exception:
            pass

        ctk.CTkLabel(form, text="👤", width=28, font=("Segoe UI", 14)).grid(row=0, column=0, padx=(0,8), pady=(0,6), sticky="w")
        su = ctk.CTkEntry(form, height=34, placeholder_text="Username", font=("Segoe UI", 12))
        su.grid(row=0, column=1, sticky="ew", pady=(0,6))

        ctk.CTkLabel(form, text="🔒", width=28, font=("Segoe UI", 14)).grid(row=1, column=0, padx=(0,8), pady=(0,6), sticky="w")
        sp = ctk.CTkEntry(form, height=34, placeholder_text="Password", show="*", font=("Segoe UI", 12))
        sp.grid(row=1, column=1, sticky="ew", pady=(0,6))

        info_text = ctk.CTkLabel(form, text="A pass key will be generated.", font=("Segoe UI", 12))
        info_text.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0,6))

        def do_create():
            username = su.get().strip()
            password = sp.get().strip()
            if not username or not password:
                messagebox.showwarning("Create Account", "Please fill all fields.")
                return
            success, pass_key = False, None
            try:
                success, pass_key = self.logic.add_user(username, password)
            except Exception:
                success, pass_key = False, None
            if success:
                try:
                    if hasattr(self, 'remember_me') and self.remember_me.get():
                        self._save_last_user(username)
                except Exception:
                    pass
                messagebox.showinfo("Welcome", f"Account created. Your pass key: {pass_key}\nKeep it safe.")
                dialog.destroy()
                self._set_active_user(username)
            else:
                messagebox.showerror("Create Account", "Username already exists. Please choose another.")

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(pady=(6, 10))
        ctk.CTkButton(btns, text="Create", width=120, fg_color=self.accent, hover_color=self.accent_hover,
                      command=do_create).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancel", width=120, command=dialog.destroy).pack(side="left", padx=6)

    def _create_account_submit(self):
        username = (self.create_username.get() if hasattr(self, 'create_username') else '').strip()
        password = (self.create_password.get() if hasattr(self, 'create_password') else '').strip()
        if not username or not password:
            messagebox.showwarning("Create Account", "Please fill all fields.")
            return
        success, pass_key = False, None
        try:
            success, pass_key = self.logic.add_user(username, password)
        except Exception:
            success, pass_key = False, None
        if success:
            try:
                if hasattr(self, 'remember_me') and self.remember_me.get():
                    self._save_last_user(username)
            except Exception:
                pass
            messagebox.showinfo("Welcome", f"Account created. Your pass key: {pass_key}\nKeep it safe.")
            self._set_active_user(username)
        else:
            messagebox.showerror("Create Account", "Username already exists. Please choose another.")

    def _forgot_password(self):
        """Reset password using pass key verification."""
        win = ctk.CTkToplevel(self)
        win.title("Forgot Password")
        win.geometry("360x280")
        win.transient(self)
        win.grab_set()
        frame = ctk.CTkFrame(win, corner_radius=12, border_width=1, border_color=self.accent)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frame, text="Verify with pass key", font=("Segoe UI", 16, "bold"), text_color=self.text_color).pack(pady=(12, 8))
        u = ctk.CTkEntry(frame, width=280, height=36, placeholder_text="Username")
        u.pack(pady=(0, 8))
        try:
            if hasattr(self, 'login_username'):
                u.insert(0, self.login_username.get())
        except Exception:
            pass
        color = ctk.CTkEntry(frame, width=280, height=36, placeholder_text="Pass Key")
        color.pack(pady=(0, 8))
        newpw = ctk.CTkEntry(frame, width=280, height=36, placeholder_text="New Password", show="*")
        newpw.pack(pady=(0, 12))
        def _do_reset():
            uu = u.get().strip(); fav = color.get().strip(); npw = newpw.get().strip()
            if not uu or not fav or not npw:
                messagebox.showwarning("Reset", "Please fill all fields.")
                return
            ok = False
            try:
                ok = self.logic.reset_password_with_passkey(uu, fav, npw)
            except Exception:
                ok = False
            if ok:
                messagebox.showinfo("Reset", "Password updated.")
                win.destroy()
            else:
                messagebox.showerror("Reset", "Verification failed or user not found.")
        ctk.CTkButton(frame, text="Update", command=_do_reset, fg_color=self.accent, hover_color=self.accent_hover).pack()

    def _open_admin_login(self):
        win = ctk.CTkToplevel(self)
        win.title("Admin Login")
        win.geometry("360x220")
        win.transient(self)
        win.grab_set()
        frm = ctk.CTkFrame(win, corner_radius=12, border_width=1, border_color=self.accent)
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frm, text="Admin Login", font=("Segoe UI", 18, "bold"), text_color=self.text_color).pack(pady=(12,8))
        u = ctk.CTkEntry(frm, width=280, height=36, placeholder_text="Username")
        u.pack(pady=(0,8))
        p = ctk.CTkEntry(frm, width=280, height=36, placeholder_text="Password", show="*")
        p.pack(pady=(0,12))
        def go():
            uu = u.get().strip(); pp = p.get().strip()
            if uu == "sheetal" and pp == "12345":
                win.destroy()
                self._open_admin_panel()
            else:
                messagebox.showerror("Admin", "Invalid credentials")
        ctk.CTkButton(frm, text="Log In", command=go, fg_color="#D32F2F", hover_color="#B71C1C").pack()

    def _open_admin_panel(self):
        win = ctk.CTkToplevel(self)
        win.title("Admin Panel")
        try:
            win.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            win.geometry(f"{sw}x{max(600, sh-80)}+0+0")
            win.resizable(True, True)
        except Exception:
            pass
        win.transient(self)
        win.grab_set()
        container = ctk.CTkFrame(win, corner_radius=12, border_width=1, border_color=self.accent)
        container.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(container, text="Users Overview", font=("Segoe UI", 20, "bold"), text_color=self.text_color).pack(pady=(8,6))
        table_wrap = ctk.CTkFrame(container)
        table_wrap.pack(fill="both", expand=True)
        cols = ("Username", "Pass Key", "Password Hash", "Total Test", "Practice", "Game", "Audio", "Edit", "Delete")
        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        tv = ttk.Treeview(table_wrap, columns=cols, show="headings")
        for c in cols:
            tv.heading(c, text=c)
            w = 120
            if c == "Password Hash":
                w = 220
            if c in ("Edit", "Delete"):
                w = 70
            tv.column(c, anchor="center", width=w)
        ysb = ttk.Scrollbar(table_wrap, orient='vertical', command=tv.yview)
        tv.configure(yscroll=ysb.set)
        ysb.pack(side='right', fill='y')
        tv.pack(fill='both', expand=True)

        def _adjust_columns():
            try:
                tot = max(800, tv.winfo_width())
                # Fixed widths for action icons
                edit_w = 70
                del_w = 70
                ph_w = int(tot * 0.28)
                user_w = int(tot * 0.18)
                pk_w = int(tot * 0.14)
                remain = tot - (edit_w + del_w + ph_w + user_w + pk_w)
                each = int(remain / 4)
                tv.column("Username", width=max(120, user_w))
                tv.column("Pass Key", width=max(100, pk_w))
                tv.column("Password Hash", width=max(180, ph_w))
                tv.column("Total Test", width=max(90, each))
                tv.column("Practice", width=max(90, each))
                tv.column("Game", width=max(90, each))
                tv.column("Audio", width=max(90, each))
                tv.column("Edit", width=edit_w)
                tv.column("Delete", width=del_w)
            except Exception:
                pass

        tv.bind('<Configure>', lambda e: _adjust_columns())
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(pady=(8,0))
        def refresh():
            for r in tv.get_children():
                tv.delete(r)
            try:
                rows = self.logic.get_all_user_stats()
            except Exception:
                rows = []
            for u, pk, ph, t, pr, g, a in rows:
                tv.insert("", "end", values=(u, pk or "", ph or "", t, pr, g, a, "✏️", "🗑️"))

        # Bottom bar with Add User and Refresh
        bottom_bar = ctk.CTkFrame(container, fg_color="transparent")
        bottom_bar.pack(pady=(8,8))
        def add_user():
            d = ctk.CTkToplevel(win)
            d.title("Add User")
            d.geometry("360x220")
            frm = ctk.CTkFrame(d, corner_radius=12, border_width=1, border_color=self.accent)
            frm.pack(fill="both", expand=True, padx=16, pady=16)
            ctk.CTkLabel(frm, text="Add User", font=("Segoe UI", 18, "bold"), text_color=self.text_color).pack(pady=(10,6))
            eu = ctk.CTkEntry(frm, width=280, height=36, placeholder_text="Username")
            eu.pack(pady=(0,8))
            ep = ctk.CTkEntry(frm, width=280, height=36, placeholder_text="Password", show="*")
            ep.pack(pady=(0,12))
            def create():
                uu = eu.get().strip(); pw = ep.get().strip()
                if not uu or not pw:
                    messagebox.showwarning("Add User", "Enter username and password")
                    return
                ok, pk = self.logic.add_user(uu, pw)
                if ok:
                    messagebox.showinfo("Added", f"User added. Pass key: {pk}")
                    d.destroy()
                    refresh()
                else:
                    messagebox.showerror("Add User", "Username exists or error")
            ctk.CTkButton(frm, text="Create", command=create, fg_color=self.accent, hover_color=self.accent_hover).pack()
        ctk.CTkButton(bottom_bar, text="Add User", command=add_user, fg_color=self.accent, hover_color=self.accent_hover).pack(side="left", padx=6)
        ctk.CTkButton(bottom_bar, text="Refresh", command=refresh, fg_color=self.accent, hover_color=self.accent_hover).pack(side="left", padx=6)

        # Row actions: click on Actions column to Edit/Delete
        def edit_user_row(row_id):
            vals = tv.item(row_id, 'values')
            old_username = vals[0]
            d = ctk.CTkToplevel(win)
            d.title("Edit User")
            d.geometry("360x260")
            frm = ctk.CTkFrame(d, corner_radius=12, border_width=1, border_color=self.accent)
            frm.pack(fill="both", expand=True, padx=16, pady=16)
            ctk.CTkLabel(frm, text="Edit User", font=("Segoe UI", 18, "bold"), text_color=self.text_color).pack(pady=(10,6))
            eu = ctk.CTkEntry(frm, width=280, height=36)
            eu.insert(0, old_username)
            eu.pack(pady=(0,8))
            ep = ctk.CTkEntry(frm, width=280, height=36, placeholder_text="New Password (optional)", show="*")
            ep.pack(pady=(0,12))
            def update():
                new_username = eu.get().strip()
                new_password = ep.get().strip()
                if new_username and new_username != old_username:
                    ok = self.logic.admin_update_username(old_username, new_username)
                    if not ok:
                        messagebox.showerror("Edit", "Username update failed")
                        return
                    old_username_local = new_username
                else:
                    old_username_local = old_username
                if new_password:
                    ok2 = self.logic.reset_password(old_username_local, new_password)
                    if not ok2:
                        messagebox.showerror("Edit", "Password update failed")
                        return
                messagebox.showinfo("Edit", "Updated")
                d.destroy()
                refresh()
            ctk.CTkButton(frm, text="Update", command=update, fg_color=self.accent, hover_color=self.accent_hover).pack()

        def delete_user_row(row_id):
            vals = tv.item(row_id, 'values')
            username = vals[0]
            if not messagebox.askyesno("Delete", f"Delete user '{username}' and their results?"):
                return
            ok = self.logic.admin_delete_user(username)
            if ok:
                messagebox.showinfo("Delete", "Deleted")
                refresh()
            else:
                messagebox.showerror("Delete", "Delete failed")

        def on_click(event):
            region = tv.identify("region", event.x, event.y)
            if region != "cell":
                return
            row_id = tv.identify_row(event.y)
            col = tv.identify_column(event.x)
            if not row_id:
                return
            edit_idx = cols.index("Edit") + 1
            del_idx = cols.index("Delete") + 1
            if col == f"#{edit_idx}":
                edit_user_row(row_id)
            elif col == f"#{del_idx}":
                delete_user_row(row_id)
        tv.bind("<ButtonRelease-1>", on_click)

        refresh()

    # --- remember me helpers ---
    def _load_last_user(self):
        try:
            if self._last_user_file.exists():
                self._last_user = self._last_user_file.read_text(encoding="utf-8").strip() or None
        except Exception:
            self._last_user = None

    def _save_last_user(self, username: str):
        try:
            self._last_user_file.write_text(username, encoding="utf-8")
            self._last_user = username
        except Exception:
            pass

    def _clear_last_user(self):
        try:
            if self._last_user_file.exists():
                self._last_user_file.unlink()
        except Exception:
            pass

    def _admin_login(self):
        """Handle admin login with username and password validation."""
        admin_dialog = ctk.CTkToplevel(self)
        admin_dialog.title("Admin Login")
        admin_dialog.geometry("400x250")
        admin_dialog.resizable(False, False)
        admin_dialog.transient(self)
        admin_dialog.grab_set()
        
        admin_dialog.geometry("+%d+%d" % (
            self.winfo_x() + (self.winfo_width() - 400) // 2,
            self.winfo_y() + (self.winfo_height() - 250) // 2
        ))
        
        login_frame = ctk.CTkFrame(admin_dialog)
        login_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(login_frame, text="Admin Login", 
                    font=("Segoe UI", 18, "bold")).pack(pady=(10, 20))
        
        ctk.CTkLabel(login_frame, text="Username:").pack(anchor="w", padx=10)
        username_entry = ctk.CTkEntry(login_frame, width=300, placeholder_text="Enter admin username")
        username_entry.pack(pady=(0, 10))
        username_entry.focus()
        
        ctk.CTkLabel(login_frame, text="Password:").pack(anchor="w", padx=10)
        password_entry = ctk.CTkEntry(login_frame, width=300, placeholder_text="Enter admin password", show="*")
        password_entry.pack(pady=(0, 20))
        
        def validate_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if username == "SheetalChoudhary" and password == "Shree jii":
                admin_dialog.destroy()
                self._set_active_user("Admin")
                messagebox.showinfo("Login Success", "Welcome, Admin! You have full access to all features.")
            else:
                messagebox.showerror("Login Failed", "Invalid admin credentials. Please try again.")
                username_entry.delete(0, tk.END)
                password_entry.delete(0, tk.END)
                username_entry.focus()
        
        button_frame = ctk.CTkFrame(login_frame)
        button_frame.pack(pady=(0, 10))
        
        ctk.CTkButton(button_frame, text="Login", command=validate_login, 
                     fg_color=self.accent, hover_color=self.accent_hover).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=admin_dialog.destroy).pack(side="left", padx=5)
        
        admin_dialog.bind('<Return>', lambda e: validate_login())

    def _set_active_user(self, name: str):
        """Set the active user for the session."""
        self.current_user = name
        for b in self.nav_buttons.values():
            try:
                b.configure(state="normal")
            except Exception:
                pass
        try:
            self.user_label.configure(text=f"User: {name}")
        except Exception:
            pass
        try:
            if hasattr(self, 'settings_user_info'):
                self.settings_user_info.configure(text=f"Logged in as: {name}")
        except Exception:
            pass
        self.frames["welcome"].lower()
        self.frames["menu"].lift()
        self._hide_sidebar_nav()
        try:
            if hasattr(self, 'menu_user_label'):
                self.menu_user_label.configure(text=f"Hello, {name}")
        except Exception:
            pass
        self._update_sidebar_stats()

    def _sidebar_navigate(self, target_frame: str):
        """Handle clicks from the sidebar navigation."""
        if not self.current_user:
            messagebox.showwarning("Name required", "Please select / enter your user from the welcome screen before proceeding.")
            return
        self._show_sidebar_nav()
        if target_frame == 'test':
            self.show_test()
        elif target_frame == 'practice':
            self._hide_all(); self.frames['practice'].lift()
        elif target_frame == 'game':
            self._hide_all(); self.frames['game'].lift()
        elif target_frame == 'profile':
            self.show_profile()
        elif target_frame == 'history':
            self.show_history_frame()
        elif target_frame == 'stats':
            self.show_stats()
        elif target_frame == 'settings':
            self.show_settings()
        else:
            self._hide_all()
            if target_frame in self.frames:
                self.frames[target_frame].lift()
        
        self.after(100, self._auto_focus_input_field, target_frame)

    def _enter_from_menu(self, frame_name):
        if not self.current_user:
            messagebox.showwarning("Name required", "Please select / enter your user from the welcome screen before proceeding.")
            return
        self._show_sidebar_nav()
        if frame_name == 'history':
            self.show_history_frame()
        elif frame_name == 'stats':
            self.show_stats()
        elif frame_name == 'profile':
            self.show_profile()
        elif frame_name == 'settings':
            self.show_settings()
        elif frame_name == 'practice':
            self._hide_all(); self.frames['practice'].lift()
        elif frame_name == 'game':
            self._hide_all(); self.frames['game'].lift()
        else:
            self._hide_all(); self.frames[frame_name].lift()

    def _back_to_welcome(self):
        self.frames["menu"].lower()
        self.frames["welcome"].lift()
        self._hide_sidebar_nav()
        try:
            self.sidebar.pack_forget()
        except Exception:
            pass

    def _back_to_menu(self):
        """Navigate back to the main menu and hide the sidebar navigation."""
        self._hide_all()
        self.frames["menu"].lift()
        self._hide_sidebar_nav()
        try:
            self.sidebar.pack_forget()
        except Exception:
            pass

    def _hide_sidebar_nav(self):
        for b in getattr(self, 'nav_buttons', {}).values():
            try:
                b.pack_forget()
            except Exception:
                pass
        try:
            self.sidebar_back_btn.pack_forget()
        except Exception:
            pass

    def _show_sidebar_nav(self):
        try:
            if not self.sidebar.winfo_ismapped():
                self.sidebar.pack(side="left", fill="y", padx=(10, 6), pady=10)
        except Exception:
            pass
        for text, b in getattr(self, 'nav_buttons', {}).items():
            try:
                b.pack(pady=6)
            except Exception:
                pass
        try:
            self.sidebar_back_btn.pack(pady=(12, 6))
        except Exception:
            pass

    def _build_results_frame(self, parent):
        header_row, header = self._make_header(parent, "Typing Success Tracker", back_command=self._back_to_menu)

        content = ctk.CTkScrollableFrame(parent)
        content.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        
        top_stats = ctk.CTkFrame(content, fg_color="transparent")
        top_stats.pack(fill="x", pady=(20, 30), padx=20)
        
        speed_frame = ctk.CTkFrame(top_stats, fg_color=self.accent, corner_radius=8, border_width=2, border_color="#6846FF")
        speed_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(speed_frame, text="Average typing speed (CPM)",
                    font=self.fonts["subheader"],
                    text_color="white").pack(pady=(10, 5))
        
        self.avg_speed_label = ctk.CTkLabel(speed_frame, text="80 sig/min",
                                          font=("Segoe UI", 24, "bold"),
                                          text_color="white")
        self.avg_speed_label.pack(pady=(0, 10))
        
        time_frame = ctk.CTkFrame(top_stats, fg_color=self.accent, corner_radius=8, border_width=2, border_color="#6846FF")
        time_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(time_frame, text="Average time (seconds)",
                    font=self.fonts["subheader"],
                    text_color="white").pack(pady=(10, 5))
        
        self.avg_time_label = ctk.CTkLabel(time_frame, text="45 seconds",
                                         font=("Segoe UI", 24, "bold"),
                                         text_color="white")
        self.avg_time_label.pack(pady=(0, 10))

        # Filter dropdown
        filter_frame = ctk.CTkFrame(content, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(10, 0), padx=20)
        ctk.CTkLabel(filter_frame, text="Filter by Test Type:", font=self.fonts["normal"]).pack(side="left", padx=(0, 10))
        self.stats_filter_var = ctk.StringVar(value="all")
        self.stats_filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["all", "test", "practice", "game", "audio"],
            variable=self.stats_filter_var,
            command=self._on_stats_filter_change
        )
        self.stats_filter_menu.pack(side="left")

        self.conclusion_label = ctk.CTkLabel(content, text="", font=("Segoe UI", 16, "bold"), text_color=self.text_color)
        self.conclusion_label.pack(pady=(0, 8))
        
        charts_frame = ctk.CTkFrame(content)
        charts_frame.pack(fill="both", expand=True, pady=(10,0), padx=20)

        plt.style.use('default')
        self.stats_figure, axes_grid = plt.subplots(2, 2, figsize=(12, 8), sharex=False)
        self.stats_axes = np.array(axes_grid).flatten()
        
        # Enhanced chart styling
        for ax in self.stats_axes:
            ax.set_facecolor('#F8F9FA')  # Light background
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)  # Subtle grid
            ax.tick_params(colors='black', labelsize=10)
            # Remove top and right spines for cleaner look
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_linewidth(1.5)
            ax.spines['left'].set_linewidth(1.5)
        
        # Enhanced titles with better styling
        self.stats_axes[0].set_title('WPM Trend', fontsize=14, fontweight='bold', pad=15)
        self.stats_axes[1].set_title('Accuracy Trend', fontsize=14, fontweight='bold', pad=15)
        self.stats_axes[2].set_title('Time per Test (s)', fontsize=14, fontweight='bold', pad=15)
        self.stats_axes[3].set_title('Daily Progress (Tests per Day)', fontsize=14, fontweight='bold', pad=15)
        
        self.stats_axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        self.stats_axes[2].tick_params(axis='x', rotation=30)
        self.stats_axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        self.stats_axes[3].tick_params(axis='x', rotation=30)

        self.stats_canvas = FigureCanvasTkAgg(self.stats_figure, master=charts_frame)
        self.stats_canvas.get_tk_widget().pack(fill="both", expand=True)
        try:
            self.stats_figure.tight_layout()
        except Exception:
            pass

    def _on_stats_filter_change(self, choice):
        self._refresh_stats()

    def _build_profile_frame(self, parent):
        _, header = self._make_header(parent, "Profile", back_command=self._back_to_menu)
        
        scroll_frame = ctk.CTkScrollableFrame(parent)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.profile_user_section = ctk.CTkFrame(scroll_frame, corner_radius=12, border_width=2, border_color=self.accent)
        self.profile_user_section.pack(fill="x", padx=20, pady=(0, 20))
        
        self.profile_user_label = ctk.CTkLabel(self.profile_user_section, 
                                             text="User: Not logged in",
                                             font=self.fonts["header"], 
                                             text_color=self.text_color)
        self.profile_user_label.pack(pady=(20, 10))
        
        self.profile_stats_section = ctk.CTkFrame(scroll_frame, corner_radius=12, border_width=2, border_color=self.accent)
        self.profile_stats_section.pack(fill="x", padx=20, pady=(0, 20))
        
        stats_header = ctk.CTkLabel(self.profile_stats_section, 
                                   text="Statistics Overview",
                                   font=self.fonts["subheader"], 
                                   text_color=self.text_color)
        stats_header.pack(pady=(15, 10))
        
        stats_grid = ctk.CTkFrame(self.profile_stats_section, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        self.profile_total_tests = ctk.CTkLabel(stats_grid, text="Total Tests: 0", font=self.fonts["normal"])
        self.profile_total_tests.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.profile_best_wpm = ctk.CTkLabel(stats_grid, text="Best WPM: 0", font=self.fonts["normal"])
        self.profile_best_wpm.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.profile_avg_wpm = ctk.CTkLabel(stats_grid, text="Average WPM: 0", font=self.fonts["normal"])
        self.profile_avg_wpm.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.profile_avg_accuracy = ctk.CTkLabel(stats_grid, text="Average Accuracy: 0%", font=self.fonts["normal"])
        self.profile_avg_accuracy.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        self.profile_total_time = ctk.CTkLabel(stats_grid, text="Total Practice Time: 0 min", font=self.fonts["normal"])
        self.profile_total_time.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.profile_activity_section = ctk.CTkFrame(scroll_frame, corner_radius=12, border_width=2, border_color=self.accent)
        self.profile_activity_section.pack(fill="x", padx=20, pady=(0, 20))
        
        activity_header = ctk.CTkLabel(self.profile_activity_section, 
                                       text="Recent Activity",
                                       font=self.fonts["subheader"], 
                                       text_color=self.text_color)
        activity_header.pack(pady=(15, 10))
        
        self.profile_activity_text = ctk.CTkTextbox(self.profile_activity_section, 
                                                   height=150, 
                                                   font=self.fonts["normal"])
        self.profile_activity_text.pack(fill="x", padx=20, pady=(0, 15))
        self.profile_activity_text.configure(state="disabled")
        
        self.profile_achievements_section = ctk.CTkFrame(scroll_frame, corner_radius=12, border_width=2, border_color=self.accent)
        self.profile_achievements_section.pack(fill="x", padx=20, pady=(0, 20))
        
        achievements_header = ctk.CTkLabel(self.profile_achievements_section, 
                                          text="Achievements",
                                          font=self.fonts["subheader"], 
                                          text_color=self.text_color)
        achievements_header.pack(pady=(15, 10))
        
        self.profile_achievements_text = ctk.CTkTextbox(self.profile_achievements_section, 
                                                        height=100, 
                                                        font=self.fonts["normal"])
        self.profile_achievements_text.pack(fill="x", padx=20, pady=(0, 15))
        self.profile_achievements_text.configure(state="disabled")

    def _build_settings_frame(self, parent):
        header_row, header = self._make_header(parent, "Settings", back_command=self._back_to_menu)

        body = ctk.CTkFrame(parent)
        body.pack(fill="both", expand=True, padx=40, pady=20)

        scroll_frame = ctk.CTkScrollableFrame(body)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        appearance_section = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color=self.accent)
        appearance_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(appearance_section, text="Appearance Mode", 
                    font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 5))
        
        self.appearance_option = ctk.CTkOptionMenu(
            appearance_section, 
            values=["default", "light", "dark"],
            command=self._on_appearance_change,
            width=200
        )
        self.appearance_option.set(self._current_theme_mode)
        self.appearance_option.pack(anchor="w", padx=16, pady=(0, 8))
        
        help_text = "Default: Very light purple theme\nLight: White theme\nDark: Dark theme"
        ctk.CTkLabel(appearance_section, text=help_text, 
                    font=self.fonts["normal"],
                    text_color=self.muted).pack(anchor="w", padx=16, pady=(0, 12))

        font_section = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color=self.accent)
        font_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(font_section, text="Font Size", 
                    font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 5))
        
        font_size_frame = ctk.CTkFrame(font_section, fg_color="transparent")
        font_size_frame.pack(fill="x", padx=16, pady=(0, 8))
        
        self.font_size_label = ctk.CTkLabel(font_size_frame, text=f"Font Size: {int(self._base_font_size * self._font_size_multiplier)}", 
                                           font=self.fonts["normal"], text_color=self.text_color)
        self.font_size_label.pack(side="left", padx=(0, 10))
        
        self.font_size_slider = ctk.CTkSlider(font_size_frame, from_=0.7, to=1.5, 
                                             command=self._on_font_size_change, 
                                             number_of_steps=16)
        self.font_size_slider.set(self._font_size_multiplier)
        self.font_size_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(font_size_frame, text="Small", font=self.fonts["normal"], text_color=self.muted).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(font_size_frame, text="Large", font=self.fonts["normal"], text_color=self.muted).pack(side="left")
        
        help_text_font = "Adjust the font size for better readability.\nChanges apply to all text in the application."
        ctk.CTkLabel(font_section, text=help_text_font, 
                    font=self.fonts["normal"],
                    text_color=self.muted).pack(anchor="w", padx=16, pady=(0, 12))

        keyboard_section = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color=self.accent)
        keyboard_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(keyboard_section, text="On-Screen Keyboard", 
                    font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 5))
        
        keyboard_frame = ctk.CTkFrame(keyboard_section, fg_color="transparent")
        keyboard_frame.pack(fill="x", padx=16, pady=(0, 8))
        
        self.keyboard_switch = ctk.CTkSwitch(keyboard_frame, text="Show on-screen keyboard",
                                            command=self._on_keyboard_toggle,
                                            font=self.fonts["normal"])
        self.keyboard_switch.pack(side="left")
        
        help_text_keyboard = "Enable a virtual keyboard that appears on screen.\nUseful for touch-screen devices or accessibility."
        ctk.CTkLabel(keyboard_section, text=help_text_keyboard, 
                    font=self.fonts["normal"],
                    text_color=self.muted).pack(anchor="w", padx=16, pady=(0, 12))

        help_section = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color=self.accent)
        help_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(help_section, text="Help & Support", 
                    font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 5))
        
        help_btn = ctk.CTkButton(help_section, text="Contact for Help", 
                                command=self._show_contact_dialog,
                                width=200, fg_color=self.accent, hover_color=self.accent_hover)
        help_btn.pack(anchor="w", padx=16, pady=(0, 12))

        logout_section = ctk.CTkFrame(scroll_frame, corner_radius=8, border_width=1, border_color=self.accent)
        logout_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(logout_section, text="Account", 
                    font=self.fonts["subheader"], text_color=self.text_color).pack(anchor="w", padx=16, pady=(12, 5))
        
        logout_btn = ctk.CTkButton(logout_section, text="Logout", 
                                   command=self._handle_logout,
                                   width=200, fg_color="#D32F2F", hover_color="#B71C1C")
        logout_btn.pack(anchor="w", padx=16, pady=(0, 12))
        
        self.settings_user_info = ctk.CTkLabel(logout_section, 
                                             text=f"Logged in as: {self.current_user if self.current_user else 'Not logged in'}", 
                                             font=self.fonts["normal"], text_color=self.muted)
        self.settings_user_info.pack(anchor="w", padx=16, pady=(0, 12))

    def _hide_all(self):
        """Hide all frames and cancel pending jobs before showing a new one."""
        # Cancel any pending UI updates to prevent errors
        self._cancel_all_jobs()

    def show_history_frame(self):
        """Show the History frame and refresh its data."""
        self._hide_all()
        self.frames["history"].lift()
        try:
            self._refresh_history()
        except Exception:
            pass

    def show_stats(self):
        """Show the Statistics frame and refresh charts."""
        self._hide_all()
        self.frames["stats"].lift()
        try:
            self._refresh_stats()
        except Exception:
            pass

    def show_profile(self):
        """FIXED: Show profile with actual user data from database"""
        self._hide_all()
        self.frames["profile"].lift()
        
        if not self.current_user:
            self.profile_user_label.configure(text="User: Not logged in")
            self.profile_total_tests.configure(text="Total Tests: 0")
            self.profile_best_wpm.configure(text="Best WPM: 0")
            self.profile_avg_wpm.configure(text="Average WPM: 0")
            self.profile_avg_accuracy.configure(text="Average Accuracy: 0%")
            self.profile_total_time.configure(text="Total Practice Time: 0 min")
            self.profile_activity_text.configure(state="normal")
            self.profile_activity_text.delete("1.0", "end")
            self.profile_activity_text.insert("1.0", "No activity to display.")
            self.profile_activity_text.configure(state="disabled")
            self.profile_achievements_text.configure(state="normal")
            self.profile_achievements_text.delete("1.0", "end")
            self.profile_achievements_text.insert("1.0", "No achievements yet.")
            self.profile_achievements_text.configure(state="disabled")
            return
        
        # Update user name
        self.profile_user_label.configure(text=f"User: {self.current_user}")
        
        # Get user's test history from database
        rows = self.logic.get_history(limit=10000, name=self.current_user)
        
        if not rows:
            self.profile_total_tests.configure(text="Total Tests: 0")
            self.profile_best_wpm.configure(text="Best WPM: 0")
            self.profile_avg_wpm.configure(text="Average WPM: 0")
            self.profile_avg_accuracy.configure(text="Average Accuracy: 0%")
            self.profile_total_time.configure(text="Total Practice Time: 0 min")
            self.profile_activity_text.configure(state="normal")
            self.profile_activity_text.delete("1.0", "end")
            self.profile_activity_text.insert("1.0", "No tests completed yet.\nStart a typing test to see your progress!")
            self.profile_activity_text.configure(state="disabled")
            self.profile_achievements_text.configure(state="normal")
            self.profile_achievements_text.delete("1.0", "end")
            self.profile_achievements_text.insert("1.0", "Complete typing tests to unlock achievements!")
            self.profile_achievements_text.configure(state="disabled")
            return
        
        # Calculate statistics from rows
        total_tests = len(rows)
        wpms = [float(r[1]) for r in rows]
        accuracies = [float(r[2]) for r in rows]
        times = [float(r[3]) for r in rows]
        
        best_wpm = max(wpms)
        avg_wpm = sum(wpms) / len(wpms)
        avg_accuracy = sum(accuracies) / len(accuracies)
        total_time_seconds = sum(times)
        total_time_minutes = total_time_seconds / 60
        
        # Update statistics display
        self.profile_total_tests.configure(text=f"Total Tests: {total_tests}")
        self.profile_best_wpm.configure(text=f"Best WPM: {best_wpm:.1f}")
        self.profile_avg_wpm.configure(text=f"Average WPM: {avg_wpm:.1f}")
        self.profile_avg_accuracy.configure(text=f"Average Accuracy: {avg_accuracy:.1f}%")
        self.profile_total_time.configure(text=f"Total Practice Time: {total_time_minutes:.0f} min")
        
        # Update recent activity
        self.profile_activity_text.configure(state="normal")
        self.profile_activity_text.delete("1.0", "end")
        
        activity_text = "Recent Test Results:\n\n"
        # Show last 5 tests (rows are already in reverse chronological order)
        for i, row in enumerate(rows[:5]):
            date_str = row[4] if len(row) > 4 else "Unknown"  # created_at
            wpm = row[1]
            accuracy = row[2]
            time_taken = row[3]
            activity_text += f"• Test #{total_tests - i}: {wpm:.1f} WPM, {accuracy:.1f}% accuracy, {time_taken:.1f}s\n"
            activity_text += f"  Date: {date_str}\n\n"
        
        self.profile_activity_text.insert("1.0", activity_text)
        self.profile_activity_text.configure(state="disabled")
        
        # Update achievements
        self.profile_achievements_text.configure(state="normal")
        self.profile_achievements_text.delete("1.0", "end")
        
        achievements = []
        
        # Speed achievements
        if best_wpm >= 100:
            achievements.append("🏆 Speed Demon: Achieved 100+ WPM")
        elif best_wpm >= 80:
            achievements.append("⚡ Fast Typer: Achieved 80+ WPM")
        elif best_wpm >= 60:
            achievements.append("🚀 Quick Fingers: Achieved 60+ WPM")
        
        # Accuracy achievements
        if avg_accuracy >= 98:
            achievements.append("🎯 Perfectionist: 98%+ average accuracy")
        elif avg_accuracy >= 95:
            achievements.append("✨ Precision Master: 95%+ average accuracy")
        elif avg_accuracy >= 90:
            achievements.append("🎯 Accurate Typer: 90%+ average accuracy")
        
        # Practice achievements
        if total_tests >= 100:
            achievements.append("📚 Dedicated Student: 100+ tests completed")
        elif total_tests >= 50:
            achievements.append("📖 Regular Practice: 50+ tests completed")
        elif total_tests >= 25:
            achievements.append("📚 Getting Started: 25+ tests completed")
        
        # Time achievements
        if total_time_minutes >= 60:
            achievements.append("⏰ Hour Master: 1+ hour of practice time")
        elif total_time_minutes >= 30:
            achievements.append("🕐 Half Hour Hero: 30+ minutes of practice")
        
        if achievements:
            achievements_text = "🏅 Achievements Unlocked:\n\n"
            for achievement in achievements:
                achievements_text += f"{achievement}\n"
        else:
            achievements_text = "Keep practicing to unlock achievements!\n\n"
            achievements_text += "Achievements you can earn:\n"
            achievements_text += "• Speed achievements (60+, 80+, 100+ WPM)\n"
            achievements_text += "• Accuracy achievements (90%+, 95%+, 98%+)\n"
            achievements_text += "• Practice achievements (25+, 50+, 100+ tests)\n"
            achievements_text += "• Time achievements (30+ min, 1+ hour)"
        
        self.profile_achievements_text.insert("1.0", achievements_text)
        self.profile_achievements_text.configure(state="disabled")

    def show_settings(self):
        self._hide_all()
        self.frames["settings"].lift()
        try:
            if hasattr(self, 'frames') and 'settings' in self.frames:
                for widget in self.frames["settings"].winfo_children():
                    self._update_settings_user_info(widget)
        except Exception:
            pass

    def show_test(self):
        """Navigate to the Test page and prepare UI state."""
        self._hide_all()
        try:
            self._show_sidebar_nav()
        except Exception:
            pass
        self.frames["test"].lift()
        try:
            self.start_btn.configure(state="normal")
            self.end_btn.configure(state="disabled")
            self.result_label.configure(text="Ready")
            self.run_stats.configure(text="WPM: -\nAccuracy: -\nTime: -")
            self.test_sentence_box.configure(state="normal")
            self.test_sentence_box.delete("1.0", "end")
            self.test_sentence_box.configure(state="disabled")
            self.test_typing_box.configure(state="disabled")
        except Exception:
            pass

# Event 
    def _update_color_scheme(self, mode):
        """Elegant color schemes for different modes."""
        if mode.lower() == "dark":
            self.accent = "#7B1FA2"
            self.accent_hover = "#9C27B0"
            self.bg_color = "#121212"
            self.sidebar_bg = "#1F1F1F"
            self.card_bg = "#272727"
            self.muted = "#9E9E9E"
            self.success = "#4CAF50"
            self.error = "#F44336"
            self.text_color = "#FFFFFF"
            self.highlight = "#E040FB"
            self.input_bg = "#3C3C3C"
            self.button_fg = "#7B1FA2"
            self.button_hover = "#9C27B0"
            self.button_text = "#FFFFFF"
        elif mode.lower() == "default":
            # Elegant purple theme with soft pastels
            self.accent = "#8B6FD9"
            self.accent_hover = "#A089E3"
            self.bg_color = "#F8F6FC"
            self.sidebar_bg = "#EDE8F5"
            self.card_bg = "#FFFFFF"
            self.muted = "#9B8AB8"
            self.success = "#4CAF50"
            self.error = "#E57373"
            self.text_color = "#2D2640"
            self.highlight = "#D4C8F0"
            self.input_bg = "#FFFFFF"
            self.button_fg = "#8B6FD9"
            self.button_hover = "#A089E3"
            self.button_text = "#FFFFFF"
        else:
            # Clean light theme with subtle grays
            self.accent = "#9E9E9E"
            self.accent_hover = "#757575"
            self.bg_color = "#FAFAFA"
            self.sidebar_bg = "#F5F5F5"
            self.card_bg = "#FFFFFF"
            self.muted = "#BDBDBD"
            self.success = "#66BB6A"
            self.error = "#EF5350"
            self.text_color = "#212121"
            self.highlight = "#E0E0E0"
            self.input_bg = "#FFFFFF"
            self.button_fg = "#757575"
            self.button_hover = "#616161"
            self.button_text = "#FFFFFF"
            
    def _on_appearance_change(self, val):
        """Handle appearance mode changes."""
        self._current_theme_mode = val
        self._update_color_scheme(val)
        if val == "default":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode(val)
        try:
            self._apply_global_styles()
        except Exception:
            pass
        try:
            if hasattr(self, 'game_canvas'):
                self.game_canvas.configure(bg=self.card_bg)
        except Exception:
            pass
        try:
            for frame in self.frames.values():
                frame.configure(fg_color=self.bg_color)
        except Exception:
            pass
        try:
            if hasattr(self, 'topbar'):
                self.topbar.configure(fg_color=self.sidebar_bg)
        except Exception:
            pass
        try:
            if hasattr(self, 'app_shell'):
                self.app_shell.configure(fg_color=self.bg_color)
        except Exception:
            pass
        try:
            if hasattr(self, 'sidebar'):
                self.sidebar.configure(fg_color=self.sidebar_bg)
        except Exception:
            pass

        self.update()

    def _auto_focus_input_field(self, mode):
        """Automatically focus the appropriate input field."""
        try:
            if mode == 'test':
                if hasattr(self, 'test_typing_box') and self.test_typing_box.cget('state') == 'normal':
                    self.test_typing_box.focus_set()
            elif mode == 'practice':
                if hasattr(self, 'practice_entry') and self.practice_entry.cget('state') == 'normal':
                    self.practice_entry.focus_set()
            elif mode == 'game':
                if hasattr(self, 'game_overlay_entry') and self.game_overlay_entry.winfo_ismapped():
                    self.game_overlay_entry.focus_set()
                elif hasattr(self, 'game_entry') and self.game_entry.cget('state') == 'normal':
                    self.game_entry.focus_set()
        except Exception:
            pass

    def _on_font_size_change(self, value):
        """Handle font size changes."""
        self._font_size_multiplier = value
        try:
            new_size = int(self._base_font_size * self._font_size_multiplier)
            self.font_size_label.configure(text=f"Font Size: {new_size}")
        except Exception:
            pass
        
        try:
            self._apply_font_scaling()
        except Exception:
            pass

    def _on_keyboard_toggle(self):
        """Toggle on-screen keyboard visibility."""
        if self._on_screen_keyboard_visible:
            self._hide_on_screen_keyboard()
        else:
            self._show_on_screen_keyboard()

    def _show_on_screen_keyboard(self):
        """Create and show the on-screen keyboard."""
        if self._on_screen_keyboard_visible:
            return
        
        self._on_screen_keyboard = ctk.CTkToplevel(self)
        self._on_screen_keyboard.title("On-Screen Keyboard")
        self._on_screen_keyboard.attributes("-topmost", True)
        
        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            keyboard_width = min(800, screen_width - 40)
            keyboard_height = 250
            x = (screen_width - keyboard_width) // 2
            y = screen_height - keyboard_height - 50
            self._on_screen_keyboard.geometry(f"{keyboard_width}x{keyboard_height}+{x}+{y}")
        except Exception:
            pass
        
        keyboard_frame = ctk.CTkFrame(self._on_screen_keyboard)
        keyboard_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
            ["Tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
            ["Caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "Enter"],
            ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "Shift"],
            ["Ctrl", "Alt", "Space", "Alt", "Ctrl"]
        ]
        
        self._keyboard_keys = {}
        self._keyboard_caps = False
        self._keyboard_shift = False
        
        for row_idx, row in enumerate(rows):
            row_frame = ctk.CTkFrame(keyboard_frame, fg_color="transparent")
            row_frame.pack(pady=2)
            
            for key in row:
                if key == "Space":
                    width = 200
                elif key in ["Backspace", "Enter", "Tab", "Caps", "Shift"]:
                    width = 80
                elif key in ["Ctrl", "Alt"]:
                    width = 60
                else:
                    width = 40
                
                btn = ctk.CTkButton(row_frame, text=key, width=width, height=35,
                                   command=lambda k=key: self._keyboard_key_press(k),
                                   font=("Arial", 10))
                btn.pack(side="left", padx=1)
                self._keyboard_keys[key] = btn
        
        close_btn = ctk.CTkButton(keyboard_frame, text="Close Keyboard", 
                                 command=self._hide_on_screen_keyboard,
                                 fg_color="#D32F2F", hover_color="#B71C1C")
        close_btn.pack(pady=(5, 0))
        
        self._on_screen_keyboard_visible = True
        self._on_screen_keyboard.protocol("WM_DELETE_WINDOW", self._hide_on_screen_keyboard)

    def _hide_on_screen_keyboard(self):
        """Hide the on-screen keyboard."""
        if not self._on_screen_keyboard_visible:
            return
        
        try:
            if self._on_screen_keyboard:
                self._on_screen_keyboard.destroy()
                self._on_screen_keyboard = None
        except Exception:
            pass
        
        self._on_screen_keyboard_visible = False
        try:
            self.keyboard_switch.deselect()
        except Exception:
            pass

    def _keyboard_key_press(self, key):
        """Handle key press from on-screen keyboard."""
        try:
            focused = self.focus_get()
            
            if not focused:
                try:
                    current_frame = None
                    for frame_name, frame in self.frames.items():
                        if frame.winfo_ismapped():
                            current_frame = frame
                            break
                    
                    if current_frame:
                        for widget in self._find_widgets_by_type(current_frame, (ctk.CTkEntry, ctk.CTkTextbox)):
                            try:
                                if widget.focus_get() == widget:
                                    focused = widget
                                    break
                            except Exception:
                                pass
                except Exception:
                    pass
            
            if not focused:
                try:
                    if hasattr(self, 'frames'):
                        if self.frames.get('test') and self.frames['test'].winfo_ismapped():
                            if hasattr(self, 'test_typing_box') and self.test_typing_box.cget('state') == 'normal':
                                focused = self.test_typing_box
                        elif self.frames.get('practice') and self.frames['practice'].winfo_ismapped():
                            if hasattr(self, 'practice_entry') and self.practice_entry.cget('state') == 'normal':
                                focused = self.practice_entry
                        elif self.frames.get('game') and self.frames['game'].winfo_ismapped():
                            if hasattr(self, 'game_overlay_entry') and self.game_overlay_entry.winfo_ismapped():
                                focused = self.game_overlay_entry
                            elif hasattr(self, 'game_entry') and self.game_entry.cget('state') == 'normal':
                                focused = self.game_entry
                except Exception:
                    pass
            
            if not focused:
                return
            
            if key == "Space":
                char = " "
            elif key == "Backspace":
                try:
                    if isinstance(focused, ctk.CTkEntry):
                        current = focused.get()
                        if current:
                            cursor_pos = focused.index("insert")
                            if cursor_pos > 0:
                                new_text = current[:cursor_pos-1] + current[cursor_pos:]
                                focused.delete(0, "end")
                                focused.insert(0, new_text)
                                focused.icursor(cursor_pos - 1)
                    elif isinstance(focused, ctk.CTkTextbox):
                        focused.delete("end-2c", "end-1c")
                except Exception:
                    pass
                return
            elif key == "Enter":
                char = "\n"
            elif key == "Tab":
                char = "\t"
            elif key == "Caps":
                self._keyboard_caps = not self._keyboard_caps
                self._update_keyboard_display()
                return
            elif key == "Shift":
                self._keyboard_shift = not self._keyboard_shift
                self._update_keyboard_display()
                return
            elif key in ["Ctrl", "Alt"]:
                return
            else:
                char = key
                if self._keyboard_shift or self._keyboard_caps:
                    char = char.upper()
                else:
                    char = char.lower()
                if self._keyboard_shift:
                    self._keyboard_shift = False
                    self._update_keyboard_display()
            
            try:
                if isinstance(focused, ctk.CTkEntry):
                    current = focused.get()
                    cursor_pos = focused.index("insert")
                    new_text = current[:cursor_pos] + char + current[cursor_pos:]
                    focused.delete(0, "end")
                    focused.insert(0, new_text)
                    focused.icursor(cursor_pos + 1)
                    if focused == self.practice_entry:
                        focused.event_generate('<KeyRelease>')
                    elif focused == self.game_entry or focused == self.game_overlay_entry:
                        if char == '\n':
                            focused.event_generate('<Return>')
                elif isinstance(focused, ctk.CTkTextbox):
                    if focused == self.test_typing_box:
                        focused.insert("insert", char)
                        focused.event_generate('<KeyRelease>')
                    else:
                        focused.insert("insert", char)
            except Exception:
                pass
        except Exception as e:
            print(f"Error handling keyboard key press: {e}")

    def _find_widgets_by_type(self, parent, widget_types):
        """Recursively find widgets of specified types."""
        widgets = []
        try:
            for child in parent.winfo_children():
                if isinstance(child, widget_types):
                    widgets.append(child)
                widgets.extend(self._find_widgets_by_type(child, widget_types))
        except Exception:
            pass
        return widgets

    def _update_settings_user_info(self, widget):
        """Recursively update user info in settings frame."""
        try:
            if isinstance(widget, ctk.CTkLabel):
                text = widget.cget("text")
                if text and "Logged in as:" in text:
                    widget.configure(text=f"Logged in as: {self.current_user if self.current_user else 'None'}")
        except Exception:
            pass
        
        try:
            for child in widget.winfo_children():
                self._update_settings_user_info(child)
        except Exception:
            pass

    def _update_keyboard_display(self):
        """Update keyboard display for caps/shift state."""
        try:
            if not self._keyboard_keys:
                return
            
            for key, btn in self._keyboard_keys.items():
                if key in ["Caps", "Shift"]:
                    if (key == "Caps" and self._keyboard_caps) or (key == "Shift" and self._keyboard_shift):
                        btn.configure(fg_color=self.accent)
                    else:
                        btn.configure(fg_color=None)
        except Exception:
            pass

    def _show_contact_dialog(self):
        """Show contact/help information dialog."""
        contact_win = ctk.CTkToplevel(self)
        contact_win.title("वर्ण वेग — Contact & Help")
        contact_win.geometry("500x400")
        contact_win.grab_set()
        
        try:
            self.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() - 500) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 400) // 2
            contact_win.geometry(f"500x400+{x}+{y}")
        except Exception:
            pass
        
        contact_frame = ctk.CTkFrame(contact_win, corner_radius=12, border_width=2, border_color=self.accent)
        contact_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header = ctk.CTkLabel(contact_frame, text="Help & Support", 
                            font=self.fonts["header"], text_color=self.text_color)
        header.pack(pady=(20, 10))
        
        info_text = """
वर्ण वेग — Typing Beyond Limits - Help & Support

For assistance with the application:

Email: sheetal.choudhary@avantika.edu.in
Phone: +91 8085017117

Features:
• Typing Tests - Practice with random sentences
• Practice Mode - Improve accuracy word by word
• Game Mode - Fun typing game
• Progress Tracking - View your improvement over time
• History - See all your past results

Tips:
• Use the Settings page to customize your experience
• Adjust font size for better readability
• Enable on-screen keyboard for touch devices
• Switch between themes for your preference
        """
        
        info_label = ctk.CTkLabel(contact_frame, text=info_text,
                                font=self.fonts["normal"], 
                                text_color=self.text_color,
                                justify="left")
        info_label.pack(pady=20, padx=20)
        
        close_btn = ctk.CTkButton(contact_frame, text="Close", 
                                 command=contact_win.destroy,
                                 width=150, fg_color=self.accent, hover_color=self.accent_hover)
        close_btn.pack(pady=(0, 20))

    def _handle_logout(self):
        """Handle logout action."""
        if not self.current_user:
            messagebox.showinfo("Info", "You are not logged in.")
            return
        
        result = messagebox.askyesno("Logout", f"Are you sure you want to logout, {self.current_user}?")
        if result:
            self.current_user = None
            
            try:
                if hasattr(self, 'settings_user_info'):
                    self.settings_user_info.configure(text="Logged in as: Not logged in")
            except Exception:
                pass
            
            try:
                self.sidebar.pack_forget()
            except Exception:
                pass
            
            for b in self.nav_buttons.values():
                try:
                    b.configure(state="disabled")
                except Exception:
                    pass
            
            self._hide_sidebar_nav()
            self._back_to_welcome()
            
            messagebox.showinfo("Logged Out", "You have been logged out successfully.")

    # Test logic
    def start_test(self):
        """Start a new typing test."""
        if not self.current_user:
            messagebox.showwarning("Name required", "Please enter your name from the welcome screen before starting a test.")
            return
        if getattr(self, '_test_running', False) and not getattr(self, '_ending_test', False):
            return
            
        sentence = self.logic.pick_sentence()
        if not sentence:
            messagebox.showerror("Error", "Could not load test sentence. Please check sentences.txt file.")
            return
            
        word_count = len(sentence.split())
        self.time_allowed = max(15, word_count * 2)
        
        try:
            self.test_sentence_box.configure(state="normal")
            self.test_sentence_box.delete("1.0", "end")
            self.test_sentence_box.insert("1.0", sentence)
            self.test_sentence_box.configure(state="disabled", text_color=self.text_color)
        except Exception as e:
            print(f"Error setting sentence: {e}")
            return

        try:
            self.test_typing_box.configure(state="normal", text_color=self.text_color)
            self.test_typing_box.delete("1.0", "end")
            for t in ("correct", "incorrect", "current"):
                self.test_typing_box.tag_remove(t, "1.0", "end")
            self.test_typing_box.focus_set()
        except Exception as e:
            print(f"Error preparing typing box: {e}")
            return

        try:
            self.start_btn.configure(state="disabled")
            self.end_btn.configure(state="normal")
        except Exception:
            pass

        self._ending_test = False
        self.logic.start_timer()
        self._test_running = True
        self.time_remaining = self.time_allowed
        try:
            self.result_label.configure(text=f"Time remaining: {self.time_remaining}s")
        except Exception:
            pass
        self._update_timer()
        
        try:
            self.result_label.configure(text=f"Time remaining: {self.time_allowed}s")
            self.run_stats.configure(text="WPM: -\nAccuracy: -\nTime: -")
        except Exception:
            pass
            
        self._update_highlighting()
        
    def _update_timer(self):
        if self._test_running and self.time_remaining > 0:
            self.result_label.configure(text=f"Time remaining: {self.time_remaining}s")
            self.time_remaining -= 1
            job_id = self.after(1000, self._update_timer)
            self._after_jobs.append(job_id)
        elif self._test_running:
            try:
                self._test_running = False
                self.end_test()
            except Exception:
                pass

    def end_test(self):
        """FIXED: End test with properly displayed result popup"""
        if getattr(self, '_ending_test', False):
            return
        if not getattr(self, '_test_running', False):
            if not hasattr(self, 'logic') or self.logic.start_time is None:
                messagebox.showinfo("Info", "No test is currently running.")
                return
        self._ending_test = True
            
        typed = self.test_typing_box.get("1.0", "end").strip()
        if not typed:
            messagebox.showwarning("Warning", "No text entered. Try again!")
            self._ending_test = False
            return
            
        try:
            wpm, accuracy, time_taken = self.logic.calculate(typed)
        except RuntimeError as e:
            messagebox.showerror("Error", str(e))
            self._ending_test = False
            return
            
        try:
            name = self.current_user
            self.logic.save_result(name, wpm, accuracy, time_taken, test_type="test")
        except Exception as e:
            print(f"Error saving results: {e}")
            
        # FIXED: Create properly formatted result dialog
        try:
            try:
                self.test_typing_box.configure(state="disabled")
                self.start_btn.configure(state="normal")
                self.end_btn.configure(state="disabled")
            except Exception:
                pass

            result_win = ctk.CTkToplevel(self)
            result_win.title("Typing Test Result")
            result_win.geometry("520x420")
            
            try:
                self.update_idletasks()
                x = self.winfo_rootx() + max(0, (self.winfo_width() - 520) // 2)
                y = self.winfo_rooty() + max(0, (self.winfo_height() - 420) // 2)
                result_win.geometry(f"520x420+{x}+{y}")
            except Exception:
                pass
            
            result_win.grab_set()
            result_win.focus_set()
            result_win.attributes("-topmost", True)
            result_win.resizable(False, False)

            result_overlay = ctk.CTkFrame(result_win, corner_radius=12, border_width=2, border_color=self.accent)
            result_overlay.pack(fill="both", expand=True, padx=20, pady=20)
            
            header = ctk.CTkLabel(result_overlay, text="🎉 Test Complete! 🎉", 
                                font=("Segoe UI", 28, "bold"),
                                text_color=self.text_color)
            header.pack(pady=(20, 10))
            
            cpm = wpm * 5
            if wpm >= 80:
                grade = "Excellent! 🏆"
                grade_color = "#2E7D32"
            elif wpm >= 60:
                grade = "Great! ⭐"
                grade_color = "#388E3C"
            elif wpm >= 40:
                grade = "Good! 👍"
                grade_color = "#689F38"
            else:
                grade = "Keep Practicing! 💪"
                grade_color = "#FFA726"
            
            results_text = (
                f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⚡ Speed: {wpm:.1f} WPM  ({cpm:.0f} CPM)\n\n"
                f"🎯 Accuracy: {accuracy:.1f}%\n\n"
                f"⏱️ Time: {time_taken:.1f} seconds\n\n"
            )

            results_block = ctk.CTkFrame(result_overlay, corner_radius=8, border_width=2, border_color=self.accent, fg_color=self.card_bg)
            results_block.pack(pady=(10, 10), padx=30, fill="x")

            results_label = ctk.CTkLabel(results_block, text=results_text,
                        font=("Segoe UI", 18),
                        justify="left", text_color=self.text_color)
            results_label.pack(pady=20, padx=20)
            
            grade_label = ctk.CTkLabel(result_overlay, text=f"Rating: {grade}", 
                                      font=("Segoe UI", 20, "bold"), 
                                      text_color=grade_color)
            grade_label.pack(pady=(0, 10))

            try:
                rows_all = self.logic.get_history(limit=10000, name=self.current_user)
                wpms_all = [float(r[1] or 0) for r in rows_all]
                if wpms_all:
                    if len(wpms_all) > 1:
                        prev_best = max(wpms_all[1:])
                        prev_low = min(wpms_all[1:])
                    else:
                        prev_best = wpm
                        prev_low = wpm
                    if wpm >= prev_best:
                        ctk.CTkLabel(result_overlay, text="🏆 New Best Speed! 🏆", 
                                   text_color="#2E7D32", 
                                   font=("Segoe UI", 16, "bold")).pack(pady=(0, 10))
                    elif wpm <= prev_low:
                        ctk.CTkLabel(result_overlay, text="Keep practicing!", 
                                   text_color="#FF9800", 
                                   font=("Segoe UI", 14)).pack(pady=(0, 10))
            except Exception:
                pass
            
            btn_row = ctk.CTkFrame(result_overlay, fg_color="transparent")
            btn_row.pack(pady=(10, 20))

            def do_restart():
                try:
                    result_win.grab_release()
                    result_win.destroy()
                except Exception:
                    pass
                try:
                    self.start_btn.configure(state="normal")
                    self.end_btn.configure(state="disabled")
                except Exception:
                    pass
                self.start_test()

            def do_close():
                try:
                    result_win.grab_release()
                    result_win.destroy()
                except Exception:
                    pass
                self._flash_label(self.result_label, self.success, 500)

            restart_btn = ctk.CTkButton(btn_row, text="🔄 Restart Test", width=160, height=40,
                                       command=do_restart, 
                                       fg_color=self.accent, 
                                       hover_color=self.accent_hover,
                                       font=("Segoe UI", 14, "bold"))
            restart_btn.pack(side="left", padx=10)
            
            close_btn = ctk.CTkButton(btn_row, text="✓ Close", width=140, height=40,
                                     command=do_close,
                                     fg_color="#4CAF50",
                                     hover_color="#388E3C",
                                     font=("Segoe UI", 14, "bold"))
            close_btn.pack(side="left", padx=10)
            
        except Exception as e:
            print(f"Error showing results overlay: {e}")
        
        try:
            self.result_label.configure(text="Test complete")
            self.test_typing_box.configure(state="disabled")
            self.start_btn.configure(state="normal")
            self.end_btn.configure(state="disabled")
            self._test_running = False
            self._ending_test = False
        except Exception as e:
            print(f"Error updating UI state: {e}")
            
        try:
            self._update_sidebar_stats()
            if hasattr(self, '_refresh_stats'):
                self._refresh_stats()
        except Exception as e:
            print(f"Error refreshing stats: {e}")

    def _update_sidebar_stats(self):
        if not self.current_user:
            self.sidebar_stats.configure(text="No user")
            return
        rows = self.logic.get_history(limit=5, name=self.current_user)
        if not rows:
            self.sidebar_stats.configure(text="No history for user")
            return
        avg = sum(r[1] for r in rows) / len(rows)
        self.sidebar_stats.configure(text=f"Recent avg WPM: {avg:.1f}")

    def _on_keypress(self, event):
        if event.keysym == "Return" and self._test_running:
            self.end_test()
            return "break"
        try:
            self._update_highlighting()
        except Exception:
            pass

    def _update_highlighting(self):
        """Update real-time highlighting of typed text."""
        if not hasattr(self, 'test_typing_box') or not hasattr(self.logic, 'current_sentence'):
            return
            
        typed = self.test_typing_box.get("1.0", "end-1c")
        target = (self.logic.current_sentence or "").strip()
        
        try:
            self.test_sentence_box.configure(state="normal")
            try:
                self.test_sentence_box.tag_remove("target_current", "1.0", "end")
            except Exception:
                pass
            typed_words = re.findall(r"\S+", typed)
            target_words = re.findall(r"\S+", target)
            curr_idx = max(0, len(typed_words) - 1 if typed.strip() else 0)
            if target_words and curr_idx < len(target_words):
                start = 0
                word_positions = []
                for m in re.finditer(r"\S+", target):
                    word_positions.append((m.start(), m.end()))
                ws, we = word_positions[curr_idx]
                self.test_sentence_box.tag_add("target_current", f"1.0+{ws}c", f"1.0+{we}c")
            self.test_sentence_box.configure(state="disabled")
        except Exception:
            try:
                self.test_sentence_box.configure(state="disabled")
            except Exception:
                pass

        try:
            for t in ("correct", "incorrect", "current", "upcoming"):
                self.test_typing_box.tag_remove(t, "1.0", "end")
        except Exception:
            pass
            
        if not typed:
            return
            
        typed = typed.rstrip("\n")
        
        typed_matches = list(re.finditer(r"\S+", typed))
        target_words = re.findall(r"\S+", target)
        
        correct_words = 0
        total_words = len(typed_matches)
        
        for i, m in enumerate(typed_matches):
            s, e = m.start(), m.end()
            typed_word = m.group()
            target_word = target_words[i] if i < len(target_words) else None
            
            start_index = f"1.0+{s}c"
            end_index = f"1.0+{e}c"
            
            try:
                if target_word is None:
                    self.test_typing_box.tag_add("incorrect", start_index, end_index)
                elif typed_word == target_word:
                    self.test_typing_box.tag_add("correct", start_index, end_index)
                    correct_words += 1
                else:
                    self.test_typing_box.tag_add("incorrect", start_index, end_index)
                
                if i == len(typed_matches) - 1:
                    self.test_typing_box.tag_add("current", start_index, end_index)
            except Exception:
                continue
        
        if total_words > 0:
            accuracy = (correct_words / total_words) * 100
            try:
                self.run_stats.configure(
                    text=f"Current Accuracy: {accuracy:.1f}%\n"
                         f"Words: {correct_words}/{total_words}\n"
                         f"Time: {self.time_remaining}s"
                )
            except Exception:
                pass
        
        if typed.strip() == target and self._test_running:
            try:
                self._test_running = False
                self.test_typing_box.configure(state='disabled')
            except Exception:
                pass
            self.end_test()
            
        try:
            if total_words > 0 and correct_words/total_words < 0.5:
                self._flash_label(self.result_label, self.error, 200)
        except Exception:
            pass

    def _on_history_filter_change(self, choice):
        self._refresh_history()

    def _refresh_history(self):
        if not hasattr(self, 'history_table'):
            return
        for item in self.history_table.get_children():
            self.history_table.delete(item)
        if not self.current_user:
            return
        
        test_type_filter = self.history_filter_var.get()
        if test_type_filter == "all":
            test_type_filter = None
            
        rows = self.logic.get_history(limit=500, name=self.current_user, test_type=test_type_filter)
        if not rows:
            return
        total = len(rows)
        for idx, r in enumerate(rows):
            seq = total - idx
            self.history_table.insert("", "end", values=(seq, r[0], f"{r[1]:.1f}", f"{r[2]:.1f}%", f"{r[3]:.1f}s"))

    def _refresh_stats(self):
        """Refresh statistics and charts."""
        try:
            if not self.current_user:
                try:
                    self.avg_speed_label.configure(text="-")
                    self.avg_time_label.configure(text="-")
                except Exception:
                    pass
                try:
                    if hasattr(self, 'stats_axes'):
                        for ax in self.stats_axes.flat:
                            ax.clear()
                    elif hasattr(self, 'speed_ax') and hasattr(self, 'time_ax'):
                        self.speed_ax.clear(); self.time_ax.clear()
                    if hasattr(self, 'stats_canvas'):
                        self.stats_canvas.draw()
                except Exception:
                    pass
                return

            test_type_filter = self.stats_filter_var.get()
            if test_type_filter == "all":
                test_type_filter = None

            rows = self.logic.get_history(limit=10000, name=self.current_user, test_type=test_type_filter)
            if not rows:
                try:
                    if hasattr(self, 'stats_axes'):
                        for ax in self.stats_axes.flat:
                            ax.clear()
                            ax.text(0.5, 0.5, 'No data yet\nComplete some typing tests to see your progress!', 
                                  ha='center', va='center', color=self.muted, fontsize=14)
                        self.stats_canvas.draw()
                except Exception:
                    pass
                return

            seqs = []
            wpms = []
            accs = []
            times = []
            total = len(rows)
            for idx, r in enumerate(rows, start=1):
                seq = total - idx + 1
                seqs.append(seq)
                wpms.append(float(r[1] or 0))
                accs.append(float(r[2] or 0))
                times.append(float(r[3] or 0))

            avg_wpm = sum(wpms) / len(wpms) if wpms else 0
            best_wpm = max(wpms) if wpms else 0
            recent_avg = sum(wpms[:5]) / min(5, len(wpms)) if wpms else 0
            avg_time = sum(times) / len(times) if times else 0
            best_acc = max(accs) if accs else 0
            avg_acc = sum(accs) / len(accs) if accs else 0
            consistency = 100 * (1 - (max(wpms) - min(wpms)) / max(wpms)) if wpms else 0

            try:
                self.avg_speed_label.configure(text=f"{avg_wpm:.1f} CPM")
                self.avg_time_label.configure(text=f"{avg_time:.1f} sec")
                direction = "up" if len(wpms) > 1 and wpms[0] >= (sum(wpms[:min(5,len(wpms))]) / min(5,len(wpms))) else "down"
                filter_text = self.stats_filter_var.get().capitalize()
                if filter_text == "All":
                    filter_text = "All Tests"
                self.conclusion_label.configure(text=f"{filter_text}: Recent trend {direction}. Best {best_wpm:.1f} WPM, Best Accuracy {best_acc:.1f}%.")
            except Exception:
                pass

            try:
                if hasattr(self, 'stat_displays'):
                    self.stat_displays.get('top_speed', ctk.CTkLabel()).configure(
                        text=f"{best_wpm:.1f} CPM\n(Best)")
                    self.stat_displays.get('avg_speed', ctk.CTkLabel()).configure(
                        text=f"{recent_avg:.1f} CPM\n(Recent Avg)")
                    self.stat_displays.get('total_tests', ctk.CTkLabel()).configure(
                        text=f"{len(wpms)}\nTotal Tests")
                    self.stat_displays.get('best_acc', ctk.CTkLabel()).configure(
                        text=f"{best_acc:.1f}%\n{consistency:.1f}% Consistent")
            except Exception:
                pass

            try:
                if hasattr(self, 'stats_axes'):
                    a00 = self.stats_axes[0]
                    a01 = self.stats_axes[1]
                    a10 = self.stats_axes[2]
                    a30 = self.stats_axes[3]
                elif hasattr(self, 'speed_ax') and hasattr(self, 'time_ax'):
                    a00 = self.speed_ax
                    a01 = self.time_ax
                    a10 = None
                    a30 = None
                else:
                    return

                for ax in (a00, a01, a10, a30):
                    if ax is not None:
                        ax.clear()

                if wpms:
                    # Bar chart for WPM
                    a00.bar(seqs, wpms, color="#5605BAFF", alpha=0.7, label='WPM')

                    # Line chart for trend
                    try:
                        if len(seqs) > 1:
                            z = np.polyfit(range(len(seqs)), wpms, 1)
                            p = np.poly1d(z)
                            a00.plot(seqs, p(range(len(seqs))), "-", color='#D0021B', linewidth=2, label='Trend')
                    except Exception:
                        pass

                # Styling for WPM chart
                a00.set_title('WPM Trend', color='black', fontsize=14, fontweight='bold', pad=15)
                a00.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                a00.tick_params(colors='black', labelsize=10)
                a00.set_ylabel('Words Per Minute', color='black', fontsize=12, fontweight='bold')
                a00.set_xlabel('Test # (1 = oldest)', color='black', fontsize=12, fontweight='bold')
                a00.set_facecolor('#F8F9FA')
                a00.spines['top'].set_visible(False)
                a00.spines['right'].set_visible(False)
                a00.spines['bottom'].set_linewidth(1.5)
                a00.spines['left'].set_linewidth(1.5)
                a00.legend(loc='upper left', fontsize=10, framealpha=0.9)
                try:
                    for i, (s, w) in enumerate(zip(seqs, wpms)):
                        if i % max(1, len(seqs) // 10) == 0 or i == len(seqs) - 1:
                            a00.annotate(f'{s}', (s, w), textcoords="offset points", xytext=(0,10), 
                                       ha='center', fontsize=8, color='black')
                except Exception:
                    pass

                try:
                    if accs:
                        # Bar chart for Accuracy
                        a01.bar(seqs, accs, color="#4F0FB0C8", alpha=0.7, label='Accuracy')

                        # Line chart for trend
                        try:
                            if len(seqs) > 1:
                                z = np.polyfit(range(len(seqs)), accs, 1)
                                p = np.poly1d(z)
                                a01.plot(seqs, p(range(len(seqs))), "-", color='#D0021B', linewidth=2, label='Trend')
                        except Exception:
                            pass

                    # Styling for Accuracy chart
                    a01.set_title('Accuracy Trend', color='black', fontsize=14, fontweight='bold', pad=15)
                    a01.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                    a01.tick_params(colors='black', labelsize=10)
                    a01.set_ylabel('Accuracy (%)', color='black', fontsize=12, fontweight='bold')
                    a01.set_xlabel('Test # (1 = oldest)', color='black', fontsize=12, fontweight='bold')
                    a01.set_facecolor('#F8F9FA')
                    a01.spines['top'].set_visible(False)
                    a01.spines['right'].set_visible(False)
                    a01.spines['bottom'].set_linewidth(1.5)
                    a01.spines['left'].set_linewidth(1.5)
                    a01.legend(loc='upper left', fontsize=10, framealpha=0.9)
                except Exception:
                    pass

                try:
                    if times:
                        # Bar chart for Time per Test
                        a10.bar(seqs, times, color="#5900BF", alpha=0.7, label='Time (s)')

                        # Line chart for trend
                        try:
                            if len(seqs) > 1:
                                z = np.polyfit(range(len(seqs)), times, 1)
                                p = np.poly1d(z)
                                a10.plot(seqs, p(range(len(seqs))), "-", color='#D0021B', linewidth=2, label='Trend')
                        except Exception:
                            pass

                    # Styling for Time per Test chart
                    a10.set_title('Time per Test (s)', color='black', fontsize=14, fontweight='bold', pad=15)
                    a10.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                    a10.tick_params(colors='black', labelsize=10)
                    a10.set_ylabel('Seconds', color='black', fontsize=12, fontweight='bold')
                    a10.set_xlabel('Test # (1 = oldest)', color='black', fontsize=12, fontweight='bold')
                    a10.set_facecolor('#F8F9FA')
                    a10.spines['top'].set_visible(False)
                    a10.spines['right'].set_visible(False)
                    a10.spines['bottom'].set_linewidth(1.5)
                    a10.spines['left'].set_linewidth(1.5)
                    a10.legend(loc='upper left', fontsize=10, framealpha=0.9)
                except Exception:
                    pass

                try:
                    from collections import defaultdict
                    
                    daily_counts = defaultdict(int)
                    daily_avg_wpm = defaultdict(list)
                    
                    for row in rows:
                        date_str = row[4] if len(row) > 4 else row[0]
                        wpm = row[1]
                        
                        try:
                            if ' ' in date_str:
                                date_part = date_str.split(' ')[0]
                            else:
                                date_part = date_str
                            daily_counts[date_part] += 1
                            daily_avg_wpm[date_part].append(wpm)
                        except Exception:
                            pass
                    
                    if daily_counts and a30:
                        sorted_dates = sorted(daily_counts.keys())
                        
                        if len(sorted_dates) > 30:
                            sorted_dates = sorted_dates[-30:]
                        
                        counts = [daily_counts[date] for date in sorted_dates]
                        avg_wpms = [sum(daily_avg_wpm[date])/len(daily_avg_wpm[date]) if daily_avg_wpm[date] else 0 for date in sorted_dates]
                        
                        # Enhanced daily progress chart with prominent green bars
                        bars = a30.bar(range(len(sorted_dates)), counts, 
                                     color='#2E7D32', alpha=0.8, label='Tests per day',
                                     edgecolor="#052007", linewidth=1.5)
                        
                        a30_twin = a30.twinx()
                        a30_twin.plot(range(len(sorted_dates)), avg_wpms, color='#FF9800', 
                                    marker='o', linewidth=3, markersize=6, label='Avg WPM')
                        a30_twin.set_ylabel('Average WPM', color='#FF9800')
                        a30_twin.tick_params(colors='#FF9800')
                        
                        a30.set_xlabel('Date', color='black', fontsize=12, fontweight='bold')
                        a30.set_ylabel('Number of Tests', color='#2E7D32', fontsize=12, fontweight='bold')
                        a30.tick_params(colors='black', labelsize=10)
                        a30.set_xticks(range(len(sorted_dates)))
                        a30.set_xticklabels([date.split('-')[1] + '-' + date.split('-')[2] for date in sorted_dates], 
                                          rotation=45, ha='right')
                        
                        # Add value labels on bars with better styling
                        for i, (bar, count) in enumerate(zip(bars, counts)):
                            if count > 0:
                                a30.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts) * 0.02,
                                       str(count), ha='center', va='bottom', fontsize=10, 
                                       fontweight='bold', color='#1B5E20')
                        
                        a30.legend(loc='upper left', fontsize=10, framealpha=0.9)
                        a30_twin.legend(loc='upper right', fontsize=10, framealpha=0.9)
                        a30.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                        
                        # Set background and styling
                        a30.set_facecolor("#826A957B")
                        a30.spines['top'].set_visible(False)
                        a30.spines['right'].set_visible(False)
                        a30.spines['bottom'].set_linewidth(1.5)
                        a30.spines['left'].set_linewidth(1.5)
                        
                except Exception as e:
                    print(f"Error drawing daily progress chart: {e}")

                try:
                    if hasattr(self, 'stats_canvas'):
                        plt.tight_layout()
                        self.stats_canvas.draw()
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"Error drawing stats: {e}")
                
        except Exception as e:
            print(f"_refresh_stats unexpected error: {e}")
        
    # Practice Mode
    def _start_practice(self):
        """Start practice session."""
        if not self.current_user:
            messagebox.showwarning("Name required", "Please enter your name before starting practice.")
            return
        
        try:
            p = self.logic._resolve_data_path("practice_words.txt")
            self.practice_words = []
            for line in p.read_text(encoding="utf-8").splitlines():
                self.practice_words.extend(word for word in line.split() if word)
        except Exception:
            self.practice_words = ["Python", "JavaScript", "Programming", "Function", 
                                 "Variable", "Class", "Method", "Object", "Array"]
        
        self.practice_start_time = None
        self.practice_start_time = time.time()
        self.practice_entry.configure(state="normal")
        self.practice_start_btn.configure(state="disabled")
        self.practice_next_btn.configure(state="normal")
        self.practice_end_btn.configure(state="normal")
        self.practice_entry.delete(0, "end")
        self.practice_entry.focus_set()
        
        for widget in self.practice_history.winfo_children():
            widget.destroy()
        
        self._next_practice_word()
        
    def _next_practice_word(self, skipped=False):
        """Display the next random word."""
        if hasattr(self, 'current_practice_word'):
            typed = self.practice_entry.get().strip()
            if skipped:
                self._add_to_history(self.current_practice_word, "skipped", typed)
            else:
                correct = typed == self.current_practice_word
                self._add_to_history(self.current_practice_word, 
                                   "correct" if correct else "incorrect", 
                                   typed)
        
        if not hasattr(self, 'practice_words') or not self.practice_words:
            messagebox.showinfo("Practice Complete", "You've practiced all available words!")
            self._reset_practice()
            return
            
        word_idx = random.randint(0, len(self.practice_words) - 1)
        self.current_practice_word = self.practice_words.pop(word_idx)
        self.practice_word_label.configure(text=self.current_practice_word)
        self.practice_entry.delete(0, "end")
        self.practice_entry.focus_set()
        
    def _add_to_history(self, target_word, status, typed_word):
        """Add a word to the history sidebar."""
        colors = {
            "correct": "#28a745",
            "incorrect": "#dc3545",
            "skipped": "#6c757d"
        }
        frame = ctk.CTkFrame(self.practice_history)
        frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(frame, 
                    text=target_word,
                    text_color=colors[status],
                    font=("Arial", 14, "bold")).pack(side="left", padx=5)
        
        if status == "incorrect":
            ctk.CTkLabel(frame,
                        text=f"→ {typed_word}",
                        text_color=colors[status],
                        font=("Arial", 12)).pack(side="left", padx=5)
        
    def _on_practice_type(self, event):
        """Handle typing in practice mode."""
        if not hasattr(self, 'current_practice_word'):
            return
            
        typed = self.practice_entry.get().strip()
        if not typed:
            return
            
        if typed == self.current_practice_word:
            self.practice_total += 1
            self.practice_correct += 1
            
            accuracy = (self.practice_correct / self.practice_total) * 100
            self.practice_stats.configure(
                text=f"Words: {self.practice_total} | Correct: {self.practice_correct} | Accuracy: {accuracy:.1f}%"
            )
            
            self.practice_word_label.configure(text_color="green")
            # Use after with a cancellable job ID
            job_id = self.after(200, lambda: self.practice_word_label.configure(text_color=self.text_color))
            self._after_jobs.append(job_id)
            job_id = self.after(200, self._next_practice_word)
            self._after_jobs.append(job_id)
        elif len(typed) >= len(self.current_practice_word):
            self.practice_total += 1
            
            accuracy = (self.practice_correct / self.practice_total) * 100
            self.practice_stats.configure(
                text=f"Words: {self.practice_total} | Correct: {self.practice_correct} | Accuracy: {accuracy:.1f}%"
            )
            
            self.practice_word_label.configure(text_color="red")
            job_id = self.after(200, lambda: self.practice_word_label.configure(text_color=self.text_color))
            self._after_jobs.append(job_id)
            job_id = self.after(200, self._next_practice_word)
            self._after_jobs.append(job_id)
        
    def _end_practice_session(self):
        """End practice session and show results."""
        if not self.practice_start_time or self.practice_total == 0:
            messagebox.showinfo("Practice Session", "No practice session to end.")
            return
            
        time_taken = time.time() - self.practice_start_time
        # Approximate WPM assuming average word length of 5
        wpm = (self.practice_correct * 5) / (time_taken / 60) if time_taken > 0 else 0
        accuracy = (self.practice_correct / self.practice_total) * 100 if self.practice_total > 0 else 0
        
        # Save results
        try:
            name = self.current_user
            self.logic.save_result(name, wpm, accuracy, time_taken, test_type="practice")
            
            # Show results dialog
            result_msg = f"Practice Session Results:\n\n"
            result_msg += f"Words Practiced: {self.practice_total}\n"
            result_msg += f"Correct Words: {self.practice_correct}\n"
            result_msg += f"Accuracy: {accuracy:.1f}%\n"
            result_msg += f"Time: {time_taken:.1f} seconds\n"
            result_msg += f"Estimated WPM: {wpm:.1f}"
            
            messagebox.showinfo("Practice Complete", result_msg)
            
            # Update stats
            self._update_sidebar_stats()
            if hasattr(self, '_refresh_stats'):
                self._refresh_stats()
                
        except Exception as e:
            print(f"Error ending practice session: {e}")
            messagebox.showerror("Error", f"Error ending practice session: {str(e)}")
        
        # Reset practice state
        self._reset_practice()

    def _reset_practice(self):
        """Reset practice session and save results."""
        if self.practice_start_time and self.practice_total > 0:
            time_taken = time.time() - self.practice_start_time
            # Approximate WPM assuming average word length of 5
            wpm = (self.practice_correct * 5) / (time_taken / 60) if time_taken > 0 else 0
            accuracy = (self.practice_correct / self.practice_total) * 100 if self.practice_total > 0 else 0
            try:
                name = self.current_user
                self.logic.save_result(name, wpm, accuracy, time_taken, test_type="practice")
            except Exception as e:
                print(f"Error saving practice result: {e}")

        self.practice_entry.delete(0, "end")
        self.practice_entry.configure(state="disabled")
        self.practice_word_label.configure(text="Click 'Start Practice' to begin")
        self.practice_start_btn.configure(state="normal")
        self.practice_next_btn.configure(state="disabled")
        self.practice_end_btn.configure(state="disabled")
        self.practice_stats.configure(text="Words: 0 | Correct: 0 | Accuracy: 0%")
        self.practice_start_time = None
        self.practice_total = 0
        self.practice_correct = 0

    # Game Mode
    def start_game(self):
        if not self.current_user:
            messagebox.showwarning("Name required", "Please enter your name before starting the game.")
            return
        self._game_running = True
        self._game_words = []
        self.game_canvas.delete("all")
        self._game_score = 0
        self._game_lives = 5
        self.game_score_label.configure(text=f"Score: {self._game_score}")
        self.game_lives_label.configure(text=f"Lives: {self._game_lives}")
        self.game_entry.configure(state="normal")
        self.game_entry.delete(0, "end")
        self.game_entry.focus_set()

        try:
            if getattr(self, 'use_overlay_entry', tk.BooleanVar(False)).get():
                try:
                    self.game_entry.configure(state='disabled')
                except Exception:
                    pass
                try:
                    self.game_overlay_entry.place(in_=self.game_canvas, relx=0.5, rely=0.9, anchor='center')
                    self.game_overlay_entry.delete(0, 'end')
                    self.game_overlay_entry.focus_set()
                    self.game_overlay_entry.bind('<Return>', self._on_game_type)
                    try:
                        self.game_overlay_entry.lift()
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                try:
                    self.game_overlay_entry.place_forget()
                    self.game_overlay_entry.unbind('<Return>')
                except Exception:
                    pass
        except Exception:
            pass

        speed = max(0.5, float(self.game_speed.get()))
        self._game_spawn_interval_ms = int(2000 / speed)
        self._schedule_spawn()
        self._schedule_move()

    def _schedule_spawn(self):
        if not self._game_running:
            return
        self._spawn_game_word()
        self._game_spawn_job = self.after(self._game_spawn_interval_ms, self._schedule_spawn)
        self._after_jobs.append(self._game_spawn_job)

    def _spawn_game_word(self):
        words = getattr(self, 'practice_words', None)
        if not words:
            try:
                p = self.logic._resolve_data_path('practice_words.txt')
                words = [w for line in p.read_text(encoding="utf-8").splitlines() for w in line.split() if w]
            except Exception:
                words = ["python", "code", "function", "variable", "loop", "class"]

        word = random.choice(words)
        cw = self.game_canvas.winfo_width() or 600
        ch = self.game_canvas.winfo_height() or 300
        y = random.randint(30, max(40, ch - 30))
        x = cw + 20
        
        if self._current_theme_mode == "dark":
            word_color = "#FFFFFF"
            shadow_color = "#000000"
        else:
            word_color = "#000000"
            shadow_color = "#FFFFFF"
        
        shadow_id = self.game_canvas.create_text(x+2, y+2, text=word, fill=shadow_color, font=("Arial", 18, "bold"), anchor="w")
        text_id = self.game_canvas.create_text(x, y, text=word, fill=word_color, font=("Arial", 18, "bold"), anchor="w")
        self._game_words.append({"text": word, "x": x, "y": y, "id": text_id, "shadow_id": shadow_id})
        
    def _schedule_move(self):
        if not self._game_running:
            return
        self._move_game_words()
        self._game_move_job = self.after(50, self._schedule_move)
        self._after_jobs.append(self._game_move_job)

    def _move_game_words(self):
        try:
            speed = float(self.game_speed.get())
        except Exception:
            speed = 1.0
        remove = []
        for w in list(self._game_words):
            dx = - (1 + speed) * 2
            try:
                self.game_canvas.move(w['id'], dx, 0)
                self.game_canvas.move(w.get('shadow_id'), dx, 0)
            except Exception:
                pass
            w['x'] += dx
            if w['x'] < -50:
                remove.append(w)
                self._game_lives -= 1
                self._render_lives_icons()
                self._flash_label(self.game_lives_label, "#ac0000", 300)
        for w in remove:
            try:
                self.game_canvas.delete(w['id'])
            except Exception:
                pass
            try:
                if 'shadow_id' in w:
                    self.game_canvas.delete(w['shadow_id'])
            except Exception:
                pass
            try:
                self._game_words.remove(w)
            except Exception:
                pass

        if self._game_lives <= 0:
            self.end_game()

    def _on_game_type(self, event=None):
        # prefer overlay entry if visible
        try:
            if getattr(self, 'use_overlay_entry', tk.BooleanVar(False)).get():
                typed = self.game_overlay_entry.get().strip()
            else:
                typed = self.game_entry.get().strip()
        except Exception:
            typed = self.game_entry.get().strip()
        if not typed:
            return
        matched = None
        for w in list(self._game_words):
            if typed == w['text']:
                matched = w
                break
        if matched:
            # remove from canvas and update score
            try:
                self.game_canvas.delete(matched['id'])
                if 'shadow_id' in matched:
                    self.game_canvas.delete(matched['shadow_id'])
            except Exception:
                pass
            try:
                self._game_words.remove(matched)
            except Exception:
                pass
            self._game_score += 10
            self.game_score_label.configure(text=f"Score: {self._game_score}")
            # flash score label
            self._flash_label(self.game_score_label, '#b6e0ff', 200)
            self.game_entry.delete(0, 'end')

    def end_game(self):
        if not getattr(self, '_game_running', False):
            # Show results even if game wasn't running but score exists
            if hasattr(self, '_game_score') and self._game_score > 0:
                self._show_game_results()
            return
            
        self._game_running = False
        # cancel jobs
        try:
            if self._game_move_job:
                self.after_cancel(self._game_move_job)
        except Exception:
            pass
        try:
            if self._game_spawn_job:
                self.after_cancel(self._game_spawn_job)
        except Exception:
            pass

        # Save game result
        try:
            name = self.current_user
            score = self._game_score
            # For game, we can store score as WPM and accuracy as 100
            self.logic.save_result(name, score, 100, 0, test_type="game")
        except Exception as e:
            print(f"Error saving game result: {e}")

        # Show game results
        self._show_game_results()

        try:
            self._update_sidebar_stats()
            if hasattr(self, '_refresh_stats'):
                self._refresh_stats()
        except Exception as e:
            print(f"Error refreshing stats: {e}")
            
    def _show_game_results(self):
        """Show game session results in a detailed overlay"""
        overlay = ctk.CTkFrame(self.frames['game'], corner_radius=12, fg_color=self.card_bg)
        overlay.place(relx=0.5, rely=0.4, anchor='center')
        
        # Calculate additional stats
        game_duration = getattr(self, '_game_duration', 0)
        words_typed = getattr(self, '_game_score', 0) // 10  # Assuming 10 points per word
        
        ctk.CTkLabel(overlay, text="🎮 Game Session Complete! 🎮", font=("Arial", 24, "bold"), text_color=self.highlight).pack(padx=30, pady=(20,10))
        
        # Results frame
        results_frame = ctk.CTkFrame(overlay, fg_color="transparent")
        results_frame.pack(padx=30, pady=10)
        
        ctk.CTkLabel(results_frame, text=f"Final Score: {self._game_score}", font=("Arial", 18, "bold")).pack(pady=5)
        ctk.CTkLabel(results_frame, text=f"Words Typed: {words_typed}", font=("Arial", 14)).pack(pady=3)
        ctk.CTkLabel(results_frame, text=f"Lives Remaining: {getattr(self, '_game_lives', 0)}", font=("Arial", 14)).pack(pady=3)
        
        # Performance rating
        if self._game_score >= 200:
            rating = "🏆 Excellent!"
            rating_color = "#FFD700"
        elif self._game_score >= 100:
            rating = "⭐ Great Job!"
            rating_color = "#4CAF50"
        elif self._game_score >= 50:
            rating = "👍 Good Work!"
            rating_color = "#2196F3"
        else:
            rating = "💪 Keep Practicing!"
            rating_color = "#FF9800"
            
        rating_label = ctk.CTkLabel(results_frame, text=rating, font=("Arial", 16, "bold"), text_color=rating_color)
        rating_label.pack(pady=10)
        
        ctk.CTkButton(overlay, text="Close Results", command=overlay.destroy, width=120).pack(pady=(10,20))
        
        # disable entry
        try:
            self.game_entry.configure(state='disabled')
        except Exception:
            pass
        # hide overlay entry if visible
        try:
            self.game_overlay_entry.place_forget()
            self.game_overlay_entry.unbind('<Return>')
        except Exception:
            pass

    def _flash_label(self, label, color, duration=200):
        """Temporarily change a label's text color to `color` for `duration` ms then revert."""
        try:
            # Use a smoother flash helper if available
            try:
                orig = label.cget('text_color')
            except Exception:
                try:
                    orig = label.cget('fg')
                except Exception:
                    orig = None
            if orig is None:
                # fallback: instant color swap
                label.configure(text_color=color)
                if duration:
                    self.after(duration, lambda: None)
            else:
                # use smooth flash (to color then back)
                self._smooth_flash(label, orig, color, steps=4, step_ms=max(20, duration // 4))
        except Exception:
            pass

    def _render_lives_icons(self, parent=None):
        """Render heart icons for lives in the status card or provided parent."""
        try:
            container = parent if parent is not None else self
            # find status_card if parent is None
            if parent is None:
                # search for the status_card by attribute (we created it earlier)
                for child in getattr(self, 'frames', {}).get('game', []).winfo_children() if hasattr(self, 'frames') else []:
                    pass
        except Exception:
            pass
        # We'll render in the status_card if available
        try:
            # look for the status_card frame in right panel via attribute search
            # simple approach: place hearts into the game_lives_label's parent
            parent_frame = self.game_lives_label.master
            # clear previous hearts (search for label with name 'heart_')
            for w in parent_frame.winfo_children():
                if getattr(w, '_is_heart', False):
                    w.destroy()
            # create heart icons
            for i in range(self._game_lives if hasattr(self, '_game_lives') else 0):
                h = ctk.CTkLabel(parent_frame, text='♥', text_color="#c00202", font=("Arial", 14, "bold"))
                h._is_heart = True
                h.pack(side='left', padx=2)
        except Exception:
            pass

    def _on_toggle_overlay(self):
        """Toggle showing the overlay entry centered over the game canvas."""
        try:
            use = bool(self.use_overlay_entry.get())
        except Exception:
            use = False
        if use:
            # hide right-panel entry and show overlay
            try:
                self.game_entry.configure(state='disabled')
            except Exception:
                pass
            try:
                # place overlay centered near bottom of canvas
                self.game_overlay_entry.place(in_=self.game_canvas, relx=0.5, rely=0.9, anchor='center')
                self.game_overlay_entry.delete(0, 'end')
                self.game_overlay_entry.focus_set()
                self.game_overlay_entry.bind('<Return>', self._on_game_type)
            except Exception:
                pass
        else:
            # show right-panel entry and hide overlay
            try:
                self.game_overlay_entry.place_forget()
                self.game_overlay_entry.unbind('<Return>')
            except Exception:
                pass
            try:
                self.game_entry.configure(state='normal')
                self.game_entry.focus_set()
            except Exception:
                pass

    # ---------- Visual theming helpers ----------
    def _create_chalk_text(self, parent, text, size=14, color=None, bold=False):
        """Create text with a chalk-like effect"""
        if color is None:
            color = self.text_color
        font_weight = "bold" if bold else "normal"
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", size, font_weight),
            text_color=color
        )
        return label

    def _apply_global_styles(self):
        """Apply consistent styling to all widgets."""
        # Define a consistent button style for all buttons (purple with black text)
        button_style = {
            "corner_radius": 8,
            "height": 40,
            "fg_color": "#7A42F4",  # Purple
            "hover_color": "#6A32E4",  # Darker Purple
            "text_color": "#FFFFFF",  # White text
            "font": self.fonts.get("button", (self.font_family, int(self._base_font_size * self._font_size_multiplier), "bold"))
        }
        
        def _recurse(widget):
            # Apply consistent styling to all child widgets
            for child in widget.winfo_children():
                try:
                    # CTkButton: Apply purple style with black text to ALL buttons
                    if isinstance(child, ctk.CTkButton):
                        child.configure(**button_style)
                    
                    # Labels: default font and appropriate colors for current theme
                    elif isinstance(child, ctk.CTkLabel):
                        try:
                            child.configure(text_color=self.text_color)
                        except Exception:
                            pass
                    
                    # Frames: use theme-appropriate background colors
                    elif isinstance(child, ctk.CTkFrame):
                        # Update frame backgrounds according to theme
                        child.configure(fg_color=self.card_bg)
                    
                    # Textboxes: ensure readable text
                    elif isinstance(child, ctk.CTkTextbox):
                        child.configure(text_color=self.text_color)
                    
                    # Ttk Treeview: style headers for better contrast
                    elif isinstance(child, ttk.Treeview):
                        style = ttk.Style()
                        style.configure("Treeview", background="#E8E2F7", fieldbackground="#E8E2F7", foreground="black")
                        style.configure("Treeview.Heading", font=self.fonts['subheader'], foreground='black')
                
                except Exception:
                    pass
                
                # Recursively process child widgets
                _recurse(child)

        # Apply styles to navigation buttons specifically
        for button in self.nav_buttons.values():
            if isinstance(button, ctk.CTkButton):
                button.configure(**button_style)
        
        # Recursively apply styles to all widgets
        try:
            _recurse(self)
        except Exception:
            pass

    def _apply_font_scaling(self):
        """Scale fonts for common widgets based on the multiplier, preserving original sizes."""
        try:
            def _recurse(widget):
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, ctk.CTkTextbox)):
                            try:
                                current_font = child.cget('font')
                            except Exception:
                                current_font = None
                            base_size = None
                            family = self.font_family
                            weight = None
                            if isinstance(current_font, (tuple, list)) and len(current_font) >= 2:
                                family = current_font[0]
                                size = current_font[1]
                                if len(current_font) >= 3:
                                    weight = current_font[2]
                                key = id(child)
                                if key not in self._original_label_fonts:
                                    if isinstance(size, int):
                                        self._original_label_fonts[key] = (family, size, weight)
                                base = self._original_label_fonts.get(key)
                                if base:
                                    family, base_size, weight = base
                                else:
                                    base_size = self._base_font_size
                            else:
                                base_size = self._base_font_size
                            new_size = int(max(10, base_size * self._font_size_multiplier))
                            if weight:
                                child.configure(font=(family, new_size, weight))
                            else:
                                child.configure(font=(family, new_size))
                    except Exception:
                        pass
                    _recurse(child)
            _recurse(self)
        except Exception:
            pass

    def _smooth_flash(self, label, color_from, color_to, steps=6, step_ms=40):
        """Animate a label's text color from color_from to color_to and back for a smooth flash.
        Uses simple linear timing with `after` to avoid blocking.
        """
        # Pre-compute intermediate colors if possible (fallback to instant swap)
        try:
            # very simple two-step flash: to color_to then back to color_from
            label.configure(text_color=color_to)
            self.after(steps * step_ms, lambda: label.configure(text_color=color_from))
        except Exception:
            try:
                label.configure(text_color=color_to)
                self.after(200, lambda: label.configure(text_color=color_from))
            except Exception:
                pass

