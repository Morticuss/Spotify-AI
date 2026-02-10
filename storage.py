import json
import os
import threading
from typing import Dict, Any
from datetime import datetime


class Storage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.ratings_file = os.path.join(data_dir, "ratings.json")
        self.model_state_file = os.path.join(data_dir, "model_state.json")
        self.track_cache_file = os.path.join(data_dir, "track_cache.json")
        self.session_history_file = os.path.join(data_dir, "session_history.json")

        self._ratings_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._session_lock = threading.Lock()

    def _safe_read_json(self, filepath: str, default=None):
        if default is None:
            default = {}
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, 'r') as file:
                content = file.read().strip()
                if not content:
                    return default
                return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Corrupt JSON in {filepath}, backing up and resetting: {e}")
            backup_path = filepath + f".corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                os.rename(filepath, backup_path)
                print(f"Backup saved to {backup_path}")
            except Exception:
                pass
            return default
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return default

    def _safe_write_json(self, filepath: str, data):
        temp_path = filepath + ".tmp"
        try:
            with open(temp_path, 'w') as file:
                json.dump(data, file, indent=2)
            os.replace(temp_path, filepath)
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            try:
                os.remove(temp_path)
            except Exception:
                pass

    def load_ratings(self) -> Dict[str, Dict]:
        with self._ratings_lock:
            return self._safe_read_json(self.ratings_file, {})

    def save_rating(self, track_id: str, rating: int, rating_data: Dict):
        with self._ratings_lock:
            ratings = self._safe_read_json(self.ratings_file, {})
            ratings[track_id] = {
                'rating': rating,
                'timestamp': rating_data.get('timestamp', datetime.now().isoformat()),
                'features': rating_data.get('features', []),
                'session_id': rating_data.get('session_id', '')
            }
            self._safe_write_json(self.ratings_file, ratings)

    def load_model_state(self) -> Dict[str, Any]:
        with self._model_lock:
            return self._safe_read_json(self.model_state_file, {})

    def save_model_state(self, state: Dict[str, Any]):
        with self._model_lock:
            self._safe_write_json(self.model_state_file, state)

    def cache_track(self, track_id: str, track_data: Dict):
        with self._cache_lock:
            cache = self._safe_read_json(self.track_cache_file, {})
            cache[track_id] = track_data
            self._safe_write_json(self.track_cache_file, cache)

    def load_track_cache(self) -> Dict[str, Dict]:
        with self._cache_lock:
            return self._safe_read_json(self.track_cache_file, {})

    def save_session(self, session_data: Dict):
        with self._session_lock:
            sessions = self._safe_read_json(self.session_history_file, [])
            sessions.append(session_data)
            self._safe_write_json(self.session_history_file, sessions)

    def load_sessions(self) -> list:
        with self._session_lock:
            return self._safe_read_json(self.session_history_file, [])