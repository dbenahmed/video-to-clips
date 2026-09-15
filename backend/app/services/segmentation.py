import os
import subprocess
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

try:
    from faster_whisper import WhisperModel
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("CRITICAL: Missing AI dependencies. Please run pip install faster-whisper sentence-transformers numpy")

from app.schemas.pipeline import SegmentationOptions

@dataclass
class TranscribedSentence:
    text_content: str
    start_time_seconds: float
    end_time_seconds: float
    semantic_embedding: Optional[np.ndarray] = None

@dataclass
class TopicBlock:
    block_id: int
    sentences: List[TranscribedSentence]
    start_time_seconds: float
    end_time_seconds: float
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds
        
    @property
    def full_transcript(self) -> str:
        return " ".join([s.text_content for s in self.sentences])


class AudioExtractor:
    @staticmethod
    def extract_wav_from_mp4(video_file_path: Path, output_wav_path: Path) -> bool:
        if not video_file_path.exists():
            return False
            
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"
            
        ffmpeg_command = [
            ffmpeg_exe, "-y", "-i", str(video_file_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(output_wav_path)
        ]
        
        try:
            result = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            if "moov atom not found" in e.stderr or "Invalid data found" in e.stderr:
                raise ValueError("The video file is corrupted or not a valid MP4.")
            raise RuntimeError(f"FFmpeg extraction failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("FFmpeg executable not found. Install imageio-ffmpeg.")


class TranscriptionEngine:
    def __init__(self, model_size: str = "base"):
        try:
            self.whisper_model = WhisperModel(model_size, device="cuda", compute_type="float16")
        except Exception:
            self.whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe_audio_to_sentences(self, audio_file_path: Path, progress_callback=None) -> List[TranscribedSentence]:
        segments, info = self.whisper_model.transcribe(
            str(audio_file_path), 
            vad_filter=True,
            beam_size=1,
            language="en"
        )
        
        parsed_sentences: List[TranscribedSentence] = []
        for segment in segments:
            clean_text = segment.text.strip()
            if not clean_text:
                continue
            parsed_sentences.append(TranscribedSentence(
                text_content=clean_text,
                start_time_seconds=segment.start,
                end_time_seconds=segment.end
            ))
            if progress_callback and info.duration > 0:
                progress = min(99.0, (segment.end / info.duration) * 100.0)
                progress_callback(progress)
                
        return parsed_sentences


class SemanticAnalyzer:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.embedding_model = SentenceTransformer(model_name)
        
    def embed_sentences(self, sentences: List[TranscribedSentence]) -> None:
        texts_to_embed = [s.text_content for s in sentences]
        vectors = self.embedding_model.encode(texts_to_embed, batch_size=32)
        for index, sentence in enumerate(sentences):
            sentence.semantic_embedding = vectors[index]
            
    @staticmethod
    def calculate_cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
        dot_product = np.dot(vector_a, vector_b)
        norm_a = np.linalg.norm(vector_a)
        norm_b = np.linalg.norm(vector_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))


class TopicBlockMapper:
    def __init__(self, similarity_drop_threshold: float):
        self.similarity_drop_threshold = similarity_drop_threshold
        
    def map_sentences_to_blocks(self, sentences: List[TranscribedSentence]) -> List[TopicBlock]:
        if not sentences: return []
        
        topic_blocks = []
        current_block_sentences = [sentences[0]]
        block_counter = 1
        
        for i in range(1, len(sentences)):
            prev_s = sentences[i-1]
            curr_s = sentences[i]
            
            if prev_s.semantic_embedding is None or curr_s.semantic_embedding is None:
                current_block_sentences.append(curr_s)
                continue
                
            sim = SemanticAnalyzer.calculate_cosine_similarity(prev_s.semantic_embedding, curr_s.semantic_embedding)
            
            if sim < self.similarity_drop_threshold:
                topic_blocks.append(TopicBlock(
                    block_id=block_counter,
                    sentences=current_block_sentences,
                    start_time_seconds=current_block_sentences[0].start_time_seconds,
                    end_time_seconds=current_block_sentences[-1].end_time_seconds
                ))
                block_counter += 1
                current_block_sentences = [curr_s]
            else:
                current_block_sentences.append(curr_s)
                
        if current_block_sentences:
            topic_blocks.append(TopicBlock(
                block_id=block_counter,
                sentences=current_block_sentences,
                start_time_seconds=current_block_sentences[0].start_time_seconds,
                end_time_seconds=current_block_sentences[-1].end_time_seconds
            ))
        return topic_blocks


class ClipExtractor:
    def __init__(self, min_duration_sec: float, max_duration_sec: float):
        self.min_duration_sec = min_duration_sec
        self.max_duration_sec = max_duration_sec
        
    def extract_golden_clips(self, topic_blocks: List[TopicBlock]) -> List[dict]:
        extracted_clips = []
        clip_counter = 1
        
        for block in topic_blocks:
            duration = block.duration_seconds
            
            if duration < self.min_duration_sec:
                continue
            elif self.min_duration_sec <= duration <= self.max_duration_sec:
                extracted_clips.append({
                    "clip_id": f"clip_{clip_counter}",
                    "start_time_seconds": block.start_time_seconds,
                    "end_time_seconds": block.end_time_seconds,
                    "duration_seconds": duration,
                    "text_transcript": block.full_transcript,
                    "extraction_reasoning": "Perfect Natural Fit (Topic bounded perfectly within limits)"
                })
                clip_counter += 1
            else:
                target_end_time = block.start_time_seconds + self.max_duration_sec
                actual_end_time = block.start_time_seconds
                rambler_sentences = []
                
                for sentence in block.sentences:
                    if sentence.end_time_seconds > target_end_time:
                        break
                    actual_end_time = sentence.end_time_seconds
                    rambler_sentences.append(sentence.text_content)
                
                if rambler_sentences:
                    extracted_clips.append({
                        "clip_id": f"clip_{clip_counter}",
                        "start_time_seconds": block.start_time_seconds,
                        "end_time_seconds": actual_end_time,
                        "duration_seconds": actual_end_time - block.start_time_seconds,
                        "text_transcript": " ".join(rambler_sentences),
                        "extraction_reasoning": f"Truncated Rambler (Original block was {duration:.1f}s)"
                    })
                    clip_counter += 1
                    
        return extracted_clips


def run_segmentation(video_path: Path, options: SegmentationOptions, progress_callback=None) -> List[dict]:
    """Runs the full segmentation pipeline and returns a list of dictionaries matching ClipResponse schema."""
    audio_wav_path = video_path.parent / f"{video_path.stem}_audio.wav"
    
    try:
        AudioExtractor.extract_wav_from_mp4(video_path, audio_wav_path)
        
        transcriber = TranscriptionEngine(model_size=options.whisper_model_size)
        sentences = transcriber.transcribe_audio_to_sentences(audio_wav_path, progress_callback)
        
        analyzer = SemanticAnalyzer()
        analyzer.embed_sentences(sentences)
        
        mapper = TopicBlockMapper(similarity_drop_threshold=options.similarity_drop_threshold)
        blocks = mapper.map_sentences_to_blocks(sentences)
        
        miner = ClipExtractor(
            min_duration_sec=options.min_clip_duration_seconds, 
            max_duration_sec=options.max_clip_duration_seconds
        )
        return miner.extract_golden_clips(blocks)
        
    finally:
        if audio_wav_path.exists():
            audio_wav_path.unlink()
