import io
import os
import re
import time
import hashlib
import asyncio
import numpy as np
import soundfile as sf
from typing import Dict, List, Optional, Tuple

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

class TTSEngine:
    def __init__(self):
        if TORCH_AVAILABLE and torch.cuda.is_available():
            self.device = 'cuda'
        elif TORCH_AVAILABLE:
            self.device = 'cpu'
        else:
            self.device = 'cloud'
        print(f"[TTSEngine] Initializing TTS Engine on {self.device}...")
        
        # Lazy loaded pipeline
        self._pipeline_a = None
        self._pipeline_b = None
        self._voice_cache: Dict[str, any] = {}
        self._audio_cache: Dict[str, bytes] = {} # MD5 -> WAV bytes
        
        # Curated voices list
        self.voices = [
            # Celebrity AI Voices (RVC v2 + Kokoro)
            {"id": "rvc_jordan_peterson", "name": "Dr. Jordan Peterson (Celebrity Voice)", "gender": "Male", "accent": "Canadian", "lang": "rvc", "tier": "Celebrity"},
            {"id": "rvc_mrbeast", "name": "MrBeast (Celebrity Voice)", "gender": "Male", "accent": "American", "lang": "rvc", "tier": "Celebrity"},

            # American Female
            {"id": "af_heart", "name": "Heart (Warm & Expressive)", "gender": "Female", "accent": "American", "lang": "a", "tier": "Top Pick"},
            {"id": "af_bella", "name": "Bella (Clear & Friendly)", "gender": "Female", "accent": "American", "lang": "a", "tier": "Popular"},
            {"id": "af_nicole", "name": "Nicole (Crisp & Direct)", "gender": "Female", "accent": "American", "lang": "a", "tier": "Standard"},
            {"id": "af_sarah", "name": "Sarah (Gentle & Smooth)", "gender": "Female", "accent": "American", "lang": "a", "tier": "Standard"},
            {"id": "af_sky", "name": "Sky (Bright & Engaging)", "gender": "Female", "accent": "American", "lang": "a", "tier": "Popular"},
            
            # American Male
            {"id": "am_adam", "name": "Adam (Authoritative & Deep)", "gender": "Male", "accent": "American", "lang": "a", "tier": "Top Pick"},
            {"id": "am_michael", "name": "Michael (Dynamic Narrator)", "gender": "Male", "accent": "American", "lang": "a", "tier": "Popular"},
            {"id": "am_fenrir", "name": "Fenrir (Rich Baritone)", "gender": "Male", "accent": "American", "lang": "a", "tier": "Standard"},
            {"id": "am_puck", "name": "Puck (Energetic & Quick)", "gender": "Male", "accent": "American", "lang": "a", "tier": "Standard"},
            {"id": "am_echo", "name": "Echo (Calm & Balanced)", "gender": "Male", "accent": "American", "lang": "a", "tier": "Standard"},

            # British Female
            {"id": "bf_emma", "name": "Emma (Sophisticated & Polished)", "gender": "Female", "accent": "British", "lang": "b", "tier": "Top Pick"},
            {"id": "bf_isabella", "name": "Isabella (Formal & Elegant)", "gender": "Female", "accent": "British", "lang": "b", "tier": "Popular"},
            {"id": "bf_alice", "name": "Alice (Storyteller)", "gender": "Female", "accent": "British", "lang": "b", "tier": "Standard"},

            # British Male
            {"id": "bm_george", "name": "George (Classic BBC Narration)", "gender": "Male", "accent": "British", "lang": "b", "tier": "Top Pick"},
            {"id": "bm_lewis", "name": "Lewis (Warm & Scholarly)", "gender": "Male", "accent": "British", "lang": "b", "tier": "Popular"},
            {"id": "bm_fable", "name": "Fable (Audiobook Voice)", "gender": "Male", "accent": "British", "lang": "b", "tier": "Standard"},

            # Edge-TTS Online Options (Optional fallback)
            {"id": "edge:en-US-JennyNeural", "name": "Jenny (Azure Neural)", "gender": "Female", "accent": "American", "lang": "edge", "tier": "Cloud"},
            {"id": "edge:en-US-GuyNeural", "name": "Guy (Azure Neural)", "gender": "Male", "accent": "American", "lang": "edge", "tier": "Cloud"},
            {"id": "edge:en-GB-SoniaNeural", "name": "Sonia (Azure UK)", "gender": "Female", "accent": "British", "lang": "edge", "tier": "Cloud"},

            # Arabic Neural Voices
            {"id": "edge:ar-EG-SalmaNeural", "name": "Salma (Egyptian Arabic)", "gender": "Female", "accent": "Arabic (Egypt)", "lang": "edge", "tier": "Arabic"},
            {"id": "edge:ar-EG-ShakirNeural", "name": "Shakir (Egyptian Arabic)", "gender": "Male", "accent": "Arabic (Egypt)", "lang": "edge", "tier": "Arabic"},
            {"id": "edge:ar-SA-HamedNeural", "name": "Hamed (Saudi Arabic)", "gender": "Male", "accent": "Arabic (Saudi)", "lang": "edge", "tier": "Arabic"},
            {"id": "edge:ar-SA-ZariyahNeural", "name": "Zariyah (Saudi Arabic)", "gender": "Female", "accent": "Arabic (Saudi)", "lang": "edge", "tier": "Arabic"},
        ]

    def _get_pipeline(self, lang: str):
        from kokoro import KPipeline
        if lang == 'b':
            if self._pipeline_b is None:
                print(f"[TTSEngine] Loading British English pipeline on {self.device}...")
                self._pipeline_b = KPipeline(lang_code='b', device=self.device)
            return self._pipeline_b
        else:
            if self._pipeline_a is None:
                print(f"[TTSEngine] Loading American English pipeline on {self.device}...")
                self._pipeline_a = KPipeline(lang_code='a', device=self.device)
            return self._pipeline_a

    def get_voice_info(self, voice_id: str) -> dict:
        for v in self.voices:
            if v["id"] == voice_id:
                return v
        return self.voices[0]

    def synthesize(self, text: str, voice_id: str = "af_heart", speed: float = 1.0) -> bytes:
        """
        Synthesizes text into 24kHz WAV audio bytes.
        Results are cached in memory by hash for instant replay.
        """
        text = text.strip()
        if not text:
            # Return 0.2s of silence
            silence = np.zeros(4800, dtype=np.float32)
            bio = io.BytesIO()
            sf.write(bio, silence, 24000, format='WAV')
            return bio.getvalue()

        cache_key = hashlib.md5(f"{text}_{voice_id}_{speed:.2f}".encode('utf-8')).hexdigest()
        if cache_key in self._audio_cache:
            return self._audio_cache[cache_key]

        if voice_id.startswith("rvc_"):
            wav_bytes = self._synthesize_rvc(text, voice_id, speed)
        elif voice_id.startswith("edge:"):
            # Handle Edge-TTS fallback
            wav_bytes = self._synthesize_edge(text, voice_id[5:], speed)
        else:
            wav_bytes = self._synthesize_kokoro(text, voice_id, speed)

        # Cache up to 1000 items in memory
        if len(self._audio_cache) > 1000:
            self._audio_cache.pop(next(iter(self._audio_cache)))
        self._audio_cache[cache_key] = wav_bytes

        return wav_bytes

    def _synthesize_rvc(self, text: str, voice_id: str, speed: float) -> bytes:
        from speechify_local.rvc_engine import rvc_engine
        cfg = rvc_engine.models_config.get(voice_id, {})
        base_voice = cfg.get("base_voice", "am_michael")
        speed_mult = cfg.get("speed_multiplier", 1.0)
        effective_speed = speed * speed_mult
        base_wav = self._synthesize_kokoro(text, base_voice, effective_speed)
        return rvc_engine.convert_audio(base_wav, voice_id)

    def _synthesize_kokoro(self, text: str, voice_id: str, speed: float) -> bytes:
        if not TORCH_AVAILABLE:
            # Automatic fallback to Azure Neural voice when running on cloud without torch
            fallback_voice = "en-US-GuyNeural" if (voice_id.startswith("am_") or voice_id.startswith("bm_")) else "en-US-JennyNeural"
            return self._synthesize_edge(text, fallback_voice, speed)

        v_info = self.get_voice_info(voice_id)
        pipeline = self._get_pipeline(v_info.get("lang", "a"))
        
        # Generator yields (graphemes, phonemes, audio_tensor)
        generator = pipeline(text, voice=voice_id, speed=speed)
        audio_chunks = []
        for _, _, audio in generator:
            if audio is not None and len(audio) > 0:
                audio_chunks.append(audio)

        if not audio_chunks:
            # Return silence if no audio was generated
            full_audio = np.zeros(4800, dtype=np.float32)
        elif len(audio_chunks) == 1:
            full_audio = audio_chunks[0]
        else:
            full_audio = np.concatenate(audio_chunks)

        # Convert to numpy float32 if needed
        if isinstance(full_audio, torch.Tensor):
            full_audio = full_audio.detach().cpu().numpy()

        bio = io.BytesIO()
        sf.write(bio, full_audio, 24000, format='WAV')
        return bio.getvalue()

    def _synthesize_edge(self, text: str, voice_name: str, speed: float) -> bytes:
        import edge_tts
        rate_pct = int((speed - 1.0) * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        async def _run_edge():
            communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)
            mp3_bytes = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes.write(chunk["data"])
            return mp3_bytes.getvalue()

        # Run async in loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            mp3_data = loop.run_until_complete(_run_edge())
        else:
            mp3_data = loop.run_until_complete(_run_edge())

        return mp3_data

# Global instance
tts_engine = TTSEngine()
