import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import threading
import time
import numpy as np

class MusicLearnerGUI(ctk.CTk):
    BUTTON_DEFAULT = "#2a2a2a"
    BUTTON_DISABLED = "#1e1e1e"
    BUTTON_LIKE_ACTIVE = "#1ed760"
    BUTTON_DISLIKE_ACTIVE = "#ef4444"
    GENRE_ITEM_BG = "#1a1a1a"
    GENRE_ITEM_HOVER = "#202020"
    GENRE_ITEM_HEIGHT = 65
    GENRE_ITEM_SPACING = 71

    def __init__(self, spotify_client, learning_engine, storage):
        super().__init__()

        self.spotify = spotify_client
        self.engine = learning_engine
        self.storage = storage

        self.title("Spotify AI Learner")
        self.state('zoomed')

        self.is_running = False
        self.current_recommended_track = None
        self.auto_play_enabled = True
        self.last_track_id = None
        self.last_progress_ms = 0
        self.current_rating = None
        self.rated_tracks = {}
        self.counted_tracks = set()
        self.committed_tracks = {}
        self.session_played_tracks = set()
        self.ui_update_lock = threading.Lock()
        self.pending_ui_updates = False
        self.genre_widgets = {}
        self._playlist_updating = False
        self.track_history = []
        self.track_history_index = -1

        self.bg_color = "#0a0a0a"
        self.card_bg = "#151515"
        self.accent_green = "#1ed760"
        self.accent_purple = "#a855f7"
        self.text_primary = "#ffffff"
        self.text_secondary = "#a0a0a0"

        self.configure(fg_color=self.bg_color)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=0, minsize=350)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        self.left_column.grid_rowconfigure(0, weight=0)
        self.left_column.grid_rowconfigure(1, weight=0)
        self.left_column.grid_rowconfigure(2, weight=1, minsize=450)
        self.left_column.grid_rowconfigure(3, weight=0)
        self.left_column.grid_columnconfigure(0, weight=1)

        self.right_column = ctk.CTkFrame(self.main_container, fg_color=self.card_bg, corner_radius=20)
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        self.setup_left_column()
        self.setup_right_column()
        self.setup_controls()

        self.bind_all("<Up>", lambda e: self.select_rating(1))
        self.bind_all("<Down>", lambda e: self.select_rating(-1))
        self.bind_all("<Right>", lambda e: self.skip_to_next())
        self.bind_all("<Left>", lambda e: self.go_back())

    def setup_left_column(self):
        header_frame = ctk.CTkFrame(self.left_column, fg_color="transparent", height=80)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_propagate(False)

        title_label = ctk.CTkLabel(
            header_frame,
            text="AI Music Discovery",
            font=("SF Pro Display", 36, "bold"),
            text_color=self.text_primary
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Powered by adaptive neural recommendations",
            font=("SF Pro Text", 13),
            text_color=self.text_secondary
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))

        self.start_button = ctk.CTkButton(
            self.left_column,
            text="START LEARNING",
            command=self.toggle_tracking,
            height=56,
            font=("SF Pro Display", 16, "bold"),
            fg_color=self.accent_green,
            hover_color="#1fdf64",
            corner_radius=28,
            border_width=0
        )
        self.start_button.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self.rec_card = ctk.CTkFrame(self.left_column, fg_color=self.card_bg, corner_radius=20)
        self.rec_card.grid(row=2, column=0, sticky="nsew", pady=(0, 15))

        self.rec_card.grid_rowconfigure(0, weight=0)
        self.rec_card.grid_rowconfigure(1, weight=1)
        self.rec_card.grid_rowconfigure(2, weight=0)
        self.rec_card.grid_columnconfigure(0, weight=1)

        rec_header_frame = ctk.CTkFrame(self.rec_card, fg_color="transparent", height=40)
        rec_header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 0))
        rec_header_frame.grid_propagate(False)

        self.rec_label = ctk.CTkLabel(
            rec_header_frame,
            text="AI RECOMMENDATION",
            font=("SF Pro Text", 11, "bold"),
            text_color=self.text_secondary
        )
        self.rec_label.pack(side="left")

        self.mood_indicator = ctk.CTkLabel(
            rec_header_frame,
            text="",
            font=("SF Pro Text", 11),
            text_color=self.accent_purple
        )
        self.mood_indicator.pack(side="right")

        content_frame = ctk.CTkFrame(self.rec_card, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=15)

        self.rec_album_label = ctk.CTkLabel(content_frame, text="")
        self.rec_album_label.pack(expand=True)

        self.rec_track_label = ctk.CTkLabel(
            content_frame,
            text="Press START to begin learning",
            font=("SF Pro Display", 16),
            text_color=self.text_primary,
            wraplength=500
        )
        self.rec_track_label.pack(pady=(10, 0))

        button_container = ctk.CTkFrame(self.rec_card, fg_color="transparent", height=90)
        button_container.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 20))
        button_container.grid_propagate(False)

        controls_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        controls_frame.pack(expand=True)

        self.thumbs_down_button = ctk.CTkButton(
            controls_frame,
            text="-",
            command=lambda: self.select_rating(-1),
            width=60,
            height=60,
            font=("Arial", 32, "bold"),
            fg_color=self.BUTTON_DEFAULT,
            hover_color="#ff4444",
            corner_radius=30,
            border_width=0,
            state="disabled",
            text_color=self.text_secondary
        )
        self.thumbs_down_button.pack(side="left", padx=8)

        self.back_button = ctk.CTkButton(
            controls_frame,
            text="<",
            command=self.go_back,
            width=60,
            height=60,
            font=("Arial", 32, "bold"),
            fg_color=self.BUTTON_DEFAULT,
            hover_color="#404040",
            corner_radius=30,
            border_width=0,
            state="disabled",
            text_color=self.text_secondary
        )
        self.back_button.pack(side="left", padx=8)

        self.skip_button = ctk.CTkButton(
            controls_frame,
            text=">",
            command=self.skip_to_next,
            width=60,
            height=60,
            font=("Arial", 32, "bold"),
            fg_color=self.BUTTON_DEFAULT,
            hover_color="#404040",
            corner_radius=30,
            border_width=0,
            state="disabled",
            text_color=self.text_secondary
        )
        self.skip_button.pack(side="left", padx=8)

        self.thumbs_up_button = ctk.CTkButton(
            controls_frame,
            text="+",
            command=lambda: self.select_rating(1),
            width=60,
            height=60,
            font=("Arial", 32, "bold"),
            fg_color=self.BUTTON_DEFAULT,
            hover_color=self.accent_green,
            corner_radius=30,
            border_width=0,
            state="disabled",
            text_color=self.text_secondary
        )
        self.thumbs_up_button.pack(side="left", padx=8)

        stats_frame = ctk.CTkFrame(self.left_column, fg_color="#1a1a1a", corner_radius=15, height=50)
        stats_frame.grid(row=3, column=0, sticky="ew")
        stats_frame.grid_propagate(False)

        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="Tracks: 0",
            font=("SF Pro Text", 12),
            text_color=self.text_secondary
        )
        self.stats_label.pack(side="left", padx=15, pady=12)

        self.adaptation_label = ctk.CTkLabel(
            stats_frame,
            text="Exploring",
            font=("SF Pro Text", 12, "bold"),
            text_color=self.accent_green
        )
        self.adaptation_label.pack(side="right", padx=15, pady=12)

    def setup_right_column(self):
        leaderboard_header_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        leaderboard_header_frame.pack(fill="x", padx=20, pady=(20, 5))

        leaderboard_header = ctk.CTkLabel(
            leaderboard_header_frame,
            text="GENRE LEADERBOARD",
            font=("SF Pro Text", 11, "bold"),
            text_color=self.text_secondary
        )
        leaderboard_header.pack(side="left")

        info_label = ctk.CTkLabel(
            leaderboard_header_frame,
            text="\u2139",
            font=("SF Pro Text", 14),
            text_color=self.text_secondary,
            cursor="hand2"
        )
        info_label.pack(side="right")
        info_label.bind("<Enter>", lambda e: self.show_percentage_tooltip())
        info_label.bind("<Leave>", lambda e: self.hide_percentage_tooltip())

        self.tooltip_label = ctk.CTkLabel(
            self.right_column,
            text="% = AI's confidence you'll like this genre\n(Based on Thompson sampling)",
            font=("SF Pro Text", 10),
            text_color=self.text_secondary,
            fg_color="#1a1a1a",
            corner_radius=5,
            padx=10,
            pady=5
        )

        scroll_container = ctk.CTkFrame(self.right_column, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=10, pady=(10, 20))

        self.genre_scroll = ctk.CTkScrollableFrame(
            scroll_container,
            fg_color="transparent",
            scrollbar_button_color="#2a2a2a",
            scrollbar_button_hover_color="#404040",
            width=330
        )
        self.genre_scroll.pack(fill="both", expand=True)

        self.genre_container = ctk.CTkFrame(self.genre_scroll, fg_color="transparent")
        self.genre_container.pack(fill="x", expand=True)

        self.genre_items = []
        self.update_genre_leaderboard()

    def show_percentage_tooltip(self):
        self.tooltip_label.place(x=20, y=50)

    def hide_percentage_tooltip(self):
        self.tooltip_label.place_forget()

    def setup_controls(self):
        controls_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.playlist_button = ctk.CTkButton(
            controls_frame,
            text="Update Playlist",
            command=self.update_playlist,
            height=36,
            font=("SF Pro Text", 12),
            fg_color="#1e3a5f",
            hover_color="#2a4a6f",
            corner_radius=18,
            border_width=0,
            text_color=self.text_primary
        )
        self.playlist_button.pack(fill="x", pady=(0, 8))

        clear_history_button = ctk.CTkButton(
            controls_frame,
            text="Clear History",
            command=self.clear_history,
            height=36,
            font=("SF Pro Text", 12),
            fg_color=self.BUTTON_DEFAULT,
            hover_color="#404040",
            corner_radius=18,
            border_width=0,
            text_color=self.text_secondary
        )
        clear_history_button.pack(fill="x")

    def update_playlist(self):
        if self._playlist_updating:
            return
        self._playlist_updating = True
        self.playlist_button.configure(text="Generating...", state="disabled")
        threading.Thread(target=self._update_playlist_async, daemon=True).start()

    def _update_playlist_async(self):
        try:
            tracks = self.engine.generate_playlist_tracks(self.session_played_tracks, count=25)
            if not tracks:
                self.after(0, lambda: self._playlist_done("No tracks found", False))
                return

            track_uris = [t['uri'] for t in tracks if t.get('uri')]
            result = self.spotify.update_playlist(track_uris)

            if result['success']:
                message = f"Playlist updated ({result['track_count']} tracks)"
                self.after(0, lambda: self._playlist_done(message, True))
            else:
                self.after(0, lambda: self._playlist_done(f"Error: {result.get('error', 'Unknown')}", False))
        except Exception as e:
            print(f"Error updating playlist: {e}")
            self.after(0, lambda: self._playlist_done("Playlist update failed", False))

    def _playlist_done(self, message, success):
        self._playlist_updating = False
        color = self.accent_green if success else "#ef4444"
        self.playlist_button.configure(text=message, state="normal", fg_color=color)
        self.after(3000, lambda: self.playlist_button.configure(
            text="Update Playlist", fg_color="#1e3a5f"
        ))

    def update_genre_leaderboard(self):
        if not hasattr(self, 'ui_update_lock'):
            return
        with self.ui_update_lock:
            if self.pending_ui_updates:
                return
            self.pending_ui_updates = True
        self.after(500, self._do_update_genre_leaderboard)

    def _do_update_genre_leaderboard(self):
        with self.ui_update_lock:
            self.pending_ui_updates = False

        try:
            aggregated_scores = self.engine.get_aggregated_genre_scores()
            genre_data = []

            for genre, scores in aggregated_scores.items():
                try:
                    alpha = scores['alpha']
                    beta = scores['beta']
                    history = scores.get('history', [])
                    interactions = len(history)

                    if interactions == 0:
                        continue

                    probability = np.random.beta(alpha, beta)
                    genre_data.append({
                        'name': genre,
                        'probability': probability,
                        'samples': interactions,
                        'total_interactions': alpha + beta,
                        'subgenres': scores.get('subgenres', [])
                    })
                except Exception as e:
                    print(f"Error processing genre {genre}: {e}")
                    continue

            if not genre_data:
                for genre_name in list(self.genre_widgets.keys()):
                    if genre_name in self.genre_widgets:
                        self.genre_widgets[genre_name]['frame'].destroy()
                        del self.genre_widgets[genre_name]
                self.genre_items.clear()

                if not any(isinstance(w, ctk.CTkLabel) and "Start rating" in w.cget("text")
                          for w in self.genre_container.winfo_children()):
                    no_data_label = ctk.CTkLabel(
                        self.genre_container,
                        text="Start rating tracks to\nbuild your taste profile",
                        font=("SF Pro Text", 13),
                        text_color=self.text_secondary,
                        justify="center"
                    )
                    no_data_label.place(relx=0.5, rely=0.5, anchor="center")
                    self.genre_items.append(no_data_label)
                return

            for widget in self.genre_container.winfo_children():
                if isinstance(widget, ctk.CTkLabel) and "Start rating" in widget.cget("text"):
                    widget.destroy()
                    if widget in self.genre_items:
                        self.genre_items.remove(widget)

            genre_data.sort(key=lambda x: (x['probability'], x['samples']), reverse=True)
            top_genres = genre_data[:15]

            new_genre_names = {g['name'] for g in top_genres}
            old_genre_names = set(self.genre_widgets.keys())

            for genre_name in old_genre_names - new_genre_names:
                self._remove_genre_widget(genre_name)

            for i, genre_info in enumerate(top_genres):
                genre_name = genre_info['name']
                new_rank = i + 1

                if genre_name in self.genre_widgets:
                    self._update_genre_data(
                        genre_name,
                        genre_info['probability'],
                        genre_info['samples'],
                        new_rank
                    )
                else:
                    self._create_genre_widget_static(
                        genre_info['name'],
                        genre_info['probability'],
                        genre_info['samples'],
                        new_rank
                    )

            self._animate_genre_positions(top_genres)

        except Exception as e:
            import traceback
            print(f"Error updating genre leaderboard: {e}")
            traceback.print_exc()

    def _update_genre_data(self, genre_name, probability, samples, new_rank):
        try:
            if genre_name not in self.genre_widgets:
                return

            widget_data = self.genre_widgets[genre_name]
            widget_data['rank'] = new_rank
            widget_data['rank_label'].configure(text=f"#{new_rank}")

            widget_data['samples_label'].configure(
                text=f"{samples} rating{'s' if samples != 1 else ''}"
            )

            widget_data['probability'] = probability
            prob_color = self.get_probability_color(probability)

            target_width = max(1, int(probability * 175))
            widget_data['prob_bar_fill'].configure(width=target_width, fg_color=prob_color)
            widget_data['prob_bar_fill'].place(x=0, y=0)

            widget_data['percentage_label'].configure(
                text=f"{int(probability * 100)}%",
                text_color=prob_color
            )
        except Exception as e:
            print(f"Error updating genre data {genre_name}: {e}")

    def _remove_genre_widget(self, genre_name):
        try:
            if genre_name in self.genre_widgets:
                self.genre_widgets[genre_name]['frame'].destroy()
                del self.genre_widgets[genre_name]
        except Exception:
            pass

    def _create_genre_widget_static(self, genre_name, probability, samples, rank):
        item_frame = ctk.CTkFrame(
            self.genre_container,
            fg_color=self.GENRE_ITEM_BG,
            corner_radius=10,
            height=self.GENRE_ITEM_HEIGHT,
            width=310,
            cursor="hand2"
        )
        item_frame.place(x=5, y=(rank - 1) * self.GENRE_ITEM_SPACING)

        click_handler = lambda e, g=genre_name: self.play_genre(g)
        item_frame.bind("<Button-1>", click_handler)
        item_frame.bind("<Enter>", lambda e, f=item_frame: f.configure(fg_color=self.GENRE_ITEM_HOVER))
        item_frame.bind("<Leave>", lambda e, f=item_frame: f.configure(fg_color=self.GENRE_ITEM_BG))

        rank_label = ctk.CTkLabel(
            item_frame,
            text=f"#{rank}",
            font=("SF Pro Display", 12, "bold"),
            text_color=self.text_secondary,
            width=40,
            anchor="w"
        )
        rank_label.place(x=12, y=22)
        rank_label.bind("<Button-1>", click_handler)

        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent", width=180, height=self.GENRE_ITEM_HEIGHT)
        info_frame.place(x=55, y=0)
        info_frame.bind("<Button-1>", click_handler)

        genre_label = ctk.CTkLabel(
            info_frame,
            text=genre_name.title(),
            font=("SF Pro Display", 13, "bold"),
            text_color=self.text_primary,
            anchor="w",
            width=180
        )
        genre_label.place(x=0, y=8)
        genre_label.bind("<Button-1>", click_handler)

        samples_label = ctk.CTkLabel(
            info_frame,
            text=f"{samples} rating{'s' if samples != 1 else ''}",
            font=("SF Pro Text", 11),
            text_color=self.text_secondary,
            anchor="w",
            width=180
        )
        samples_label.place(x=0, y=28)
        samples_label.bind("<Button-1>", click_handler)

        prob_bar_bg = ctk.CTkFrame(info_frame, fg_color="#0a0a0a", width=180, height=6, corner_radius=3)
        prob_bar_bg.place(x=0, y=48)
        prob_bar_bg.bind("<Button-1>", click_handler)

        prob_bar_fill = ctk.CTkFrame(
            prob_bar_bg,
            fg_color=self.get_probability_color(probability),
            width=max(1, int(probability * 175)),
            height=6,
            corner_radius=3
        )
        prob_bar_fill.place(x=0, y=0)
        prob_bar_fill.bind("<Button-1>", click_handler)

        percentage_label = ctk.CTkLabel(
            item_frame,
            text=f"{int(probability * 100)}%",
            font=("SF Pro Display", 16, "bold"),
            text_color=self.get_probability_color(probability),
            anchor="e",
            width=50
        )
        percentage_label.place(x=240, y=22)
        percentage_label.bind("<Button-1>", click_handler)

        self.genre_widgets[genre_name] = {
            'frame': item_frame,
            'rank': rank,
            'current_y': (rank - 1) * self.GENRE_ITEM_SPACING,
            'target_y': (rank - 1) * self.GENRE_ITEM_SPACING,
            'rank_label': rank_label,
            'genre_label': genre_label,
            'samples_label': samples_label,
            'prob_bar_fill': prob_bar_fill,
            'percentage_label': percentage_label,
            'probability': probability,
        }

        self.genre_items.append(item_frame)

    def _animate_genre_positions(self, sorted_genre_data):
        try:
            total_height = len(sorted_genre_data) * self.GENRE_ITEM_SPACING
            self.genre_container.configure(height=total_height)

            for i, genre_info in enumerate(sorted_genre_data):
                genre_name = genre_info['name']
                if genre_name in self.genre_widgets:
                    self.genre_widgets[genre_name]['target_y'] = i * self.GENRE_ITEM_SPACING

            self._smooth_move_widgets()
        except Exception as e:
            print(f"Error animating positions: {e}")

    def _smooth_move_widgets(self, step=0):
        ease_factor = 0.4
        try:
            any_moving = False

            for genre_name, widget_data in self.genre_widgets.items():
                current_y = widget_data['current_y']
                target_y = widget_data['target_y']

                if abs(current_y - target_y) > 1:
                    any_moving = True
                    diff = target_y - current_y
                    new_y = current_y + diff * ease_factor
                    widget_data['current_y'] = new_y
                    widget_data['frame'].place(x=5, y=int(new_y))
                elif current_y != target_y:
                    widget_data['current_y'] = target_y
                    widget_data['frame'].place(x=5, y=int(target_y))

            if any_moving and step < 15:
                self.after(20, lambda: self._smooth_move_widgets(step + 1))
        except Exception as e:
            print(f"Error in smooth move: {e}")

    def play_genre(self, genre_name):
        if not self.is_running:
            return
        print(f"Playing track from genre: {genre_name}")
        threading.Thread(target=self.fetch_genre_track, args=(genre_name,), daemon=True).start()

    def fetch_genre_track(self, genre_name):
        try:
            from genre_taxonomy import GENRE_TAXONOMY
            parent = GENRE_TAXONOMY.get_parent_genre(genre_name.lower())
            search_genre = parent if parent else genre_name

            results = self.spotify.client.search(q=f"genre:{search_genre}", type='track', limit=50)

            if not results or 'tracks' not in results or not results['tracks']:
                return

            tracks = results['tracks']['items']
            if not tracks:
                return

            import random
            available_tracks = [t for t in tracks if t.get('id') and t['id'] not in self.session_played_tracks]
            if not available_tracks:
                available_tracks = [t for t in tracks if t.get('id')]

            if not available_tracks:
                return

            track = random.choice(available_tracks)
            if not track.get('id') or not track.get('name'):
                return

            track_data = {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist.get('name', 'Unknown') for artist in track.get('artists', [])]),
                'album_cover': track['album']['images'][0]['url'] if track.get('album') and track['album'].get('images') else None,
                'uri': track.get('uri', '')
            }

            self.current_recommended_track = track_data
            self.session_played_tracks.add(track['id'])
            self.after(0, lambda: self.update_recommendation_ui(track_data))

            if self.auto_play_enabled:
                time.sleep(0.3)
                self.after(0, self.play_recommended)
        except Exception as e:
            import traceback
            print(f"Error fetching genre track for '{genre_name}': {e}")
            traceback.print_exc()
            self.after(0, lambda: self.rec_track_label.configure(
                text="Couldn't load genre track. Try another genre."
            ))

    def get_probability_color(self, probability):
        if probability >= 0.7:
            return self.accent_green
        elif probability >= 0.5:
            return "#fbbf24"
        elif probability >= 0.3:
            return "#f97316"
        else:
            return "#ef4444"

    def _configure_button(self, button, state=None, fg_color=None, text_color=None):
        if not hasattr(self, '_button_states'):
            self._button_states = {}
        button_id = id(button)
        current = self._button_states.get(button_id, {})
        kwargs = {}
        if state is not None and current.get('state') != state:
            kwargs['state'] = state
        if fg_color is not None and current.get('fg_color') != fg_color:
            kwargs['fg_color'] = fg_color
        if text_color is not None and current.get('text_color') != text_color:
            kwargs['text_color'] = text_color
        if kwargs:
            button.configure(**kwargs)
            self._button_states[button_id] = {**current, **kwargs}

    def _set_buttons_for_new_track(self):
        self._configure_button(self.thumbs_up_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        self._configure_button(self.thumbs_down_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        self._configure_button(self.skip_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        has_history = self.track_history_index > 0
        self._configure_button(
            self.back_button,
            state="normal" if has_history else "disabled",
            fg_color=self.BUTTON_DEFAULT if has_history else self.BUTTON_DISABLED,
            text_color=self.text_secondary
        )

    def _set_buttons_disabled(self):
        self._configure_button(self.thumbs_up_button, state="disabled", fg_color=self.BUTTON_DISABLED)
        self._configure_button(self.thumbs_down_button, state="disabled", fg_color=self.BUTTON_DISABLED)
        self._configure_button(self.skip_button, state="disabled", fg_color=self.BUTTON_DISABLED)
        self._configure_button(self.back_button, state="disabled", fg_color=self.BUTTON_DISABLED)

    def _set_buttons_for_rating(self, rating):
        if rating > 0:
            self._configure_button(self.thumbs_up_button, state="normal", fg_color=self.BUTTON_LIKE_ACTIVE, text_color=self.text_primary)
            self._configure_button(self.thumbs_down_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        else:
            self._configure_button(self.thumbs_down_button, state="normal", fg_color=self.BUTTON_DISLIKE_ACTIVE, text_color=self.text_primary)
            self._configure_button(self.thumbs_up_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        self._configure_button(self.skip_button, state="normal", fg_color=self.BUTTON_DEFAULT, text_color=self.text_secondary)
        has_history = self.track_history_index > 0
        self._configure_button(
            self.back_button,
            state="normal" if has_history else "disabled",
            fg_color=self.BUTTON_DEFAULT if has_history else self.BUTTON_DISABLED,
            text_color=self.text_secondary
        )

    def select_rating(self, rating):
        if not self.current_recommended_track:
            return

        track_id = self.current_recommended_track['id']
        previous_rating = self.rated_tracks.get(track_id)

        if previous_rating == rating:
            was_counted = track_id in self.counted_tracks
            self.current_rating = None
            self.rated_tracks.pop(track_id, None)
            if was_counted:
                self.counted_tracks.remove(track_id)
            self._set_buttons_for_new_track()
            self.show_feedback("Rating removed", self.text_secondary)
            self.undo_rating(track_id, rating, was_counted)
            return

        replacing = previous_rating is not None and previous_rating != rating
        was_counted = track_id in self.counted_tracks
        if replacing:
            self.undo_rating(track_id, previous_rating, was_counted)
            self.show_feedback(
                f"Replaced {'like' if previous_rating > 0 else 'dislike'} with {'like' if rating > 0 else 'dislike'}",
                self.accent_green if rating > 0 else "#ef4444"
            )

        self.current_rating = rating
        self.rated_tracks[track_id] = rating
        self._set_buttons_for_rating(rating)
        self.save_current_rating(replacing=replacing, was_counted=was_counted)

    def save_current_rating(self, replacing=False, was_counted=False):
        if self.current_rating is not None and self.current_recommended_track:
            track_id = self.current_recommended_track['id']
            rating = self.current_rating

            if not replacing and self.committed_tracks.get(track_id) == rating:
                return

            should_count = not replacing and track_id not in self.counted_tracks

            print(f"Saving rating for {track_id}: {rating} (replacing={replacing}, should_count={should_count})")

            threading.Thread(
                target=self.process_rating,
                args=(track_id, rating, False, replacing, should_count),
                daemon=True
            ).start()

    def undo_rating(self, track_id, rating, was_counted):
        print(f"Undoing rating for {track_id}: {rating} (was_counted={was_counted})")
        threading.Thread(
            target=self.process_rating,
            args=(track_id, rating, True, False, was_counted),
            daemon=True
        ).start()

    def toggle_tracking(self):
        if not self.is_running:
            self.is_running = True
            self.session_played_tracks.clear()
            self.track_history.clear()
            self.track_history_index = -1
            self.start_button.configure(
                text="STOP LEARNING",
                fg_color="#ef4444",
                hover_color="#dc2626"
            )

            self.track_end_thread = threading.Thread(target=self.monitor_track_end, daemon=True)
            self.track_end_thread.start()

            self.get_new_recommendation()
        else:
            self.is_running = False
            self.start_button.configure(
                text="START LEARNING",
                fg_color=self.accent_green,
                hover_color="#1fdf64"
            )

    def monitor_track_end(self):
        while self.is_running:
            try:
                current = self.spotify.get_current_track()
                if current and self.current_recommended_track:
                    if current['id'] == self.current_recommended_track['id']:
                        duration_ms = current.get('duration_ms', 0)
                        progress_ms = current.get('progress_ms', 0)

                        if duration_ms > 0 and progress_ms >= duration_ms - 3000:
                            print(f"Track ending, saving rating and auto-advancing...")
                            self.after(0, self.save_current_rating)
                            time.sleep(2)
                            self.after(0, self.skip_to_next)
                            time.sleep(5)
            except Exception as e:
                print(f"Error monitoring track end: {e}")
            time.sleep(1)

    def load_album_cover(self, url, label_widget, size=(180, 180)):
        try:
            response = requests.get(url, timeout=5)
            image = Image.open(BytesIO(response.content))
            image = image.resize(size)
            self.after(0, lambda img=image: self._apply_album_cover(img, label_widget, size))
        except Exception as e:
            print(f"Error loading album cover: {e}")

    def _apply_album_cover(self, image, label_widget, size):
        try:
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=size)
            label_widget.configure(image=photo, text="")
            label_widget.image = photo
        except Exception as e:
            print(f"Error applying album cover: {e}")

    def set_image(self, label_widget, photo):
        label_widget.configure(image=photo, text="")
        label_widget.image = photo

    def get_new_recommendation(self):
        self.rec_track_label.configure(text="Finding your next track...")
        self.current_rating = None
        threading.Thread(target=self.fetch_recommendation_async, daemon=True).start()

    def fetch_recommendation_async(self):
        try:
            print("Fetching recommendation...")
            start_time = time.time()

            track = self.engine.get_recommended_track(self.session_played_tracks)

            elapsed = time.time() - start_time
            print(f"Recommendation found in {elapsed:.2f}s")

            if track and track.get('id') and track.get('name'):
                print(f"Found track: {track['name']} by {track.get('artist', 'Unknown')}")
                self.current_recommended_track = track
                self.session_played_tracks.add(track['id'])

                self.track_history = self.track_history[:self.track_history_index + 1]
                self.track_history.append(track)
                self.track_history_index = len(self.track_history) - 1

                self.after(0, lambda: self.update_recommendation_ui(track))

                if self.auto_play_enabled:
                    time.sleep(0.5)
                    self.after(0, self.play_recommended)
            else:
                print("No valid track found")
                self.after(0, lambda: self.rec_track_label.configure(
                    text="Couldn't find a track. Trying again..."
                ))
        except Exception as e:
            import traceback
            print(f"Error fetching recommendation: {e}")
            traceback.print_exc()
            error_msg = "Connection error. Check your internet." if "ConnectionError" in str(type(e)) else "Error loading track."
            self.after(0, lambda msg=error_msg: self.rec_track_label.configure(text=msg))

    def update_recommendation_ui(self, track):
        self.rec_track_label.configure(text=f"{track['name']}\n{track['artist']}")

        existing_rating = self.rated_tracks.get(track['id'])
        if existing_rating is not None:
            self.current_rating = existing_rating
            self._set_buttons_for_rating(existing_rating)
        else:
            self.current_rating = None
            self._set_buttons_for_new_track()

        if track['album_cover']:
            threading.Thread(
                target=self.load_album_cover,
                args=(track['album_cover'], self.rec_album_label, (180, 180)),
                daemon=True
            ).start()

        self.update_stats()
        self.update_mood_indicator()

    def update_mood_indicator(self):
        if self.engine.session_ratings >= 3:
            mood_desc = self.get_mood_description()
            self.mood_indicator.configure(text=f"\u266a {mood_desc}")
        else:
            self.mood_indicator.configure(text="\u2022 Learning...")

    def get_mood_description(self):
        mean = self.engine.session_feature_mean

        energy = mean[1]
        valence = mean[2]
        danceability = mean[0]

        if energy > 0.7 and valence > 0.6:
            return "Energetic"
        elif energy > 0.7 and valence < 0.4:
            return "Intense"
        elif energy < 0.4 and valence > 0.6:
            return "Chill"
        elif energy < 0.4 and valence < 0.4:
            return "Melancholic"
        elif danceability > 0.7:
            return "Groovy"
        else:
            return "Balanced"

    def process_rating(self, track_id, rating, is_undo=False, is_replacement=False, should_count=False):
        try:
            print(f"Processing rating for track {track_id}: {rating} (undo={is_undo}, replacement={is_replacement}, should_count={should_count})")
            self.engine.update_with_rating(track_id, rating, is_undo=is_undo, should_count=should_count)

            if should_count and not is_undo:
                self.counted_tracks.add(track_id)
            elif is_undo and track_id in self.counted_tracks:
                self.counted_tracks.remove(track_id)

            if is_undo:
                if track_id in self.committed_tracks:
                    del self.committed_tracks[track_id]
            else:
                self.committed_tracks[track_id] = rating

            print(f"Rating processed! Total: {self.engine.total_ratings}, Session: {self.engine.session_ratings}")

            self.after(100, self._safe_ui_update)

        except Exception as e:
            import traceback
            print(f"Error processing rating: {e}")
            traceback.print_exc()

    def _safe_ui_update(self):
        try:
            self.update_stats()
            self.update_genre_leaderboard()
        except Exception as e:
            print(f"Error in UI update: {e}")

    def skip_to_next(self):
        if not self.is_running:
            return
        if self.track_history_index < len(self.track_history) - 1:
            self.track_history_index += 1
            track = self.track_history[self.track_history_index]
            self.current_recommended_track = track
            self.update_recommendation_ui(track)
            if self.auto_play_enabled:
                self.play_recommended()
        else:
            print("Skipping to next track...")
            self.get_new_recommendation()

    def go_back(self):
        if not self.is_running:
            return
        if self.track_history_index <= 0:
            return

        self.track_history_index -= 1
        track = self.track_history[self.track_history_index]
        self.current_recommended_track = track
        self.update_recommendation_ui(track)

        if self.auto_play_enabled:
            self.play_recommended()

    def show_feedback(self, message, color):
        self.rec_label.configure(text_color=color)
        self.after(600, lambda: self.rec_label.configure(text_color=self.text_secondary))

    def play_recommended(self):
        if self.current_recommended_track:
            print(f"Playing: {self.current_recommended_track['name']}")
            threading.Thread(
                target=self.spotify.play_track,
                args=(self.current_recommended_track['uri'],),
                daemon=True
            ).start()

    def update_stats(self):
        try:
            total_ratings = self.engine.total_ratings
            session_ratings = self.engine.session_ratings

            self.stats_label.configure(text=f"Tracks: {total_ratings}")

            if self.engine.consecutive_dislikes >= 2:
                mode = "Exploring"
                color = "#f97316"
            elif self.engine.exploration_rate < 0.2:
                mode = "Dialed In"
                color = self.accent_green
            elif session_ratings >= 5:
                mode = "Locked In"
                color = self.accent_purple
            else:
                mode = "Learning"
                color = "#fbbf24"

            self.adaptation_label.configure(text=mode, text_color=color)

            print(f"Stats updated - Total: {total_ratings}, Session: {session_ratings}")
        except Exception as e:
            import traceback
            print(f"Error updating stats: {e}")
            traceback.print_exc()

    def clear_history(self):
        import tkinter.messagebox as messagebox
        result = messagebox.askyesno(
            "Clear History",
            "This will delete all your ratings and reset the AI learning.\n\n"
            "Are you sure you want to continue?",
            icon="warning"
        )

        if result:
            self.engine.genre_scores.clear()
            self.engine.artist_scores.clear()
            self.engine.total_ratings = 0
            self.engine.session_ratings = 0
            self.engine.recent_ratings.clear()
            self.engine.global_feature_mean = np.array([0.5] * 9)
            self.engine.recent_feature_mean = np.array([0.5] * 9)
            self.engine.session_feature_mean = np.array([0.5] * 9)
            self.engine.exploration_rate = 0.4
            self.engine.consecutive_dislikes = 0

            import os
            import json
            data_dir = "data"
            if os.path.exists(os.path.join(data_dir, "ratings.json")):
                with open(os.path.join(data_dir, "ratings.json"), 'w') as f:
                    json.dump({}, f)
            if os.path.exists(os.path.join(data_dir, "model_state.json")):
                with open(os.path.join(data_dir, "model_state.json"), 'w') as f:
                    json.dump({}, f)

            self.rated_tracks.clear()
            self.counted_tracks.clear()
            self.committed_tracks.clear()
            self.session_played_tracks.clear()
            self.track_history.clear()
            self.track_history_index = -1
            self.current_rating = None

            self.update_stats()
            self.update_genre_leaderboard()

            messagebox.showinfo("History Cleared", "All rating history has been cleared.")