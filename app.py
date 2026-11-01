import streamlit as st
import pickle
import pandas as pd
import requests
from db import init_db, register_user, login_user, save_survey, get_survey
from datetime import datetime
import html as html_lib

import os

# 1. Page Configuration
st.set_page_config(page_title="Cinematic Hub", layout="wide")

# Initialize SQLite DB
try:
    init_db()
except Exception as _db_err:
    st.error(f"⚠️ Database connection error: {_db_err}\n\nPlease make sure MySQL is running and credentials in `.streamlit/secrets.toml` are correct.")
    st.stop()

# 2. Function to Load External CSS
def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Inject your custom CSS
load_css("accet/style.css")

# --- GENRE MAPPING ---
GENRE_TAG_MAP = {
    "Action": ["action"],
    "Adventure": ["adventure"],
    "Animation": ["animation"],
    "Comedy": ["comedy"],
    "Crime": ["crime"],
    "Documentary": ["documentary"],
    "Drama": ["drama"],
    "Family": ["family"],
    "Fantasy": ["fantasy"],
    "History": ["history"],
    "Horror": ["horror"],
    "Musical": ["musical", "music"],
    "Mystery": ["mystery"],
    "Romance": ["romance"],
    "Sci-Fi": ["sci-fi", "sciencefiction"],
    "Thriller": ["thriller"],
    "War": ["war"],
    "Western": ["western"],
}

BOLLYWOOD_GENRE_MAP = {
    "Action": ["Action"],
    "Adventure": ["Adventure"],
    "Animation": ["Animation"],
    "Comedy": ["Comedy"],
    "Crime": ["Crime"],
    "Documentary": ["Documentary"],
    "Drama": ["Drama"],
    "Family": ["Family"],
    "Fantasy": ["Fantasy"],
    "History": ["History"],
    "Horror": ["Horror"],
    "Musical": ["Musical", "Music"],
    "Mystery": ["Mystery"],
    "Romance": ["Romance"],
    "Sci-Fi": ["Sci-Fi"],
    "Thriller": ["Thriller"],
    "War": ["War"],
    "Western": ["Western"],
}

GENRE_EMOJI = {
    "Action": "💥", "Adventure": "🗺️", "Animation": "🎨", "Comedy": "😂",
    "Crime": "🔍", "Documentary": "📚", "Drama": "🎭", "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🧙", "History": "📜", "Horror": "👻", "Musical": "🎵",
    "Mystery": "🔎", "Romance": "❤️", "Sci-Fi": "🚀", "Thriller": "😱",
    "War": "⚔️", "Western": "🤠",
}

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_movie_details(title):
    try:
        api_key = st.secrets["OMDB_API_KEY"]
        url = f"http://www.omdbapi.com/?t={title}&apikey={api_key}"
        response = requests.get(url, timeout=10).json()
        poster = response.get('Poster', "")
        if not poster or poster == "N/A":
            poster = "https://via.placeholder.com/500x750/1a1a2e/e50914?text=No+Poster"
        return {
            "poster": poster,
            "year": response.get('Year', "N/A") if response.get('Year') and response.get('Year') != "N/A" else "N/A",
            "rating": response.get('imdbRating', "N/A") if response.get('imdbRating') and response.get('imdbRating') != "N/A" else "N/A",
            "plot": response.get('Plot', "No synopsis available.") if response.get('Plot') and response.get('Plot') != "N/A" else "No synopsis available."
        }
    except Exception:
        return {"poster": "https://via.placeholder.com/500x750/1a1a2e/e50914?text=No+Poster", "year": "N/A", "rating": "N/A", "plot": "N/A"}

def get_movies_by_genre(movies_df, genre, count=10):
    """Filter movies by genre using tag mapping."""
    tags = GENRE_TAG_MAP.get(genre, [])
    if not tags:
        return pd.DataFrame()
    pattern = "|".join(tags)
    mask = movies_df['tags'].str.contains(pattern, case=False, na=False)
    return movies_df[mask].head(count)

def get_survey_recommendations(movies_df, survey_data):
    _, age, genres_str, actors_str, year_from, year_to, _ = survey_data
    filtered = movies_df.copy()
    filtered['release_date'] = pd.to_numeric(filtered['release_date'], errors='coerce')
    filtered = filtered[(filtered['release_date'] >= year_from) & (filtered['release_date'] <= year_to)]
    search_terms = genres_str.lower().split(",") + [a.strip().lower() for a in actors_str.split(",") if a.strip()]
    def score_row(tag_text):
        tag_text = str(tag_text).lower()
        return sum(1 for term in search_terms if term in tag_text)
    filtered['score'] = filtered['tags'].apply(score_row)
    recommended = filtered.sort_values(by='score', ascending=False)
    return recommended.head(5)

