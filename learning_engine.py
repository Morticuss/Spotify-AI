import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from genre_taxonomy import GENRE_TAXONOMY

class LearningEngine:
    def __init__(self, storage, spotify_client):
        self.storage = storage
        self.spotify = spotify_client

        state = self.storage.load_model_state()

        loaded_genre_scores = state.get('genre_scores', {})
        self.genre_scores = defaultdict(lambda: {'alpha': 1.0, 'beta': 1.0, 'history': deque(maxlen=50)})
        for genre, scores in loaded_genre_scores.items():
            self.genre_scores[genre] = {
                'alpha': float(scores.get('alpha', 1.0)),
                'beta': float(scores.get('beta', 1.0)),
                'history': deque(scores.get('history', []), maxlen=50)
            }

        loaded_artist_scores = state.get('artist_scores', {})
        self.artist_scores = defaultdict(lambda: {'alpha': 1.0, 'beta': 1.0, 'history': deque(maxlen=50)})
        for artist, scores in loaded_artist_scores.items():
            self.artist_scores[artist] = {
                'alpha': float(scores.get('alpha', 1.0)),
                'beta': float(scores.get('beta', 1.0)),
                'history': deque(scores.get('history', []), maxlen=50)
            }

        self.feature_clusters = state.get('feature_clusters', [])
        self.recent_ratings = deque(maxlen=100)
        self.session_preferences = deque(maxlen=10)

        self.global_feature_mean = np.array(state.get('global_feature_mean', [0.5] * 9))
        self.recent_feature_mean = np.array(state.get('recent_feature_mean', [0.5] * 9))
        self.session_feature_mean = np.array([0.5] * 9)

        self.exploration_rate = state.get('exploration_rate', 0.4)
        self.total_ratings = state.get('total_ratings', 0)
        self.session_ratings = 0
        self.consecutive_dislikes = 0

        self.time_decay_factor = 0.95
        self.recent_weight = 0.7
        self.session_weight = 0.5

        self.last_rating_time = datetime.now()
        self.session_start_time = datetime.now()

    def get_feature_vector(self, track_features: Dict) -> np.ndarray:
        return np.array([
            track_features['danceability'],
            track_features['energy'],
            track_features['valence'],
            track_features['tempo'],
            track_features['acousticness'],
            track_features['instrumentalness'],
            track_features['speechiness'],
            track_features['liveness'],
            track_features['loudness']
        ])

    def detect_session_shift(self) -> bool:
        time_since_last_rating = (datetime.now() - self.last_rating_time).total_seconds()

        if time_since_last_rating > 2 * 3600:
            return True

        if self.consecutive_dislikes >= 5:
            return True

        if len(self.recent_ratings) >= 8:
            recent_likes = sum(1 for rating in list(self.recent_ratings)[-8:] if rating['rating'] > 0)
            if recent_likes == 0:
                return True

        return False

    def reset_session(self):
        self.session_feature_mean = np.array([0.5] * 9)
        self.session_ratings = 0
        self.consecutive_dislikes = 0
        self.session_start_time = datetime.now()
        self.exploration_rate = min(0.5, self.exploration_rate + 0.1)

    def apply_time_decay(self):
        time_elapsed = (datetime.now() - self.last_rating_time).total_seconds() / 3600
        decay = np.exp(-time_elapsed / 24)

        for genre in self.genre_scores:
            self.genre_scores[genre]['alpha'] *= (1 - (1 - decay) * 0.1)
            self.genre_scores[genre]['beta'] *= (1 - (1 - decay) * 0.1)
            self.genre_scores[genre]['alpha'] = max(1.0, self.genre_scores[genre]['alpha'])
            self.genre_scores[genre]['beta'] = max(1.0, self.genre_scores[genre]['beta'])

        for artist in self.artist_scores:
            self.artist_scores[artist]['alpha'] *= (1 - (1 - decay) * 0.1)
            self.artist_scores[artist]['beta'] *= (1 - (1 - decay) * 0.1)
            self.artist_scores[artist]['alpha'] = max(1.0, self.artist_scores[artist]['alpha'])
            self.artist_scores[artist]['beta'] = max(1.0, self.artist_scores[artist]['beta'])

    def get_recent_preference_weights(self) -> Tuple[float, float, float]:
        if self.session_ratings < 3:
            return 0.5, 0.4, 0.1

        if self.session_ratings >= 10:
            return 0.3, 0.3, 0.4

        return 0.4, 0.4, 0.2

    def thompson_sample_genre(self, genres: List[str]) -> float:
        if not genres:
            return 0.5

        primary_genre = self._get_primary_genre(genres)
        if not primary_genre:
            return 0.5

        score_data = self.genre_scores[primary_genre]
        alpha = score_data['alpha']
        beta = score_data['beta']

        mean_estimate = alpha / (alpha + beta)

        recent_bonus = 0
        if score_data['history']:
            recent_ratings = list(score_data['history'])[-10:]
            recent_avg = sum(recent_ratings) / len(recent_ratings)
            recent_bonus = recent_avg * 0.5

        total_samples = alpha + beta - 2
        confidence = min(1.0, total_samples / 20.0)

        sample = (confidence * mean_estimate + (1 - confidence) * 0.5) + recent_bonus

        if beta > alpha * 2.5:
            sample *= 0.4

        return min(1.0, max(0.0, sample))

    def thompson_sample_artist(self, artist_id: str) -> float:
        score_data = self.artist_scores[artist_id]
        alpha = score_data['alpha']
        beta = score_data['beta']

        mean_estimate = alpha / (alpha + beta)

        recent_bonus = 0
        if score_data['history']:
            recent_ratings = list(score_data['history'])[-10:]
            recent_avg = sum(recent_ratings) / len(recent_ratings)
            recent_bonus = recent_avg * 0.4

        total_samples = alpha + beta - 2
        confidence = min(1.0, total_samples / 15.0)

        sample = (confidence * mean_estimate + (1 - confidence) * 0.5) + recent_bonus

        if beta > alpha * 2:
            sample *= 0.5

        return min(1.0, max(0.0, sample))

    def calculate_track_score(self, track_features: Dict) -> float:
        try:
            if not track_features:
                return 0.5

            feature_vector = self.get_feature_vector(track_features)

            is_fallback = bool(track_features.get('fallback'))

            if not is_fallback:
                try:
                    global_weight, recent_weight, session_weight = self.get_recent_preference_weights()

                    global_distance = np.linalg.norm(feature_vector - self.global_feature_mean)
                    global_score = np.exp(-global_distance * 2)

                    recent_distance = np.linalg.norm(feature_vector - self.recent_feature_mean)
                    recent_score = np.exp(-recent_distance * 2)

                    session_distance = np.linalg.norm(feature_vector - self.session_feature_mean)
                    session_score = np.exp(-session_distance * 2)

                    feature_score = (global_weight * global_score +
                                    recent_weight * recent_score +
                                    session_weight * session_score)
                except Exception as feat_err:
                    print(f"Error calculating feature score: {feat_err}")
                    feature_score = 0.5
            else:
                feature_score = 0.5

            genre_score = self.thompson_sample_genre(track_features.get('genres', []))
            artist_score = self.thompson_sample_artist(track_features['artist_id']) if track_features.get('artist_id') else 0.5

            diversity_bonus = 0
            artist_penalty = 0
            genre_diversity_bonus = 0

            if len(self.recent_ratings) >= 5:
                recent_track_ids = [r['track_id'] for r in list(self.recent_ratings)[-5:]]
                if track_features['id'] not in recent_track_ids:
                    diversity_bonus = 0.1

                if track_features.get('artist_id'):
                    recent_10_artist_count = sum(1 for r in list(self.recent_ratings)[-10:]
                                                 if r.get('artist_id') == track_features['artist_id'])
                    recent_5_artist_count = sum(1 for r in list(self.recent_ratings)[-5:]
                                                if r.get('artist_id') == track_features['artist_id'])

                    if recent_5_artist_count > 0:
                        artist_penalty = 0.5 * (recent_5_artist_count / 5.0)
                    elif recent_10_artist_count > 1:
                        artist_penalty = 0.3 * (recent_10_artist_count / 10.0)

                current_genre = self._get_primary_genre(track_features.get('genres', []))
                if current_genre:
                    recent_genres = [r.get('primary_genre') for r in list(self.recent_ratings)[-5:]
                                   if r.get('primary_genre')]
                    if current_genre not in recent_genres and len(recent_genres) >= 2:
                        genre_diversity_bonus = 0.15

            exploration_bonus = random.random() * self.exploration_rate

            mood_consistency_bonus = 0
            if not is_fallback and self.session_ratings >= 3:
                session_distance = np.linalg.norm(feature_vector - self.session_feature_mean)
                session_score = np.exp(-session_distance * 2)
                mood_consistency_bonus = session_score * 0.15

            jitter = random.uniform(-0.01, 0.01)

            if is_fallback:
                final_score = (0.10 * feature_score +
                              0.45 * genre_score +
                              0.10 * artist_score +
                              0.12 * exploration_bonus +
                              0.12 * diversity_bonus +
                              0.11 * genre_diversity_bonus +
                              jitter) - artist_penalty
            else:
                final_score = (0.28 * feature_score +
                              0.35 * genre_score +
                              0.08 * artist_score +
                              0.08 * exploration_bonus +
                              0.10 * diversity_bonus +
                              0.07 * genre_diversity_bonus +
                              0.04 * mood_consistency_bonus +
                              jitter) - artist_penalty

            return final_score

        except Exception as e:
            print(f"Error in calculate_track_score: {e}")
            return 0.5

    def update_with_rating(self, track_id: str, rating: int, is_undo: bool = False, should_count: bool = True):
        if self.detect_session_shift():
            self.reset_session()

        track_features = self.spotify.get_track_features(track_id)
        if not track_features:
            print(f"WARNING: Could not get track features for {track_id}")
            return

        if not track_features.get('genres') and track_features.get('artist_id'):
            try:
                genres = self.spotify.fetch_genres_for_artist(track_features['artist_id'])
                if genres:
                    track_features['genres'] = genres
                    self.spotify._feature_cache[track_id] = track_features
                    print(f"Fetched {len(genres)} genres from artist cache: {genres[:3]}")
            except Exception as e:
                print(f"Could not fetch genres for artist: {e}")

        if not track_features.get('genres'):
            fallback_genre = self._infer_genre_from_features(track_features)
            if fallback_genre:
                track_features['genres'] = [fallback_genre]
                print(f"Using inferred genre: {fallback_genre}")

        primary_genre = self._get_primary_genre(track_features.get('genres', []))

        print(f"Updating with rating {rating} for track {track_id}")
        print(f"Track genres: {track_features.get('genres', [])}")
        print(f"Primary genre: {primary_genre}")

        feature_vector = self.get_feature_vector(track_features)
        reward = 1.0 if rating > 0 else 0.0

        strength_multiplier = -1.0 if is_undo else 1.0

        rating_data = {
            'track_id': track_id,
            'rating': rating,
            'features': feature_vector.tolist(),
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_start_time.isoformat(),
            'primary_genre': primary_genre,
            'artist_id': track_features.get('artist_id')
        }

        self.recent_ratings = deque([r for r in self.recent_ratings if r['track_id'] != track_id], maxlen=100)
        if not is_undo:
            self.recent_ratings.append(rating_data)

        global_learning_rate = 0.05
        recent_learning_rate = 0.15
        session_learning_rate = 0.3

        if rating > 0:
            error = feature_vector - self.global_feature_mean
            self.global_feature_mean += global_learning_rate * error

            error = feature_vector - self.recent_feature_mean
            self.recent_feature_mean += recent_learning_rate * error

            if self.session_ratings > 0:
                error = feature_vector - self.session_feature_mean
                self.session_feature_mean += session_learning_rate * error
            else:
                self.session_feature_mean = feature_vector

            self.consecutive_dislikes = 0
        else:
            anti_error = self.global_feature_mean - feature_vector
            self.global_feature_mean += global_learning_rate * 0.3 * anti_error

            anti_error = self.recent_feature_mean - feature_vector
            self.recent_feature_mean += recent_learning_rate * 0.5 * anti_error

            self.consecutive_dislikes += 1

        base_strength = 3.0 if reward > 0 else 1.5
        strength = base_strength * strength_multiplier
        artist_strength = strength * 0.3

        if primary_genre:
            if rating > 0:
                self.genre_scores[primary_genre]['alpha'] += strength
                if not is_undo:
                    self.genre_scores[primary_genre]['history'].append(1.0)
                elif self.genre_scores[primary_genre]['history']:
                    self.genre_scores[primary_genre]['history'].pop()
            else:
                self.genre_scores[primary_genre]['beta'] += strength
                if not is_undo:
                    self.genre_scores[primary_genre]['history'].append(0.0)
                elif self.genre_scores[primary_genre]['history']:
                    self.genre_scores[primary_genre]['history'].pop()

        if track_features.get('artist_id'):
            artist_id = track_features['artist_id']
            if rating > 0:
                self.artist_scores[artist_id]['alpha'] += artist_strength
                if not is_undo:
                    self.artist_scores[artist_id]['history'].append(1.0)
                elif self.artist_scores[artist_id]['history']:
                    self.artist_scores[artist_id]['history'].pop()
            else:
                self.artist_scores[artist_id]['beta'] += artist_strength
                if not is_undo:
                    self.artist_scores[artist_id]['history'].append(0.0)
                elif self.artist_scores[artist_id]['history']:
                    self.artist_scores[artist_id]['history'].pop()

        if is_undo:
            if should_count:
                self.total_ratings = max(0, self.total_ratings - 1)
                self.session_ratings = max(0, self.session_ratings - 1)
        elif should_count:
            self.total_ratings += 1
            self.session_ratings += 1

        base_exploration = 0.15
        if self.consecutive_dislikes >= 2:
            self.exploration_rate = min(0.7, self.exploration_rate + 0.15)
        elif rating > 0:
            self.exploration_rate = max(base_exploration, self.exploration_rate * 0.95)
        else:
            self.exploration_rate = max(base_exploration, self.exploration_rate * 0.98)

        self.last_rating_time = datetime.now()

        self.apply_time_decay()

        self.storage.save_rating(track_id, rating, rating_data)
        self.save_state()

    def _infer_genre_from_features(self, track_features: Dict) -> Optional[str]:
        try:
            if track_features.get('fallback'):
                return None

            energy = track_features.get('energy', 0.5)
            danceability = track_features.get('danceability', 0.5)
            valence = track_features.get('valence', 0.5)
            acousticness = track_features.get('acousticness', 0.5)
            instrumentalness = track_features.get('instrumentalness', 0.5)
            speechiness = track_features.get('speechiness', 0.5)

            if speechiness > 0.33:
                return 'hip hop'
            elif energy > 0.8 and danceability > 0.7:
                return 'electronic dance'
            elif energy > 0.7 and acousticness < 0.3 and instrumentalness < 0.3:
                return 'rock'
            elif danceability > 0.7 and energy > 0.6 and valence > 0.6:
                return 'pop'
            elif acousticness > 0.6:
                return 'folk'
            elif instrumentalness > 0.5:
                if energy > 0.5:
                    return 'electronic dance'
                else:
                    return 'ambient'
            elif energy < 0.4 and valence < 0.4:
                return 'downtempo'
            elif energy > 0.6:
                return 'pop'
            else:
                return 'indie rock'

        except Exception as e:
            print(f"Error inferring genre from features: {e}")
            return None

    def _get_primary_genre(self, genres: List[str]) -> Optional[str]:
        if not genres:
            return None

        for genre in genres:
            if GENRE_TAXONOMY.is_cultural_variant(genre):
                return genre

        for genre in genres:
            parent = GENRE_TAXONOMY.get_parent_genre(genre)
            if parent:
                return genre

        return genres[0] if genres else None

    def get_recommended_track(self, session_played_tracks: set) -> Optional[Dict]:
        try:
            liked_genres = self._get_liked_genres()

            genre_search_probability = 0.5

            if len(self.recent_ratings) >= 5:
                recent_likes = sum(1 for r in list(self.recent_ratings)[-5:] if r['rating'] > 0)
                like_rate = recent_likes / 5.0

                if like_rate >= 0.8:
                    genre_search_probability = 0.85
                elif like_rate >= 0.6:
                    genre_search_probability = 0.70
                elif like_rate <= 0.2:
                    genre_search_probability = 0.30

            if liked_genres and random.random() < genre_search_probability:
                try:
                    candidates = self._search_by_liked_genres(liked_genres, session_played_tracks)
                    if candidates:
                        result = self._select_best_candidate(candidates, session_played_tracks)
                        if result:
                            return result
                except Exception as genre_err:
                    print(f"Error in genre-based search: {genre_err}")

            try:
                candidates = self.spotify.search_batch_random_tracks(12)
            except Exception as search_err:
                print(f"Error in batch search: {search_err}")
                candidates = []

            if not candidates:
                print("No candidates found from random search")
                return None

            candidates = [t for t in candidates if t.get('id') and t['id'] not in session_played_tracks]

            if len(self.recent_ratings) >= 10:
                recent_track_ids = set([r['track_id'] for r in list(self.recent_ratings)[-10:]])
                candidates = [t for t in candidates if t['id'] not in recent_track_ids]

            if not candidates:
                print("All candidates filtered out")
                return None

            return self._select_best_candidate(candidates, session_played_tracks)

        except Exception as e:
            import traceback
            print(f"Error in get_recommended_track: {e}")
            traceback.print_exc()
            return None

    def _get_liked_genres(self) -> List[str]:
        liked = []
        for genre, scores in self.genre_scores.items():
            alpha = scores['alpha']
            beta = scores['beta']
            history = scores.get('history', [])

            if len(history) >= 3:
                recent_avg = sum(list(history)[-5:]) / min(5, len(history))
                overall_ratio = alpha / (beta + 1)

                if overall_ratio > 1.3 and alpha > 2.5:
                    confidence_score = overall_ratio * (1 + recent_avg)
                    liked.append((genre, confidence_score))

        liked.sort(key=lambda x: x[1], reverse=True)
        return [g[0] for g in liked[:6]]

    def _search_by_liked_genres(self, genres: List[str], session_played_tracks: set) -> List[Dict]:
        all_candidates = []
        seen_track_ids = set()

        for genre in genres[:4]:
            try:
                parent = GENRE_TAXONOMY.get_parent_genre(genre)
                search_genre = parent if parent else genre

                if len(all_candidates) < 10:
                    results = self.spotify.client.search(q=f"genre:{search_genre}", type='track', limit=20)
                else:
                    year = random.choice(['2024', '2023', '2022', '2021', '2020', '2019'])
                    results = self.spotify.client.search(
                        q=f"genre:{search_genre} year:{year}",
                        type='track',
                        limit=15
                    )

                if not results or 'tracks' not in results:
                    continue

                tracks = results['tracks']['items']

                for track in tracks:
                    track_id = track.get('id')
                    if not track_id or track_id in session_played_tracks or track_id in seen_track_ids:
                        continue

                    seen_track_ids.add(track_id)
                    track_data = {
                        'id': track_id,
                        'name': track.get('name', 'Unknown'),
                        'artist': ', '.join([artist.get('name', 'Unknown') for artist in track.get('artists', [])]),
                        'album_cover': track['album']['images'][0]['url'] if track.get('album') and track['album'].get('images') else None,
                        'uri': track.get('uri', '')
                    }
                    all_candidates.append(track_data)

                    if len(all_candidates) >= 20:
                        return all_candidates

            except Exception as e:
                print(f"Error searching genre {genre}: {e}")
                continue

        return all_candidates

    def _select_best_candidate(self, candidates: List[Dict], session_played_tracks: set) -> Optional[Dict]:
        track_ids = [track['id'] for track in candidates]
        features_dict = self.spotify.get_batch_track_features(track_ids)

        scored_tracks = []
        for track in candidates:
            if track['id'] in session_played_tracks:
                continue

            features = features_dict.get(track['id'])
            if features:
                primary_genre = self._get_primary_genre(features.get('genres', []))
                if primary_genre:
                    features['genres'] = [primary_genre]

                score = self.calculate_track_score(features)
                scored_tracks.append((track, score))

        if not scored_tracks:
            return candidates[0] if candidates else None

        scored_tracks.sort(key=lambda x: x[1], reverse=True)

        if self.consecutive_dislikes >= 2:
            exploration_pool_size = max(1, int(len(scored_tracks) * 0.6))
            exploration_pool = scored_tracks[:exploration_pool_size]
            return random.choice(exploration_pool)[0]
        else:
            top_pool = scored_tracks[:min(5, len(scored_tracks))]
            return random.choice(top_pool)[0]

    def generate_playlist_tracks(self, session_played_tracks: set, count: int = 25) -> List[Dict]:
        all_candidates = []
        seen_ids = set(session_played_tracks)

        liked_genres = self._get_liked_genres()
        use_session = self.session_ratings >= 5

        if liked_genres:
            for genre in liked_genres[:6]:
                try:
                    parent = GENRE_TAXONOMY.get_parent_genre(genre)
                    search_genre = parent if parent else genre

                    for year_query in [f"genre:{search_genre}", f"genre:{search_genre} year:2024", f"genre:{search_genre} year:2023"]:
                        results = self.spotify.client.search(q=year_query, type='track', limit=50)
                        if not results or 'tracks' not in results:
                            continue
                        for track in results['tracks']['items']:
                            track_id = track.get('id')
                            if not track_id or track_id in seen_ids:
                                continue
                            seen_ids.add(track_id)
                            all_candidates.append({
                                'id': track_id,
                                'name': track.get('name', 'Unknown'),
                                'artist': ', '.join([a.get('name', 'Unknown') for a in track.get('artists', [])]),
                                'album_cover': track['album']['images'][0]['url'] if track.get('album') and track['album'].get('images') else None,
                                'uri': track.get('uri', '')
                            })
                except Exception as e:
                    print(f"Error searching genre {genre} for playlist: {e}")
                    continue

        if len(all_candidates) < 50:
            try:
                random_tracks = self.spotify.search_batch_random_tracks(30)
                for track in random_tracks:
                    if track['id'] not in seen_ids:
                        seen_ids.add(track['id'])
                        all_candidates.append(track)
            except Exception as e:
                print(f"Error fetching random tracks for playlist: {e}")

        if not all_candidates:
            return []

        track_ids = [t['id'] for t in all_candidates]
        features_dict = self.spotify.get_batch_track_features(track_ids)

        scored_tracks = []
        for track in all_candidates:
            features = features_dict.get(track['id'])
            if not features:
                continue

            primary_genre = self._get_primary_genre(features.get('genres', []))
            if primary_genre:
                features['genres'] = [primary_genre]

            score = self.calculate_track_score(features)

            if use_session and not features.get('fallback'):
                try:
                    feature_vector = self.get_feature_vector(features)
                    session_distance = np.linalg.norm(feature_vector - self.session_feature_mean)
                    session_bonus = np.exp(-session_distance * 2) * 0.2
                    score += session_bonus
                except Exception:
                    pass

            scored_tracks.append((track, score))

        scored_tracks.sort(key=lambda x: x[1], reverse=True)

        selected = []
        selected_artists = set()
        for track, score in scored_tracks:
            artist = track.get('artist', '')
            if artist in selected_artists and len(selected) >= 5:
                continue
            selected.append(track)
            selected_artists.add(artist)
            if len(selected) >= count:
                break

        return selected

    def get_top_rated_tracks(self, limit: int = 50) -> List[Tuple[str, int]]:
        ratings = self.storage.load_ratings()
        sorted_tracks = sorted(
            [(track_id, data['rating']) for track_id, data in ratings.items() if data['rating'] > 0],
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_tracks[:limit]

    def get_session_stats(self) -> Dict:
        return {
            "total_ratings": self.total_ratings,
            "session_ratings": self.session_ratings,
            "exploration_rate": self.exploration_rate,
            "consecutive_dislikes": self.consecutive_dislikes,
        }

    def save_state(self):
        state = {
            'genre_scores': {k: {'alpha': v['alpha'], 'beta': v['beta'], 'history': list(v['history'])}
                           for k, v in self.genre_scores.items()},
            'artist_scores': {k: {'alpha': v['alpha'], 'beta': v['beta'], 'history': list(v['history'])}
                            for k, v in self.artist_scores.items()},
            'global_feature_mean': self.global_feature_mean.tolist(),
            'recent_feature_mean': self.recent_feature_mean.tolist(),
            'exploration_rate': self.exploration_rate,
            'total_ratings': self.total_ratings,
            'feature_clusters': self.feature_clusters
        }
        self.storage.save_model_state(state)

    def get_aggregated_genre_scores(self) -> Dict[str, Dict]:
        aggregated = defaultdict(lambda: {
            'alpha': 0.0,
            'beta': 0.0,
            'history': [],
            'subgenres': [],
            'total_interactions': 0
        })

        for genre, scores in self.genre_scores.items():
            parent = GENRE_TAXONOMY.get_parent_genre(genre)
            is_cultural = GENRE_TAXONOMY.is_cultural_variant(genre)

            if parent:
                display_genre = parent
            elif is_cultural:
                display_genre = genre.title()
            else:
                display_genre = genre.title()

            if display_genre not in aggregated:
                aggregated[display_genre] = {
                    'alpha': 0.0,
                    'beta': 0.0,
                    'history': [],
                    'subgenres': [],
                    'total_interactions': 0
                }

            aggregated[display_genre]['alpha'] += scores['alpha']
            aggregated[display_genre]['beta'] += scores['beta']
            aggregated[display_genre]['history'].extend(scores.get('history', []))
            aggregated[display_genre]['subgenres'].append(genre)
            aggregated[display_genre]['total_interactions'] += len(scores.get('history', []))

        return dict(aggregated)