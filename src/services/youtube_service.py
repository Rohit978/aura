"""
YouTube Service
Searches for YouTube videos and gets video IDs for music playback
Uses YouTube Data API v3 for accurate video search
"""

import os
import requests
from typing import Optional, Dict, List
import re
import json
import logging

logger = logging.getLogger(__name__)

# Try to import Google API client
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    logger.warning("google-api-python-client not available. YouTube API features disabled.")


class YouTubeService:
    """Service for finding YouTube videos for songs using YouTube Data API v3"""
    
    def __init__(self):
        # Initialize YouTube API client
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.youtube_api = None
        
        if self.api_key and YOUTUBE_API_AVAILABLE:
            try:
                self.youtube_api = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube Data API v3 initialized successfully")
            except Exception as e:
                logger.error(f"Could not initialize YouTube API: {e}")
                self.youtube_api = None
        else:
            if not self.api_key:
                logger.warning("YOUTUBE_API_KEY not found in environment. YouTube API features disabled. Falling back to web scraping.")
            elif not YOUTUBE_API_AVAILABLE:
                logger.warning("google-api-python-client library not installed. YouTube API features disabled. Falling back to web scraping.")
            self.youtube_api = None
        
        # Fallback: HTTP session for scraping (if API not available)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _is_valid_video_id(self, video_id: str) -> bool:
        """Validate that a video ID looks correct"""
        if not video_id or len(video_id) != 11:
            return False
        # YouTube video IDs are alphanumeric with hyphens and underscores
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return False
        # Filter out common invalid patterns
        invalid_patterns = ['AAAAAAAAAAA', 'undefined', 'null', 'true', 'false']
        if video_id in invalid_patterns:
            return False
        return True
    
    def _extract_video_ids_from_json(self, text: str) -> List[str]:
        """Extract video IDs from YouTube's initial data JSON"""
        video_ids = []
        try:
            # Find ytInitialData JSON object
            match = re.search(r'var ytInitialData = ({.+?});', text)
            if match:
                data = json.loads(match.group(1))
                # Navigate through the JSON structure to find video IDs
                contents = data.get('contents', {})
                two_column_search = contents.get('twoColumnSearchResultsRenderer', {})
                primary_contents = two_column_search.get('primaryContents', {})
                section_list = primary_contents.get('sectionListRenderer', {})
                contents_list = section_list.get('contents', [])
                
                for content in contents_list:
                    item_section = content.get('itemSectionRenderer', {})
                    items = item_section.get('contents', [])
                    for item in items:
                        video_renderer = item.get('videoRenderer', {})
                        if video_renderer:
                            video_id = video_renderer.get('videoId')
                            if video_id and self._is_valid_video_id(video_id):
                                video_ids.append(video_id)
        except Exception as e:
            logger.debug(f"Error extracting from JSON: {e}")
        
        return video_ids
    
    def search_video_id(self, song_title: str, artists: list) -> Optional[str]:
        """
        Search for YouTube video ID for a song using YouTube Data API v3.
        Falls back to web scraping if API is not available.
        
        Args:
            song_title: Song title
            artists: List of artist names
            
        Returns:
            YouTube video ID or None
        """
        # Use YouTube Data API v3 if available
        if self.youtube_api:
            return self._search_with_api(song_title, artists)
        
        # Fallback to web scraping
        logger.warning("YouTube API not available, falling back to web scraping")
        return self._search_with_scraping(song_title, artists)
    
    def _search_with_api(self, song_title: str, artists: list) -> Optional[str]:
        """
        Search for video using YouTube Data API v3.
        This is the preferred method as it's more accurate and reliable.
        """
        try:
            artist_str = " ".join(artists[:2]) if artists else ""
            
            # Build optimized search queries
            queries = [
                f"{song_title} {artist_str} official audio",  # Most accurate for music
                f"{song_title} {artist_str} official",  # Fallback to official
                f"{song_title} {artist_str}",  # Just title and artist
                f"{song_title} {artist_str} music"  # General music search
            ]
            
            for search_query in queries:
                try:
                    # Call YouTube Data API v3 search
                    request = self.youtube_api.search().list(
                        part='id,snippet',
                        q=search_query,
                        type='video',
                        maxResults=5,
                        videoCategoryId='10',  # Music category
                        order='relevance'
                    )
                    response = request.execute()
                    
                    if 'items' in response and len(response['items']) > 0:
                        # Filter results to find best match
                        for item in response['items']:
                            video_id = item['id']['videoId']
                            snippet = item.get('snippet', {})
                            title = snippet.get('title', '').lower()
                            description = snippet.get('description', '').lower()
                            
                            # Validate video ID
                            if not self._is_valid_video_id(video_id):
                                continue
                            
                            # Filter out non-music content (ads, playlists, etc.)
                            title_lower = title.lower()
                            if any(keyword in title_lower for keyword in ['#shorts', 'playlist', 'mix', 'compilation']):
                                continue
                            
                            # Check if title/description matches song
                            song_title_lower = song_title.lower()
                            artist_lower = artist_str.lower() if artist_str else ""
                            
                            # Score match quality
                            title_match = song_title_lower in title or any(
                                word in title for word in song_title_lower.split() if len(word) > 3
                            )
                            artist_match = not artist_str or any(
                                artist.lower() in title or artist.lower() in description 
                                for artist in artists[:2]
                            )
                            
                            # Prefer official audio/video
                            is_official = 'official' in title or 'official audio' in title or 'official video' in title
                            
                            # Return best match (official preferred, then good title/artist match)
                            if is_official and (title_match or artist_match):
                                logger.info(f"Found official video via API: {video_id} for {song_title}")
                                return video_id
                            
                            # Good match even if not official
                            if title_match and artist_match:
                                logger.info(f"Found matching video via API: {video_id} for {song_title}")
                                return video_id
                        
                        # If no perfect match, return first result
                        if response['items']:
                            video_id = response['items'][0]['id']['videoId']
                            if self._is_valid_video_id(video_id):
                                logger.info(f"Found video via API (first result): {video_id} for {song_title}")
                                return video_id
                
                except HttpError as e:
                    if e.resp.status == 403:
                        logger.error("YouTube API quota exceeded or API key invalid")
                        break  # Don't retry with other queries if API key is invalid
                    logger.warning(f"YouTube API error for query '{search_query}': {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error with YouTube API query '{search_query}': {e}")
                    continue
        
        except Exception as e:
            logger.error(f"YouTube API search error: {e}")
        
        return None
    
    def _search_with_scraping(self, song_title: str, artists: list) -> Optional[str]:
        """
        Fallback method: Search using web scraping.
        Used when YouTube API is not available.
        """
        if not song_title or not song_title.strip():
            logger.warning("Empty song title provided for YouTube scraping")
            return None
        
        try:
            artist_str = " ".join(artists[:2]) if artists else ""
            
            queries = [
                f"{song_title} {artist_str} official audio",
                f"{song_title} {artist_str} official",
                f"{song_title} {artist_str} music",
                f"{song_title} {artist_str}"
            ]
            
            logger.info(f"Scraping YouTube for: '{song_title}' by {artists}")
            
            for search_query in queries:
                try:
                    search_query = search_query.strip()
                    if not search_query:
                        continue
                    
                    search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(search_query)}"
                    logger.debug(f"Trying search URL: {search_url}")
                    
                    response = self.session.get(search_url, timeout=15)
                    
                    if response.status_code == 200:
                        text = response.text
                        
                        # Extract from ytInitialData JSON
                        video_ids = self._extract_video_ids_from_json(text)
                        if video_ids:
                            logger.info(f"Found {len(video_ids)} video IDs from JSON for '{search_query}'")
                            for vid_id in video_ids:
                                if self._is_valid_video_id(vid_id):
                                    logger.info(f"Found valid video ID via scraping: {vid_id} for '{song_title}'")
                                    return vid_id
                        
                        # Extract from watch URLs
                        watch_pattern = r'/watch\?v=([a-zA-Z0-9_-]{11})'
                        watch_matches = re.findall(watch_pattern, text)
                        if watch_matches:
                            logger.info(f"Found {len(watch_matches)} video IDs from URLs for '{search_query}'")
                            for vid_id in watch_matches:
                                if self._is_valid_video_id(vid_id):
                                    logger.info(f"Found valid video ID via URL scraping: {vid_id} for '{song_title}'")
                                    return vid_id
                    else:
                        logger.warning(f"YouTube search returned status {response.status_code} for '{search_query}'")
                
                except requests.exceptions.Timeout:
                    logger.warning(f"YouTube search timeout for: '{search_query}'")
                    continue
                except Exception as e:
                    logger.debug(f"Error searching YouTube for '{search_query}': {e}")
                    continue
        
        except Exception as e:
            logger.error(f"YouTube scraping error for '{song_title}': {e}")
        
        logger.warning(f"Could not find YouTube video via scraping for '{song_title}' by {artists}")
        return None
    
    def get_embed_url(self, video_id: str) -> str:
        """
        Get YouTube embed URL for a video ID with ad-blocking parameters.
        Uses youtube-nocookie.com domain which has significantly fewer ads.
        """
        # Use youtube-nocookie.com domain (fewer ads, no cookies)
        # Add aggressive ad-blocking parameters
        params = [
            'autoplay=0',
            'enablejsapi=1',
            'origin=' + requests.utils.quote('http://localhost:8000'),
            'rel=0',  # Don't show related videos
            'modestbranding=1',  # Minimal branding
            'iv_load_policy=3',  # Don't show annotations
            'fs=0',  # Disable fullscreen
            'playsinline=1',
            'controls=0',  # Hide controls (we use our own)
            'disablekb=1',  # Disable keyboard controls
            'cc_load_policy=0',  # Don't load captions
            'loop=0',  # Don't loop
            'mute=0',  # Don't mute
            'start=0',  # Start at beginning
        ]
        # Use youtube-nocookie.com instead of youtube.com (fewer ads)
        return f"https://www.youtube-nocookie.com/embed/{video_id}?{'&'.join(params)}"
    
    def get_watch_url(self, video_id: str) -> str:
        """Get YouTube watch URL for a video ID"""
        return f"https://www.youtube.com/watch?v={video_id}"


# Singleton instance
_youtube_service = None

def get_youtube_service() -> YouTubeService:
    """Get singleton instance of YouTubeService"""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service