def get_top_rated_movies(movies_df, count=10):
    """Get top rated movies by fetching IMDB ratings."""
    sample = movies_df.head(30)
    rated = []
    for _, row in sample.iterrows():
        details = fetch_movie_details(row['title'])
        rating_val = details['rating']
        if rating_val != "N/A":
            try:
                rated.append((float(rating_val), row['title'], details))
            except (ValueError, TypeError):
                continue
    rated.sort(reverse=True, key=lambda x: x[0])
    return rated[:count]

def get_trending_movies(movies_df, count=10):
    """Get recent/trending movies."""
    movies_df = movies_df.copy()
    movies_df['release_date'] = pd.to_numeric(movies_df['release_date'], errors='coerce')
    recent = movies_df[movies_df['release_date'] >= 2010].sort_values('release_date', ascending=False)
    return recent.head(count)

def display_genre_row(genre, movies_df, count=10):
    """Display a Netflix-style horizontal row of movies for a specific genre."""
    genre_movies = get_movies_by_genre(movies_df, genre, count)
    
    if len(genre_movies) == 0:
        return
    
    emoji = GENRE_EMOJI.get(genre, "🎬")
    st.markdown(f'<div class="genre-title">{emoji} {genre}</div>', unsafe_allow_html=True)
    
    cols = st.columns(count)
    
    for idx, (_, row) in enumerate(genre_movies.iterrows()):
        if idx < len(cols):
            details = fetch_movie_details(row['title'])
            with cols[idx]:
                poster = details["poster"]
                rating = details["rating"]
                year = details["year"]
                title_escaped = html_lib.escape(row['title'])
                plot_escaped = html_lib.escape(details["plot"])
                
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-card-poster">
                        <img src="{poster}" alt="{title_escaped}">
                        <div class="movie-card-overlay">
                            <div class="movie-card-rating">⭐ {rating}</div>
                            <div class="movie-card-year">{year}</div>
                        </div>
                    </div>
                    <div class="movie-card-title">{title_escaped}</div>
                    <div class="movie-card-plot">{plot_escaped}</div>
                </div>
                """, unsafe_allow_html=True)

def display_top_rated_row(movies_df, count=10):
    """Display top rated movies row."""
    rated_movies = get_top_rated_movies(movies_df, count)
    
    if not rated_movies:
        return
    
    st.markdown('<div class="genre-title">🏆 Top Rated</div>', unsafe_allow_html=True)
    cols = st.columns(min(count, len(rated_movies)))
    
    for idx, (rating, title, details) in enumerate(rated_movies):
        if idx < len(cols):
            poster = details["poster"]
            year = details["year"]
            title_escaped = html_lib.escape(title)
            plot_escaped = html_lib.escape(details["plot"])
            with cols[idx]:
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-card-poster">
                        <img src="{poster}" alt="{title_escaped}">
                        <div class="movie-card-overlay">
                            <div class="movie-card-rating">⭐ {rating}</div>
                            <div class="movie-card-year">{year}</div>
                        </div>
                    </div>
                    <div class="movie-card-title">{title_escaped}</div>
                    <div class="movie-card-plot">{plot_escaped}</div>
                </div>
                """, unsafe_allow_html=True)

