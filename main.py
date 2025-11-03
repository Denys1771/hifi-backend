from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from typing import List, Optional
import re

app = FastAPI(title="HiFi Music API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos
class Track(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    cover_url: Optional[str]
    duration: int
    quality: str = "High"

class SearchResponse(BaseModel):
    status: str
    data: dict

class StreamResponse(BaseModel):
    status: str
    data: dict

# Función para buscar en YouTube
def search_youtube(query: str, max_results: int = 20) -> List[dict]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'format': 'bestaudio/best',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            tracks = []
            for entry in result.get('entries', []):
                if entry:
                    tracks.append({
                        'id': entry.get('id'),
                        'title': entry.get('title', 'Unknown'),
                        'artist': extract_artist(entry.get('title', '')),
                        'album': entry.get('album', 'Unknown'),
                        'cover_url': entry.get('thumbnail'),
                        'duration': (entry.get('duration', 0) or 0) * 1000,
                        'quality': 'High',
                    })
            
            return tracks
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        return []

def extract_artist(title: str) -> str:
    """Extrae el artista del título de YouTube"""
    patterns = [
        r'^([^-]+)\s*-\s*',
        r'^([^:]+)\s*:\s*',
        r'\(([^)]+)\)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1).strip()
    
    return "Unknown Artist"

def get_stream_url(video_id: str, quality: str = "high") -> Optional[str]:
    """Obtiene URL de streaming directa"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            
            formats = info.get('formats', [])
            audio_formats = [f for f in formats if f.get('acodec') != 'none']
            
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0))
                return best_audio.get('url')
            
            return info.get('url')
    except Exception as e:
        print(f"Error getting stream URL: {e}")
        return None

# Endpoints
@app.get("/")
def root():
    return {
        "name": "HiFi Music API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/search")
async def search(
    q: str = Query(..., description="Search query"),
    type: str = Query("tracks", description="Search type")
):
    """Buscar música - GET METHOD"""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    tracks = search_youtube(q)
    
    return {
        "status": "success",
        "data": {
            "tracks": tracks,
            "artists": [],
            "albums": []
        }
    }

@app.get("/api/track/{track_id}")
async def get_track(track_id: str):
    """Obtener detalles de una canción"""
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={track_id}", download=False)
            
            return {
                "status": "success",
                "data": {
                    "id": track_id,
                    "title": info.get('title'),
                    "artist": extract_artist(info.get('title', '')),
                    "album": info.get('album', 'Unknown'),
                    "cover_url": info.get('thumbnail'),
                    "duration": (info.get('duration', 0) or 0) * 1000,
                    "quality": "High",
                    "bitrate": f"{info.get('abr', 128)} kbps",
                    "sample_rate": "44.1 kHz"
                }
            }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/stream/{track_id}")
async def get_stream(
    track_id: str,
    quality: str = Query("high", description="Audio quality")
):
    """Obtener URL de streaming"""
    url = get_stream_url(track_id, quality)
    
    if not url:
        raise HTTPException(status_code=404, detail="Stream URL not found")
    
    return {
        "status": "success",
        "data": {
            "stream_url": url,
            "quality": quality,
            "expires_at": None
        }
    }

@app.get("/api/download/{track_id}")
async def get_download(
    track_id: str,
    quality: str = Query("high", description="Audio quality")
):
    """Obtener URL de descarga"""
    url = get_stream_url(track_id, quality)
    
    if not url:
        raise HTTPException(status_code=404, detail="Download URL not found")
    
    return {
        "status": "success",
        "data": {
            "download_url": url,
            "quality": quality,
            "file_size": None,
            "expires_at": None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)