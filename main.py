from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import logging
from typing import List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HiFi Music API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos
class SearchRequest(BaseModel):
    query: str

class Track(BaseModel):
    id: str
    titulo: str
    artista: str
    album: Optional[str] = None
    duracion: int
    imagenUrl: Optional[str] = None
    audioUrl: str
    fuente: str = "youtube"

class SearchResponse(BaseModel):
    tracks: List[Track]

# Configuración de yt-dlp
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

@app.get("/")
async def root():
    return {"message": "HiFi Music API", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/search", response_model=SearchResponse)
async def search_tracks(request: SearchRequest):
    try:
        logger.info(f"Buscando: {request.query}")
        
        ydl_opts = YDL_OPTS.copy()
        ydl_opts['default_search'] = 'ytsearch10'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(request.query, download=False)
            
            if not result or 'entries' not in result:
                return SearchResponse(tracks=[])
            
            tracks = []
            for entry in result['entries']:
                if not entry:
                    continue
                
                # Buscar el mejor formato de audio
                audio_url = None
                if 'formats' in entry:
                    for fmt in entry['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            audio_url = fmt.get('url')
                            break
                
                # Si no encuentra audio solo, usar URL directa
                if not audio_url:
                    audio_url = entry.get('url')
                
                if not audio_url:
                    continue
                
                track = Track(
                    id=entry.get('id', ''),
                    titulo=entry.get('title', 'Sin título'),
                    artista=entry.get('uploader', 'Desconocido'),
                    album=entry.get('album'),
                    duracion=int(entry.get('duration', 0)),
                    imagenUrl=entry.get('thumbnail'),
                    audioUrl=audio_url,
                    fuente="youtube"
                )
                tracks.append(track)
            
            logger.info(f"Encontradas {len(tracks)} canciones")
            return SearchResponse(tracks=tracks)
            
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/track/{track_id}")
async def get_track(track_id: str):
    try:
        logger.info(f"Obteniendo track: {track_id}")
        
        url = f"https://www.youtube.com/watch?v={track_id}"
        
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Buscar el mejor formato de audio
            audio_url = None
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        audio_url = fmt.get('url')
                        break
            
            if not audio_url:
                audio_url = info.get('url')
            
            if not audio_url:
                raise HTTPException(status_code=404, detail="No se encontró URL de audio")
            
            track = Track(
                id=info.get('id', ''),
                titulo=info.get('title', 'Sin título'),
                artista=info.get('uploader', 'Desconocido'),
                album=info.get('album'),
                duracion=int(info.get('duration', 0)),
                imagenUrl=info.get('thumbnail'),
                audioUrl=audio_url,
                fuente="youtube"
            )
            
            return track
            
    except Exception as e:
        logger.error(f"Error obteniendo track: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)