def display_trending_row(movies_df, count=10):
    """Display trending/recent movies row."""
    trending = get_trending_movies(movies_df, count)
    
    if len(trending) == 0:
        return
    
    st.markdown('<div class="genre-title">🔥 Trending Now</div>', unsafe_allow_html=True)
    cols = st.columns(count)
    
    for idx, (_, row) in enumerate(trending.iterrows()):
        if idx < len(cols):
            details = fetch_movie_details(row['title'])
            poster = details["poster"]
            rating = details["rating"]
            year = details["year"]
            title_escaped = html_lib.escape(row['title'])
            plot_escaped = html_lib.escape(details["plot"])
            with cols[idx]:
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-card-poster">
                        <img src="{poster}" alt="{title_escaped}">
                        <div class="movie-card-overlay">
                            <div class="movie-card-rating">⭐ {rating}</div>
                            <div class="movie-card-year">{year}</div>
                        </div>
                    </div>
                    <div class="movie-card-title">{title_escaped}</div>
                    <div class="movie-card-plot">{plot_escaped}</div>
                </div>
                """, unsafe_allow_html=True)

def display_hero_banner(movies_df):
    """Display a hero banner with a featured movie."""
    import random
    sample = movies_df.sample(1).iloc[0]
    details = fetch_movie_details(sample['title'])
    
    poster = details["poster"]
    rating = details["rating"]
    year = details["year"]
    plot = details["plot"]
    title = html_lib.escape(sample['title'])
    
    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-content">
            <div class="hero-badge">🎬 FEATURED</div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">
                <span class="hero-rating">⭐ IMDB {rating}</span>
                <span class="hero-year">📅 {year}</span>
            </div>
            <p class="hero-plot">{html_lib.escape(plot)}</p>
        </div>
        <div class="hero-poster">
            <img src="{poster}" alt="{title}">
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- BOLLYWOOD / HINDI MOVIE FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_bollywood_details(imdb_id, title=""):
    """Fetch Bollywood movie details from OMDB using IMDB ID."""
    try:
        api_key = st.secrets["OMDB_API_KEY"]
        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={api_key}"
        response = requests.get(url, timeout=10).json()
        poster = response.get('Poster', "")
        if not poster or poster == "N/A":
            poster = "https://via.placeholder.com/500x750/1a1a2e/e50914?text=No+Poster"
        return {
            "poster": poster,
            "year": response.get('Year', "N/A") if response.get('Year') and response.get('Year') != "N/A" else "N/A",
            "rating": response.get('imdbRating', "N/A") if response.get('imdbRating') and response.get('imdbRating') != "N/A" else "N/A",
            "plot": response.get('Plot', "No synopsis available.") if response.get('Plot') and response.get('Plot') != "N/A" else "No synopsis available."
        }
    except Exception:
        return {"poster": "https://via.placeholder.com/500x750/1a1a2e/e50914?text=No+Poster", "year": "N/A", "rating": "N/A", "plot": "N/A"}

def get_bollywood_by_genre(bollywood_df, genre, count=10, year_range=(1916, 2017)):
    """Filter Bollywood movies by genre and year range."""
    genres = BOLLYWOOD_GENRE_MAP.get(genre, [])
    if not genres:
        return pd.DataFrame()
    pattern = "|".join(genres)
    mask = bollywood_df['genre'].str.contains(pattern, case=False, na=False)
    filtered = bollywood_df[mask]
    filtered = filtered[(filtered['releaseYear'] >= year_range[0]) & (filtered['releaseYear'] <= year_range[1])]
    return filtered.head(count)

def display_bollywood_row(genre, bollywood_df, count=10, year_range=(1916, 2017)):
    """Display a Netflix-style horizontal row of Bollywood movies for a specific genre."""
    genre_movies = get_bollywood_by_genre(bollywood_df, genre, count, year_range)
    
    if len(genre_movies) == 0:
        return
    
    emoji = GENRE_EMOJI.get(genre, "🎬")
    st.markdown(f'<div class="genre-title">{emoji} Bollywood {genre}</div>', unsafe_allow_html=True)
    
    cols = st.columns(min(count, len(genre_movies)))
    
    for idx, (_, row) in enumerate(genre_movies.iterrows()):
        if idx < len(cols):
            imdb_id = row.get('imdbId', '')
            details = fetch_bollywood_details(imdb_id, row['title'])
            with cols[idx]:
                poster = details["poster"]
                rating = details["rating"]
                year = details["year"]
                title_escaped = html_lib.escape(row['title'])
                plot_escaped = html_lib.escape(details["plot"])
                
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-card-poster">
                        <img src="{poster}" alt="{title_escaped}">
                        <div class="movie-card-overlay">
                            <div class="movie-card-rating">⭐ {rating}</div>
                            <div class="movie-card-year">{year}</div>
                        </div>
                    </div>
                    <div class="movie-card-title">{title_escaped}</div>
                    <div class="movie-card-plot">{plot_escaped}</div>
                </div>
                """, unsafe_allow_html=True)

