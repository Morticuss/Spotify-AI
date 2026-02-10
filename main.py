import customtkinter as ctk
from gui import MusicLearnerGUI
from spotify_client import SpotifyClient
from learning_engine import LearningEngine
from storage import Storage

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    storage = Storage()
    spotify = SpotifyClient()
    engine = LearningEngine(storage, spotify)
    
    app = MusicLearnerGUI(spotify, engine, storage)
    app.mainloop()

if __name__ == "__main__":
    main()
