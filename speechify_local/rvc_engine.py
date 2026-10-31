import os
import io
import math
import logging
import numpy as np
import scipy.signal
import soundfile as sf
import torch
import torch.nn.functional as F
import faiss
import parselmouth
import librosa
from transformers import HubertModel
from speechify_local.rvc.models import SynthesizerTrnMs768NSFsid

logger = logging.getLogger("RVCEngine")

def change_rms(data1: np.ndarray, sr1: int, data2: np.ndarray, sr2: int, rate: float = 0.25) -> np.ndarray:
    """
    Transfers the dynamic volume envelope from source audio (data1) onto 
    converted audio (data2) to preserve crisp natural phrasing and eliminate muffling.
    """
    try:
        frame_len1 = int(sr1 // 2) * 2
        hop_len1 = int(sr1 // 2)
        rms1 = librosa.feature.rms(y=data1, frame_length=frame_len1, hop_length=hop_len1)
        
        frame_len2 = int(sr2 // 2) * 2
        hop_len2 = int(sr2 // 2)
        rms2 = librosa.feature.rms(y=data2, frame_length=frame_len2, hop_length=hop_len2)
        
        t_rms1 = torch.from_numpy(rms1).float()
        t_rms2 = torch.from_numpy(rms2).float()
        
        target_len = data2.shape[0]
        t_rms1 = F.interpolate(t_rms1.unsqueeze(0), size=target_len, mode="linear", align_corners=False).squeeze()
        t_rms2 = F.interpolate(t_rms2.unsqueeze(0), size=target_len, mode="linear", align_corners=False).squeeze()
        t_rms2 = torch.clamp(t_rms2, min=1e-6)
        
        gain = torch.pow(t_rms1, 1.0 - rate) * torch.pow(t_rms2, rate - 1.0)
        gain_np = gain.numpy()
        data2 = data2 * gain_np
    except Exception as e:
        logger.warning("change_rms fallback: %s", e)
    return data2

class RVCEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._hubert = None
        self._models = {}
        
        # Highpass filter (48Hz cutoff at 16kHz) to scrub DC offset and sub-bass rumble
        self.bh, self.ah = scipy.signal.butter(N=5, Wn=48, btype="high", fs=16000)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.models_config = {
            "rvc_jordan_peterson": {
                "name": "Dr. Jordan Peterson (Celebrity Voice)",
                # am_michael provides expressive cadence, articulate phrasing and intellectual inflection
                "base_voice": "am_michael",
                "pth": os.path.join(base_dir, "rvc_models", "Jordan_Peterson", "JordanPeterson", "JordanPeterson.pth"),
                "index": os.path.join(base_dir, "rvc_models", "Jordan_Peterson", "JordanPeterson", "added_IVF3550_Flat_nprobe_1_JordanPeterson_v2.index"),
                "pitch_shift": 1,  # Centered at Peterson's signature ~130-140Hz vocal range
                "speed_multiplier": 0.88, # Measured, philosophical cadence
                "index_rate": 0.75,
                "rms_mix_rate": 0.25,
                "gender": "Male",
                "accent": "Canadian",
                "tier": "Celebrity"
            },
            "rvc_mrbeast": {
                "name": "MrBeast (Celebrity Voice)",
                # am_puck provides quick, punchy, energetic pacing
                "base_voice": "am_puck",
                "pth": os.path.join(base_dir, "rvc_models", "MrBeast", "MrBeast.pth"),
                "index": os.path.join(base_dir, "rvc_models", "MrBeast", "added_IVF355_Flat_nprobe_1_MrBeast_v2.index"),
                "pitch_shift": 1,  # Upbeat vocal resonance
                "speed_multiplier": 1.02, # Fast-paced YouTube style
                "index_rate": 0.75,
                "rms_mix_rate": 0.25,
                "gender": "Male",
                "accent": "American",
                "tier": "Celebrity"
            }
        }
        self.hubert_path = os.path.join(base_dir, "rvc", "hubert_base")

    def _get_hubert(self):
        if self._hubert is None:
            logger.info("Loading HuBERT SSL Feature Extractor on %s...", self.device)
            self._hubert = HubertModel.from_pretrained(self.hubert_path).to(self.device).eval()
        return self._hubert

    def _get_model(self, voice_id: str):
        if voice_id in self._models:
            return self._models[voice_id]

        cfg = self.models_config.get(voice_id)
        if not cfg or not os.path.exists(cfg["pth"]):
            raise FileNotFoundError(f"RVC voice model checkpoint not found for {voice_id}")

        logger.info("Loading RVC weights for %s...", voice_id)
        cpt = torch.load(cfg["pth"], map_location=self.device)
        net_g = SynthesizerTrnMs768NSFsid(*cpt["config"], is_half=False).to(self.device).eval()
        if hasattr(net_g, "enc_q"):
            del net_g.enc_q
        net_g.load_state_dict(cpt["weight"], strict=False)

        index = None
        if os.path.exists(cfg.get("index", "")):
            try:
                index = faiss.read_index(cfg["index"])
                index.make_direct_map()
                logger.info("Faiss index loaded with direct mapping for %s (%d vectors).", voice_id, index.ntotal)
            except Exception as e:
                logger.warning("Could not load Faiss index for %s: %s", voice_id, e)
                index = None

        self._models[voice_id] = (net_g, index, 40000, cfg)
        return self._models[voice_id]

    def convert_audio(self, source_wav_bytes: bytes, voice_id: str) -> bytes:
        """
        Converts source speech audio bytes into the target celebrity voice with
        sample-accurate 100Hz temporal frame alignment (scale_factor=2),
        boundary reflection padding, Parselmouth autocorrelation pitch tracking,
        and dynamic RMS envelope matching.
        """
        cfg = self.models_config.get(voice_id)
        if not cfg:
            return source_wav_bytes

        source_audio, sr_in = sf.read(io.BytesIO(source_wav_bytes))
        if len(source_audio) < 480: # Less than 20ms
            return source_wav_bytes

        if len(source_audio.shape) > 1:
            source_audio = source_audio.mean(axis=1)

        net_g, index, target_sr, cfg = self._get_model(voice_id)
        hubert = self._get_hubert()

        # 1. Resample source audio to 16,000 Hz for HuBERT and Pitch extraction
        audio_16k = librosa.resample(source_audio.astype(np.float32), orig_sr=sr_in, target_sr=16000)

        # 2. High-pass filter to remove DC drift and sub-bass thump (<48Hz)
        audio_16k = scipy.signal.filtfilt(self.bh, self.ah, audio_16k).astype(np.float32)

        # 3. Reflection padding (0.5s on each side) to prevent border truncation and neural edge artifacts
        pad_len_16k = 8000  # 0.5s at 16kHz
        pad_tgt = int(pad_len_16k * (target_sr / 16000)) # 20,000 samples at 40kHz
        audio_pad = np.pad(audio_16k, (pad_len_16k, pad_len_16k), mode="reflect").astype(np.float32)

        p_len = len(audio_pad) // 160 # 100 frames per second at 10ms hop

        # 4. Extract continuous fundamental frequency (F0) with Parselmouth
        sound = parselmouth.Sound(audio_pad, 16000)
        pitch_obj = sound.to_pitch_ac(
            time_step=0.010,
            voicing_threshold=0.6,
            pitch_floor=50.0,
            pitch_ceiling=1100.0
        )
        f0 = pitch_obj.selected_array["frequency"].copy()

        # Pad or trim f0 array to strictly match p_len frames
        pad_size = (p_len - len(f0) + 1) // 2
        if pad_size > 0 or p_len - len(f0) - pad_size > 0:
            f0 = np.pad(f0, [[max(0, pad_size), max(0, p_len - len(f0) - pad_size)]], mode="constant")
        f0 = f0[:p_len]

        # Smooth unvoiced frames through linear interpolation to prevent neural vocoder glitching
        uv = (f0 == 0)
        if uv.any() and (~uv).any():
            f0[uv] = np.interp(np.where(uv)[0], np.where(~uv)[0], f0[~uv])

        # Apply pitch shift (semitones)
        pitch_shift = cfg.get("pitch_shift", 0)
        if pitch_shift != 0:
            f0 = f0 * (2.0 ** (pitch_shift / 12.0))

        f0_bak = f0.copy()

        # Quantize F0 to coarse pitch bins (1-255)
        f0_min, f0_max = 50.0, 1100.0
        f0_mel_min = 1127.0 * np.log(1.0 + f0_min / 700.0)
        f0_mel_max = 1127.0 * np.log(1.0 + f0_max / 700.0)
        f0_mel = 1127.0 * np.log(1.0 + f0 / 700.0)
        f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - f0_mel_min) * 254.0 / (f0_mel_max - f0_mel_min) + 1.0
        f0_mel[f0_mel <= 1] = 1.0
        f0_mel[f0_mel > 255] = 255.0
        f0_coarse = np.rint(f0_mel).astype(np.int64)

        # 5. Extract 768-D HuBERT representations
        t_16k = torch.from_numpy(audio_pad).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feats = hubert(t_16k).last_hidden_state

        feats_np = feats.squeeze(0).cpu().numpy().astype(np.float32)
        index_rate = cfg.get("index_rate", 0.75)

        # 6. Faiss index retrieval blending with trained celebrity acoustic vectors
        if index is not None and index_rate > 0:
            try:
                score, ix = index.search(feats_np, k=8)
                score = np.maximum(score, 1e-6)
                weight = np.square(1.0 / score)
                weight /= weight.sum(axis=1, keepdims=True)
                
                ntotal = index.ntotal
                flat_ix = ix.reshape(-1)
                reconstructed = np.array([
                    index.reconstruct(int(idx_i)) if (0 <= int(idx_i) < ntotal) else np.zeros(768, dtype=np.float32)
                    for idx_i in flat_ix
                ], dtype=np.float32).reshape(ix.shape[0], ix.shape[1], -1)
                npy = np.sum(reconstructed * np.expand_dims(weight, axis=-1), axis=1)
                feats_np = index_rate * npy + (1.0 - index_rate) * feats_np
            except Exception as ex:
                logger.warning("Faiss retrieval error: %s", ex)

        feats_t = torch.from_numpy(feats_np).unsqueeze(0).to(self.device)

        # 7. CRITICAL: Interpolate HuBERT features by 2x to achieve 100Hz frame rate
        feats_t = F.interpolate(feats_t.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)

        # 8. Align frame count
        p_len = min(p_len, feats_t.shape[1])
        feats_t = feats_t[:, :p_len]
        f0_coarse = f0_coarse[:p_len]
        f0_bak = f0_bak[:p_len]

        pitch_t = torch.from_numpy(f0_coarse).unsqueeze(0).to(self.device)
        nsff0_t = torch.from_numpy(f0_bak.astype(np.float32)).unsqueeze(0).to(self.device)
        lengths_t = torch.LongTensor([p_len]).to(self.device)
        sid_t = torch.LongTensor([0]).to(self.device)

        # 9. Neural Source Filter HiFi-GAN Vocoder Synthesis (40kHz)
        with torch.no_grad():
            audio_out, _, _ = net_g.infer(feats_t, lengths_t, pitch_t, nsff0_t, sid_t)

        out_np = audio_out.squeeze().cpu().numpy()

        # 10. Slice off reflection padding to retain only pure speech
        if len(out_np) > pad_tgt * 2:
            out_np = out_np[pad_tgt : -pad_tgt]

        # 11. Dynamic RMS Volume Envelope Matching
        rms_rate = cfg.get("rms_mix_rate", 0.25)
        if rms_rate < 1.0:
            out_np = change_rms(source_audio.astype(np.float32), sr_in, out_np, target_sr, rate=rms_rate)

        # 12. Resample back to standard 24,000 Hz using high-quality polyphase resampler
        out_24k = librosa.resample(out_np.astype(np.float32), orig_sr=target_sr, target_sr=24000)

        # 13. Peak normalization to commercial audio standard (-1.4 dB / 0.85 peak)
        max_val = np.abs(out_24k).max()
        if max_val > 0.05:
            out_24k = out_24k * (0.85 / max_val)

        bio = io.BytesIO()
        sf.write(bio, out_24k, 24000, format="WAV")
        return bio.getvalue()

rvc_engine = RVCEngine()