def display_bollywood_hero(bollywood_df, year_range=(1916, 2017)):
    """Display a hero banner featuring a Bollywood movie."""
    import random
    filtered = bollywood_df[(bollywood_df['releaseYear'] >= year_range[0]) & (bollywood_df['releaseYear'] <= year_range[1])]
    if len(filtered) == 0:
        return
    sample = filtered.sample(1).iloc[0]
    imdb_id = sample.get('imdbId', '')
    details = fetch_bollywood_details(imdb_id, sample['title'])
    
    poster = details["poster"]
    rating = details["rating"]
    year = details["year"]
    plot = details["plot"]
    title = html_lib.escape(sample['title'])
    
    st.markdown(f"""
    <div class="hero-banner" style="background: linear-gradient(135deg, rgba(255, 165, 0, 0.15), rgba(255, 107, 107, 0.08)); border-color: rgba(255, 165, 0, 0.3);">
        <div class="hero-content">
            <div class="hero-badge" style="background: linear-gradient(90deg, #FF9933, #FF6B6B);">🇮🇳 BOLLYWOOD FEATURED</div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">
                <span class="hero-rating">⭐ IMDB {rating}</span>
                <span class="hero-year">📅 {year}</span>
            </div>
            <p class="hero-plot">{html_lib.escape(plot)}</p>
        </div>
        <div class="hero-poster">
            <img src="{poster}" alt="{title}">
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- PHASE 3: SEARCH & SIMILARITY RECOMMENDATIONS ---
def extract_genres_from_tags(tag_text):
    """Extract genre keywords from TMDB tags string."""
    tag_text = str(tag_text).lower()
    genre_keywords = {
        "Action": ["action"], "Adventure": ["adventure"], "Animation": ["animation"],
        "Comedy": ["comedy"], "Crime": ["crime"], "Documentary": ["documentary"],
        "Drama": ["drama"], "Family": ["family"], "Fantasy": ["fantasy"],
        "History": ["history"], "Horror": ["horror"], "Musical": ["musical", "music"],
        "Mystery": ["mystery"], "Romance": ["romance"], "Sci-Fi": ["sci-fi", "sciencefiction"],
        "Thriller": ["thriller"], "War": ["war"], "Western": ["western"],
    }
    found = set()
    for genre, keywords in genre_keywords.items():
        for kw in keywords:
            if kw in tag_text:
                add = genre
                found.add(add)
                break
    return found

def get_era_bucket(year):
    """Classify a year into an era bucket."""
    if pd.isna(year):
        return None
    year = int(year)
    if year < 1990:
        return "pre_1990"
    elif year < 2010:
        return "1990_2010"
    else:
        return "2010_present"

def compute_similarity_score(source_movies, source_idx, target_movies, target_idx, source_type="hollywood"):
    """Compute similarity score between two movies based on the spec scoring rule.
    
    Scoring:
    - Shared genre: +3 per shared genre
    - Same director: +2
    - Shared cast: +2 per shared name
    - Same era bucket: +1
    - Same content type: +1
    """
    if source_type == "hollywood":
        source_row = source_movies.iloc[source_idx]
        target_row = target_movies.iloc[target_idx]
        source_genres = extract_genres_from_tags(source_row['tags'])
        target_genres = extract_genres_from_tags(target_row['tags'])
    else:
        source_row = source_movies.iloc[source_idx]
        target_row = target_movies.iloc[target_idx]
        source_genres = set(g.strip() for g in str(source_row.get('genre', '')).split('|') if g.strip())
        target_genres = set(g.strip() for g in str(target_row.get('genre', '')).split('|') if g.strip())

    score = 0

    # Shared genre: +3 per shared genre
    shared_genres = source_genres & target_genres
    score += len(shared_genres) * 3

    # Same director: +2
    if source_type == "hollywood":
        source_director = str(source_row.get('tags', '')).lower()
        target_director = str(target_row.get('tags', '')).lower()
    else:
        source_directors = str(source_row.get('directors', '')).lower()
        target_directors = str(target_row.get('directors', '')).lower()
        if source_directors == target_directors and source_directors != 'nan':
            score += 2

    # Shared cast: +2 per shared name
    if source_type == "hollywood":
        source_cast = set(str(source_row.get('tags', '')).lower().split())
        target_cast = set(str(target_row.get('tags', '')).lower().split())
    else:
        source_cast = set(a.strip().lower() for a in str(source_row.get('actors', '')).split('|') if a.strip())
        target_cast = set(a.strip().lower() for a in str(target_row.get('actors', '')).split('|') if a.strip())

    shared_cast = source_cast & target_cast
    score += len(shared_cast) * 2

    # Same era bucket: +1
    if source_type == "hollywood":
        source_year = pd.to_numeric(source_row.get('release_date'), errors='coerce')
        target_year = pd.to_numeric(target_row.get('release_date'), errors='coerce')
    else:
        source_year = pd.to_numeric(source_row.get('releaseYear'), errors='coerce')
        target_year = pd.to_numeric(target_row.get('releaseYear'), errors='coerce')

    if pd.notna(source_year) and pd.notna(target_year):
        if get_era_bucket(source_year) == get_era_bucket(target_year):
            score += 1

    return score

def get_similar_movies(source_title, movies_df, source_type="hollywood", top_n=10):
    """Get similar movies using the scoring rule from the spec."""
    if not source_title:
        return []
    if source_type == "hollywood":
        matches = movies_df[movies_df['title'] == source_title]
        if len(matches) == 0:
            matches = movies_df[movies_df['title'].str.contains(source_title, case=False, na=False, regex=False)]
        if len(matches) == 0:
            return []
        source_idx = matches.index[0]
    else:
        matches = movies_df[movies_df['title'] == source_title]
        if len(matches) == 0:
            matches = movies_df[movies_df['title'].str.contains(source_title, case=False, na=False, regex=False)]
        if len(matches) == 0:
            return []
        source_idx = matches.index[0]

    scores = []
    for idx, row in movies_df.iterrows():
        if idx == source_idx:
            continue
        score = compute_similarity_score(movies_df, source_idx, movies_df, idx, source_type)
        if score > 0:
            scores.append((score, row['title']))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_n]

# --- DATA LOADING ---
movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open('similarity.pkl', 'rb'))

# --- BOLLYWOOD DATA LOADING ---
bollywood_df = pd.read_csv('BollywoodMovieDetail.csv')
bollywood_df['releaseYear'] = pd.to_numeric(bollywood_df['releaseYear'], errors='coerce')

# --- SESSION STATE MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'year_filter' not in st.session_state:
    st.session_state['year_filter'] = (1916, 2017)
if 'search_selected' not in st.session_state:
    st.session_state['search_selected'] = None

# --- AUTHENTICATION UI (PHASE 1) ---
if not st.session_state['logged_in']:
    st.markdown("""
        <style>
        /* Animated gradient background for login page */
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
            padding: 20px;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 450px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            animation: fadeIn 0.8s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        .login-title {
            text-align: center;
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #e50914, #ff6b6b, #ffd700);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
            letter-spacing: 2px;
        }
        .login-subtitle {
            text-align: center;
            color: #b3b3b3;
            font-size: 0.95rem;
            margin-bottom: 30px;
        }
        .login-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(229, 9, 20, 0.5), transparent);
            margin: 25px 0;
        }
        .login-feature {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #cccccc;
            font-size: 0.9rem;
            margin: 8px 0;
            opacity: 0.8;
        }
        .login-feature span {
            color: #e50914;
            font-size: 1.2rem;
        }
        .floating-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
            z-index: -1;
        }
        .particle {
            position: absolute;
            width: 4px;
            height: 4px;
            background: rgba(229, 9, 20, 0.3);
            border-radius: 50%;
            animation: float 6s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.3; }
            50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
        }
        </style>
        
        <div class="floating-particles">
            <div class="particle" style="left:10%; top:20%; animation-delay:0s;"></div>
            <div class="particle" style="left:30%; top:60%; animation-delay:1s;"></div>
            <div class="particle" style="left:50%; top:30%; animation-delay:2s;"></div>
            <div class="particle" style="left:70%; top:70%; animation-delay:3s;"></div>
            <div class="particle" style="left:90%; top:40%; animation-delay:4s;"></div>
            <div class="particle" style="left:20%; top:80%; animation-delay:1.5s;"></div>
            <div class="particle" style="left:60%; top:10%; animation-delay:2.5s;"></div>
            <div class="particle" style="left:80%; top:50%; animation-delay:3.5s;"></div>
        </div>
        
        <div class="login-container">
            <div class="login-card">
                <div class="login-title">🎬 CINEMATCH</div>
                <div class="login-subtitle">Your Personalized Movie Universe Awaits</div>
                <div class="login-feature"><span>✨</span> AI-Powered Recommendations</div>
                <div class="login-feature"><span>🎯</span> Survey-Based Personalization</div>
                <div class="login-feature"><span>🍿</span> Browse by Genre & Era</div>
                <div class="login-feature"><span>🔍</span> Discover Hidden Gems</div>
                <div class="login-divider"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register & Survey"])

    with tab1:
        st.markdown('<div style="max-width:400px; margin:0 auto; padding:10px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color:#ffffff; margin-bottom:20px;">Welcome Back</h3>', unsafe_allow_html=True)
        login_user_input = st.text_input("👤 Username", key="login_user", placeholder="Enter your username")
        login_pass_input = st.text_input("🔒 Password", type="password", key="login_pass", placeholder="Enter your password")
        if st.button("Log In", key="login_btn", use_container_width=True):
            if login_user(login_user_input, login_pass_input):
                st.session_state['logged_in'] = True
                st.session_state['user'] = login_user_input
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div style="max-width:400px; margin:0 auto; padding:10px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color:#ffffff; margin-bottom:20px;">Create Account</h3>', unsafe_allow_html=True)
        reg_user = st.text_input("👤 Choose Username", key="reg_user", placeholder="Pick a unique username")
        reg_pass = st.text_input("🔒 Choose Password", type="password", key="reg_pass", placeholder="Create a strong password")
        
        st.markdown('<div class="login-divider"></div>', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#ffffff; margin:15px 0 10px 0;">🎯 Quick Survey</h4>', unsafe_allow_html=True)
        
        # 1. User Age
        user_age = st.number_input("1. Your Age", min_value=1, max_value=120, value=22)
        
        # 2. Favorite Genres
        available_genres = ["Action", "Comedy", "Drama", "Horror", "Romance", "Sci-Fi", "Thriller", "Musical", "Animation"]
        selected_genres = st.multiselect("2. Favorite Genres", available_genres, help="Select multiple genres you enjoy")
        
        # 3. Favorite Actor / Actress
        favorite_actors = st.text_input("3. Favorite Actor / Actress", placeholder="e.g. Leonardo DiCaprio, Tom Hanks")
        
        # 4. Specific Time Period Preference
        all_eras = st.checkbox("All Eras (no time filter)", value=False, key="all_eras")
        if not all_eras:
            year_range = st.slider(
                "4. Select Your Preferred Movie Era",
                min_value=1916, max_value=2017,
                value=(1990, 2010),
                help="Drag the sliders to set your preferred year range"
            )
            year_from, year_to = year_range
        else:
            year_from, year_to = 1916, 2017
        
        st.markdown(f'<div style="text-align:center; color:#e50914; font-weight:600; margin-top:-5px;">📅 Showing movies from {year_from} to {year_to}</div>', unsafe_allow_html=True)
        
        # 5. Suggestion Box
        suggestions = st.text_area("5. Suggestions (Optional)", placeholder="Any ideas to improve CineMatch?")

        if st.button("Register & Join CineMatch", key="reg_btn", use_container_width=True):
            if reg_user and reg_pass:
                if register_user(reg_user, reg_pass):
                    save_survey(reg_user, user_age, selected_genres, favorite_actors, year_from, year_to, suggestions)
                    st.success("Account created! You can now log in.")
                else:
                    st.error("Username already exists. Try another.")
            else:
                st.warning("Please enter both username and password.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN PLATFORM UI (AFTER LOGIN) ---
else:
    st.sidebar.write(f"Logged in as: **{st.session_state['user']}**")
    
    # Show selected time period indicator
    user_survey_sidebar = get_survey(st.session_state['user'])
    if user_survey_sidebar:
        _, _, _, _, yf, yt, _ = user_survey_sidebar
        if yf and yt:
            st.sidebar.markdown(f"📅 **Selected Era:** {yf} – {yt}")
        else:
            st.sidebar.markdown("📅 **Selected Era:** All Eras")
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.session_state['year_filter'] = (1916, 2017)
        st.rerun()

    # YEAR RANGE FILTER - Visible indicator on main page
    with st.expander("📅 Filter by Time Period", expanded=True):
        filter_col1, filter_col2 = st.columns([3, 1])
        with filter_col1:
            year_range = st.slider(
                "Select Movie Era",
                min_value=1916, max_value=2017,
                value=st.session_state.get('year_filter', (1916, 2017)),
                help="Filter all movies by release year"
            )
        with filter_col2:
            st.markdown('<div style="padding-top:25px;">', unsafe_allow_html=True)
            if st.button("Reset to All Eras", key="reset_eras", use_container_width=True):
                st.session_state['year_filter'] = (1916, 2017)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.session_state['year_filter'] = year_range
        st.markdown(f'<div style="text-align:center; color:#e50914; font-weight:600; margin-top:-10px;">🎬 Showing movies from {year_range[0]} to {year_range[1]}</div>', unsafe_allow_html=True)

    # Filter movies by selected year range
    movies['release_date'] = pd.to_numeric(movies['release_date'], errors='coerce')
    filtered_movies = movies[(movies['release_date'] >= year_range[0]) & (movies['release_date'] <= year_range[1])]
    st.sidebar.write(f"📅 **Filter:** {year_range[0]} – {year_range[1]}")
    st.sidebar.write(f"🎬 **Movies:** {len(filtered_movies)}")

    # --- SEARCH BAR (MOVED TO TOP) ---
    st.markdown('<div style="padding:20px 0; background: rgba(0,0,0,0.5); margin:-20px -20px 20px -20px; position:sticky; top:0; z-index:100; backdrop-filter:blur(10px);">', unsafe_allow_html=True)
    st.markdown('<div style="max-width:600px; margin:0 auto; padding:0 20px;">', unsafe_allow_html=True)
    
    st.markdown('<div style="color:#ffffff; font-size:1.2rem; font-weight:600; margin-bottom:10px; text-align:center;">🔍 Discover Your Next Favorite Movie</div>', unsafe_allow_html=True)
    
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        search_query = st.text_input("Search for movies...", value="", key="search_input_top", placeholder="e.g. Inception, Lagaan, The Dark Knight", help="Start typing to see autocomplete suggestions")
        # Autocomplete suggestions
        if search_query:
            query_lower = search_query.lower().strip()
            if query_lower:
                hollywood_suggestions = filtered_movies[filtered_movies['title'].str.startswith(query_lower, na=False)]
                bollywood_suggestions = bollywood_df[bollywood_df['title'].str.startswith(query_lower, na=False)]
                bollywood_suggestions = bollywood_suggestions[(bollywood_suggestions['releaseYear'] >= year_range[0]) & 
                                                              (bollywood_suggestions['releaseYear'] <= year_range[1])]
                
                all_suggestions = pd.concat([hollywood_suggestions, bollywood_suggestions], ignore_index=True)
                all_suggestions = all_suggestions.drop_duplicates(subset=['title'])
                
                if len(all_suggestions) > 0:
                    st.markdown(f'<div style="color:#b3b3b3; margin-top:5px; font-size:0.85rem;">💡 Suggestions: {", ".join(all_suggestions["title"].tolist()[:5])}{" ..." if len(all_suggestions) > 5 else ""}</div>', unsafe_allow_html=True)
    
    with search_col2:
        search_type = st.selectbox("Search in", ["Both", "Hollywood", "Bollywood"], key="search_type_top", label_visibility="collapsed")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # HERO BANNER
    display_hero_banner(filtered_movies)

    # SURVEY-BASED RECOMMENDATIONS
    user_survey = get_survey(st.session_state['user'])
    if user_survey:
        _, _, _, _, yf, yt, _ = user_survey
        era_label = f" ({yf}–{yt})" if yf and yt else " (All Eras)"
        st.markdown(f'<div class="genre-title">🌟 Personalized For You{era_label}</div>', unsafe_allow_html=True)
        survey_recs = get_survey_recommendations(filtered_movies, user_survey)
        
        rec_cols = st.columns(5)
        for idx, (_, row) in enumerate(survey_recs.iterrows()):
            details = fetch_movie_details(row['title'])
            with rec_cols[idx % 5]:
                poster = details["poster"]
                rating = details["rating"]
                year = details["year"]
                title_escaped = html_lib.escape(row['title'])
                plot_escaped = html_lib.escape(details["plot"])
                st.markdown(f"""
                <div class="movie-card">
                    <div class="movie-card-poster">
                        <img src="{poster}" alt="{title_escaped}">
                        <div class="movie-card-overlay">
                            <div class="movie-card-rating">⭐ {rating}</div>
                            <div class="movie-card-year">{year}</div>
                        </div>
                    </div>
                    <div class="movie-card-title">{title_escaped}</div>
                    <div class="movie-card-plot">{plot_escaped}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # PHASE 2: NETFLIX-STYLE GENRE ROWS
    display_trending_row(filtered_movies, count=10)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    display_top_rated_row(filtered_movies, count=10)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    genres_to_display = ["Action", "Horror", "Sci-Fi", "Comedy", "Romance", "Drama", "Thriller", "Animation", "Adventure", "Crime"]

    for genre in genres_to_display:
        display_genre_row(genre, filtered_movies, count=10)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # BOLLYWOOD / HINDI MOVIE SECTION
    st.markdown('<div class="genre-title">🇮🇳 Bollywood / Hindi Movies</div>', unsafe_allow_html=True)
    display_bollywood_hero(bollywood_df, year_range=year_range)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    bollywood_genres = ["Action", "Comedy", "Drama", "Romance", "Thriller", "Horror", "Musical", "Crime", "Adventure", "Family"]

    for genre in bollywood_genres:
        display_bollywood_row(genre, bollywood_df, count=10, year_range=year_range)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # PHASE 3: SEARCH & SIMILARITY RECOMMENDATIONS
    st.markdown('<div class="genre-title">🔍 Search Any Movie</div>', unsafe_allow_html=True)

    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        search_query = st.text_input("Type a movie title to search...", value="", key="search_input", placeholder="e.g. Inception, Lagaan, The Dark Knight")
        # Autocomplete suggestions
        if search_query:
            query_lower = search_query.lower().strip()
            if query_lower:
                # Get prefix suggestions for both datasets
                hollywood_suggestions = filtered_movies[filtered_movies['title'].str.startswith(query_lower, na=False)]
                bollywood_suggestions = bollywood_df[bollywood_df['title'].str.startswith(query_lower, na=False)]
                bollywood_suggestions = bollywood_suggestions[(bollywood_suggestions['releaseYear'] >= year_range[0]) & 
                                                              (bollywood_suggestions['releaseYear'] <= year_range[1])]
                
                all_suggestions = pd.concat([hollywood_suggestions, bollywood_suggestions], ignore_index=True)
                all_suggestions = all_suggestions.drop_duplicates(subset=['title'])
                
                if len(all_suggestions) > 0:
                    st.markdown(f'<div style="color:#b3b3b3; margin-bottom:5px; font-size:0.85rem;">💡 Type suggestions: {", ".join(all_suggestions["title"].tolist()[:5])}{" ..." if len(all_suggestions) > 5 else ""}</div>', unsafe_allow_html=True)
    
    with search_col2:
        search_type = st.selectbox("Search in", ["Both", "Hollywood", "Bollywood"], key="search_type")

    if search_query:
        query_lower = search_query.lower().strip()
        if search_type in ["Both", "Hollywood"]:
            hollywood_matches = filtered_movies[filtered_movies['title'].str.startswith(query_lower, na=False)]
        else:
            hollywood_matches = pd.DataFrame()

        if search_type in ["Both", "Bollywood"]:
            bollywood_matches = bollywood_df[bollywood_df['title'].str.startswith(query_lower, na=False)]
            bollywood_matches = bollywood_matches[(bollywood_matches['releaseYear'] >= year_range[0]) & 
                                                  (bollywood_matches['releaseYear'] <= year_range[1])]
        else:
            bollywood_matches = pd.DataFrame()

        if len(hollywood_matches) == 0 and len(bollywood_matches) == 0:
            st.markdown('<div style="color:#b3b3b3; text-align:center; padding:20px;">No movies found. Try a different search term.</div>', unsafe_allow_html=True)
        else:
            total = len(hollywood_matches) + len(bollywood_matches)
            st.markdown(f'<div style="color:#b3b3b3; margin-bottom:10px;">Found {total} result(s) for "{html_lib.escape(search_query)}"</div>', unsafe_allow_html=True)

            if len(hollywood_matches) > 0:
                st.markdown('<div style="color:#ffffff; font-weight:600; margin:15px 0 8px 0;">🎬 Hollywood</div>', unsafe_allow_html=True)
                match_cols = st.columns(min(5, len(hollywood_matches)))
                for idx, (_, row) in enumerate(hollywood_matches.head(10).iterrows()):
                    if idx < len(match_cols):
                        details = fetch_movie_details(row['title'])
                        with match_cols[idx]:
                            poster = details["poster"]
                            rating = details["rating"]
                            year = details["year"]
                            title_escaped = html_lib.escape(row['title'])
                            plot_escaped = html_lib.escape(details["plot"])
                            st.markdown(f"""
                            <div class="movie-card" onclick="document.getElementById('selected_movie_{idx}').click()">
                                <div class="movie-card-poster">
                                    <img src="{poster}" alt="{title_escaped}">
                                    <div class="movie-card-overlay">
                                        <div class="movie-card-rating">⭐ {rating}</div>
                                        <div class="movie-card-year">{year}</div>
                                    </div>
                                </div>
                                <div class="movie-card-title">{title_escaped}</div>
                                <div class="movie-card-plot">{plot_escaped}</div>
                                <button id="selected_movie_{idx}" style="display:none;" onclick="window.streamlitSetComponentValue('{row['title']}')"></button>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"View Recommendations", key=f"h_rec_{idx}", use_container_width=True):
                                st.session_state['search_selected'] = row['title']
                                st.session_state['search_selected_type'] = 'hollywood'
                                st.rerun()

            if len(bollywood_matches) > 0:
                st.markdown('<div style="color:#ffffff; font-weight:600; margin:15px 0 8px 0;">🇮🇳 Bollywood</div>', unsafe_allow_html=True)
                match_cols = st.columns(min(5, len(bollywood_matches)))
                for idx, (_, row) in enumerate(bollywood_matches.head(10).iterrows()):
                    if idx < len(match_cols):
                        imdb_id = row.get('imdbId', '')
                        details = fetch_bollywood_details(imdb_id, row['title'])
                        with match_cols[idx]:
                            poster = details["poster"]
                            rating = details["rating"]
                            year = details["year"]
                            title_escaped = html_lib.escape(row['title'])
                            plot_escaped = html_lib.escape(details["plot"])
                            st.markdown(f"""
                            <div class="movie-card">
                                <div class="movie-card-poster">
                                    <img src="{poster}" alt="{title_escaped}">
                                    <div class="movie-card-overlay">
                                        <div class="movie-card-rating">⭐ {rating}</div>
                                        <div class="movie-card-year">{year}</div>
                                    </div>
                                </div>
                                <div class="movie-card-title">{title_escaped}</div>
                                <div class="movie-card-plot">{plot_escaped}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"View Recommendations", key=f"b_rec_{idx}", use_container_width=True):
                                st.session_state['search_selected'] = row['title']
                                st.session_state['search_selected_type'] = 'bollywood'
                                st.rerun()

    if 'search_selected' in st.session_state:
        selected_title = st.session_state['search_selected']
        selected_type = st.session_state.get('search_selected_type', 'hollywood')

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        if selected_type == 'hollywood':
            source_movies = filtered_movies
            all_source_movies = movies
        else:
            source_movies = bollywood_df
            all_source_movies = bollywood_df

        similar = get_similar_movies(selected_title, source_movies, source_type=selected_type, top_n=10)

        if similar:
            st.markdown(f'<div class="genre-title">🎬 Because you searched "{html_lib.escape(selected_title)}"</div>', unsafe_allow_html=True)

            rec_cols = st.columns(min(5, len(similar)))
            for idx, (score, title) in enumerate(similar[:10]):
                if idx < len(rec_cols):
                    if selected_type == 'hollywood':
                        details = fetch_movie_details(title)
                    else:
                        imdb_row = bollywood_df[bollywood_df['title'] == title]
                        if len(imdb_row) > 0:
                            details = fetch_bollywood_details(imdb_row.iloc[0].get('imdbId', ''), title)
                        else:
                            details = fetch_bollywood_details('', title)
                    with rec_cols[idx]:
                        poster = details["poster"]
                        rating = details["rating"]
                        year = details["year"]
                        title_escaped = html_lib.escape(title)
                        plot_escaped = html_lib.escape(details["plot"])
                        st.markdown(f"""
                        <div class="movie-card">
                            <div class="movie-card-poster">
                                <img src="{poster}" alt="{title_escaped}">
                                <div class="movie-card-overlay">
                                    <div class="movie-card-rating">⭐ {rating}</div>
                                    <div class="movie-card-year">{year}</div>
                                </div>
                            </div>
                            <div class="movie-card-title">{title_escaped}</div>
                            <div class="movie-card-plot">{plot_escaped}</div>
                        </div>
                        """, unsafe_allow_html=True)

            if st.button("Clear Search", key="clear_search", use_container_width=True):
                del st.session_state['search_selected']
                st.session_state['search_input'] = ''
                st.rerun()
        else:
            st.markdown('<div style="color:#b3b3b3; text-align:center; padding:20px;">No similar movies found.</div>', unsafe_allow_html=True)