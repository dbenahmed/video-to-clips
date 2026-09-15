"""
================================================================================
PIPELINE PLAYGROUND: Video Segmentation (Clipping)
================================================================================
Purpose:
    This script is dedicated exclusively to finding logical clip boundaries 
    (segmentation) based on audio transcriptions and semantic topic shifts.
    It uses an "Extraction" paradigm (Gold Mining) rather than Partitioning.

Approach (The "Gold Mining" Principle):
    Traditional clipping algorithms use "Partitioning"—they blindly chop a video 
    into contiguous 30-second blocks from left to right. This often forces 
    unrelated topics or boring transitions into the same clip. 
    
    This script uses "Extraction" (Gold Mining). We map the entire video first, 
    shatter it into isolated "Topic Blocks", and only extract the blocks that 
    naturally stand alone as perfect clips.

    Example:
    - 0:00 to 0:15: "Welcome back to the podcast..." (Topic Block 1)
    - 0:15 to 1:00: "Here is why AI is the future..." (Topic Block 2)
    - 1:00 to 1:10: "So yeah, anyway..." (Topic Block 3)
    
    Instead of combining these into a messy 1-minute clip, the Semantic Analyzer 
    mathematically detects the topic shifts. The Extractor throws away Block 1 
    (Garbage), throws away Block 3 (Garbage), and extracts Block 2 as a perfect, 
    standalone 45-second golden clip!

    Step-by-Step:
    1. Transcribe: Whisper detects sentences and exact timestamps.
    2. Vectorize: Sentence-Transformers (all-MiniLM-L6-v2) maps sentence meanings.
    3. Shatter: Cosine similarity drops identify cohesive "Topic Blocks".
    4. Extract: The miner keeps the gold (30-60s blocks) and trashes the dirt.
================================================================================
"""

import os
import json
import subprocess
import numpy as np  # Used for high-performance math operations (like calculating Cosine Similarity between vectors)
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

# Attempt to import heavy AI libraries, providing a helpful error if missing
try:
    # WhisperModel: Uses AI to convert raw audio into text with precise start/end timestamps.
    from faster_whisper import WhisperModel
    
    # SentenceTransformer: Takes a string of text and outputs a 384-dimensional mathematical vector representing its semantic meaning.
    # EXAMPLE OUTPUT: 
    # "I love my dog" -> array([-0.034, 0.128, -0.982, 0.004, ...]) (384 floating point numbers)
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("CRITICAL: Missing AI dependencies.")
    print("Please run: pip install faster-whisper sentence-transformers numpy")
    exit(1)


# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class TranscribedSentence:
    """Represents a complete grammatical sentence with exact timestamps."""
    text_content: str
    start_time_seconds: float
    end_time_seconds: float
    semantic_embedding: Optional[np.ndarray] = None


@dataclass
class TopicBlock:
    """Represents a cohesive block of sentences discussing the exact same topic."""
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


@dataclass
class ExtractedClip:
    """The final golden output: a high-quality standalone short-form clip."""
    clip_id: str
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float
    text_transcript: str
    extraction_reasoning: str


# ============================================================================
# MODULE 1: AUDIO EXTRACTION
# ============================================================================

class AudioExtractor:
    """Responsibility: Safely extract a lightweight audio track from a video file."""
    
    @staticmethod
    def extract_wav_from_mp4(video_file_path: Path, output_wav_path: Path) -> bool:
        """
        Uses FFmpeg to extract a 16kHz mono WAV file. 
        16kHz mono is the optimal format required by the Whisper AI model.
        """
        if not video_file_path.exists():
            print(f"Error: Video file not found at {video_file_path}")
            return False
            
        print(f"Extracting audio to {output_wav_path.name}...")
        
        # FFmpeg command: -y (overwrite), -vn (no video), -acodec pcm_s16le (WAV format), 
        # -ar 16000 (16kHz sample rate), -ac 1 (mono channel)
        ffmpeg_command = [
            "ffmpeg", "-y", "-i", str(video_file_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(output_wav_path)
        ]
        
        try:
            # We use DEVNULL to hide the massive wall of FFmpeg logs
            subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except subprocess.CalledProcessError:
            print("Error: FFmpeg extraction failed. Is FFmpeg installed on your system?")
            return False


# ============================================================================
# MODULE 2: AI TRANSCRIPTION
# ============================================================================

class TranscriptionEngine:
    """Responsibility: Convert audio into grammatically correct sentences with timestamps."""
    
    def __init__(self, model_size: str = "base"):
        # We load the Whisper model. 'base' is fast and highly accurate for English.
        print(f"Loading Whisper model ({model_size})...")
        self.whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe_audio_to_sentences(self, audio_file_path: Path) -> List[TranscribedSentence]:
        """Runs Whisper and parses the raw segments into our TranscribedSentence DTO."""
        print("Transcribing audio (this may take a moment)...")
        
        # We set vad_filter=True to ignore silent parts of the audio
        segments, _ = self.whisper_model.transcribe(str(audio_file_path), vad_filter=True)
        
        parsed_sentences: List[TranscribedSentence] = []
        
        # Note: Whisper natively attempts to group text by punctuation into "segments".
        # For this playground, we will trust Whisper's default segmentation as sentences.
        # In production, we might want to iterate word-by-word and strictly look for "." or "?".
        for segment in segments:
            clean_text = segment.text.strip()
            if not clean_text:
                continue
                
            sentence_obj = TranscribedSentence(
                text_content=clean_text,
                start_time_seconds=segment.start,
                end_time_seconds=segment.end
            )
            parsed_sentences.append(sentence_obj)
            
        # EXAMPLE OUTPUT OF THIS STEP:
        # [
        #   TranscribedSentence(
        #       text_content="Welcome to the podcast, guys.",
        #       start_time_seconds=0.0,
        #       end_time_seconds=2.4,
        #       semantic_embedding=None
        #   ),
        #   ...
        # ]
        return parsed_sentences


# ============================================================================
# MODULE 3: SEMANTIC ANALYSIS (EMBEDDINGS)
# ============================================================================

class SemanticAnalyzer:
    """Responsibility: Convert text into mathematical vectors and calculate similarities."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Loads the tiny, lightning-fast Sentence Transformer model
        print(f"Loading Sentence-Transformer model ({model_name})...")
        self.embedding_model = SentenceTransformer(model_name)
        
    def embed_sentences(self, sentences: List[TranscribedSentence]) -> None:
        """Populates the semantic_embedding field for a list of sentences in-place."""
        print(f"Generating semantic embeddings for {len(sentences)} sentences...")
        
        # We extract just the text to pass to the AI
        texts_to_embed = [sentence.text_content for sentence in sentences]
        
        # The AI returns a matrix of vectors (one vector per sentence)
        vectors = self.embedding_model.encode(texts_to_embed)
        
        for index, sentence in enumerate(sentences):
            sentence.semantic_embedding = vectors[index]
            
        # EXAMPLE MUTATION FROM THIS STEP:
        # sentence.semantic_embedding = array([-0.034, 0.128, -0.982, ...]) # (384 floats)
            
    @staticmethod
    def calculate_cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
        """
        Calculates how mathematically similar two topics are (0.0 to 1.0).
        
        EXAMPLE OF HOW THIS MATH WORKS:
        If vector_a = "I love my dog" and vector_b = "My favorite pet is a retriever"
        The equation below (Dot Product / Normalization) outputs: ~0.85 (Highly similar).
        
        If vector_b = "I need to repair my car engine"
        The equation outputs: ~0.12 (Completely unrelated).
        
        When our script sees the score drop from 0.85 down to 0.12, it officially marks a topic cut!
        """
        dot_product = np.dot(vector_a, vector_b)
        norm_a = np.linalg.norm(vector_a)
        norm_b = np.linalg.norm(vector_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(dot_product / (norm_a * norm_b))


# ============================================================================
# MODULE 4: TOPIC MAPPING
# ============================================================================

class TopicBlockMapper:
    """Responsibility: Find major topic shifts and group sentences into cohesive blocks."""
    
    def __init__(self, similarity_drop_threshold: float = 0.25):
        # The threshold determines how severe a similarity drop must be to trigger a cut.
        # e.g., if Sentence A and B have 0.8 similarity, and B and C have 0.4, 
        # the drop is 0.4, which is > 0.25, so we cut!
        self.similarity_drop_threshold: float = similarity_drop_threshold
        
    def map_sentences_to_blocks(self, sentences: List[TranscribedSentence]) -> List[TopicBlock]:
        """Scans the video landscape and shatters it into isolated, cohesive thoughts."""
        print("Mapping semantic boundaries and generating Topic Blocks...")
        
        if not sentences:
            return []
            
        topic_blocks: List[TopicBlock] = []
        current_block_sentences: List[TranscribedSentence] = [sentences[0]]
        block_counter: int = 1
        
        for i in range(1, len(sentences)):
            previous_sentence = sentences[i-1]
            current_sentence = sentences[i]
            
            # Ensure both sentences have embeddings
            if previous_sentence.semantic_embedding is None or current_sentence.semantic_embedding is None:
                current_block_sentences.append(current_sentence)
                continue
                
            # Compare the meaning of the current sentence to the previous one
            similarity_score = SemanticAnalyzer.calculate_cosine_similarity(
                previous_sentence.semantic_embedding, 
                current_sentence.semantic_embedding
            )
            
            # In a real environment, we would look for "drops" (valleys) compared to a moving average.
            # For this MVP, we simply say: "If the absolute similarity is very low, they changed topics."
            # A score below 0.3 generally indicates completely unrelated subjects.
            is_major_topic_shift = similarity_score < 0.3
            
            if is_major_topic_shift:
                # We found a boundary! Lock in the current block and start a new one.
                finished_block = TopicBlock(
                    block_id=block_counter,
                    sentences=current_block_sentences,
                    start_time_seconds=current_block_sentences[0].start_time_seconds,
                    end_time_seconds=current_block_sentences[-1].end_time_seconds
                )
                topic_blocks.append(finished_block)
                
                block_counter += 1
                current_block_sentences = [current_sentence] # Start fresh
            else:
                # Still talking about the same thing, keep accumulating
                current_block_sentences.append(current_sentence)
                
        # Don't forget to save the very last block when the video ends!
        if current_block_sentences:
            final_block = TopicBlock(
                block_id=block_counter,
                sentences=current_block_sentences,
                start_time_seconds=current_block_sentences[0].start_time_seconds,
                end_time_seconds=current_block_sentences[-1].end_time_seconds
            )
            topic_blocks.append(final_block)
            
        print(f"Shattered video into {len(topic_blocks)} cohesive Topic Blocks.")
        
        # EXAMPLE OUTPUT OF THIS STEP:
        # [
        #   TopicBlock(
        #       block_id=1,
        #       sentences=[<TranscribedSentence>, <TranscribedSentence>],
        #       start_time_seconds=0.0,
        #       end_time_seconds=15.4
        #       # (Calculated Duration: 15.4s)
        #   ),
        #   ...
        # ]
        return topic_blocks


# ============================================================================
# MODULE 5: THE GOLD MINER (CLIP EXTRACTION)
# ============================================================================

class ClipExtractor:
    """Responsibility: Evaluate Topic Blocks and extract only the highest quality shorts."""
    
    def __init__(self, min_duration_sec: float = 30.0, max_duration_sec: float = 60.0):
        self.min_duration_sec: float = min_duration_sec
        self.max_duration_sec: float = max_duration_sec
        
    def extract_golden_clips(self, topic_blocks: List[TopicBlock]) -> List[ExtractedClip]:
        """Filters the dirt and extracts the gold."""
        print("Mining Topic Blocks for golden short-form clips...")
        
        extracted_clips: List[ExtractedClip] = []
        clip_counter: int = 1
        
        for block in topic_blocks:
            duration = block.duration_seconds
            
            # Scenario 1: The Garbage (Too Short)
            if duration < self.min_duration_sec:
                # We completely ignore it. It's likely dead air, a tangent, or a transition.
                continue
                
            # Scenario 2: The Golden Clip (Perfect Length)
            elif self.min_duration_sec <= duration <= self.max_duration_sec:
                clip = ExtractedClip(
                    clip_id=f"clip_{clip_counter}",
                    start_time_seconds=block.start_time_seconds,
                    end_time_seconds=block.end_time_seconds,
                    duration_seconds=duration,
                    text_transcript=block.full_transcript,
                    extraction_reasoning="Perfect Natural Fit (Topic bounded perfectly within 30-60s)"
                )
                extracted_clips.append(clip)
                clip_counter += 1
                
            # Scenario 3: The Rambler (Too Long)
            else:
                # The speaker dove deep into one topic for several minutes.
                # We extract the first 60 seconds (the "Hook" and core premise) and discard the rest.
                
                # Find the sentence that pushes us over the 60-second limit
                target_end_time = block.start_time_seconds + self.max_duration_sec
                actual_end_time = block.start_time_seconds
                rambler_sentences: List[str] = []
                
                for sentence in block.sentences:
                    if sentence.end_time_seconds > target_end_time:
                        break
                    actual_end_time = sentence.end_time_seconds
                    rambler_sentences.append(sentence.text_content)
                
                # If we managed to grab at least one sentence
                if rambler_sentences:
                    clip = ExtractedClip(
                        clip_id=f"clip_{clip_counter}",
                        start_time_seconds=block.start_time_seconds,
                        end_time_seconds=actual_end_time,
                        duration_seconds=(actual_end_time - block.start_time_seconds),
                        text_transcript=" ".join(rambler_sentences),
                        extraction_reasoning=f"Truncated Rambler (Original block was {duration:.1f}s, cut down to core hook)"
                    )
                    extracted_clips.append(clip)
                    clip_counter += 1
                    
        print(f"Successfully extracted {len(extracted_clips)} golden clips!")
        
        # EXAMPLE OUTPUT OF THIS STEP:
        # [
        #   ExtractedClip(
        #       clip_id="clip_1",
        #       start_time_seconds=15.4,
        #       end_time_seconds=60.4,
        #       duration_seconds=45.0,
        #       text_transcript="Here is why AI is the future... [full block text]",
        #       extraction_reasoning="Perfect Natural Fit (Topic bounded perfectly within 30-60s)"
        #   )
        # ]
        return extracted_clips


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_segmentation_pipeline() -> None:
    """The master function that wires all modules together."""
    
    current_directory: Path = Path(__file__).parent
    sample_video_path: Path = current_directory / "sample.mp4"
    audio_wav_path: Path = current_directory / "temp_audio.wav"
    output_json_path: Path = current_directory / "segmentation_recipe.json"
    
    if not sample_video_path.exists():
        print(f"Error: {sample_video_path.name} not found. Please provide a video to segment.")
        return
        
    # 1. Extract Audio
    success = AudioExtractor.extract_wav_from_mp4(sample_video_path, audio_wav_path)
    if not success:
        return
        
    try:
        # 2. Transcribe
        transcriber = TranscriptionEngine(model_size="base")
        sentences = transcriber.transcribe_audio_to_sentences(audio_wav_path)
        
        # 3. Analyze Semantics
        analyzer = SemanticAnalyzer(model_name="all-MiniLM-L6-v2")
        analyzer.embed_sentences(sentences)
        
        # 4. Map Boundaries
        mapper = TopicBlockMapper(similarity_drop_threshold=0.3)
        blocks = mapper.map_sentences_to_blocks(sentences)
        
        # 5. Extract Gold
        miner = ClipExtractor(min_duration_sec=30.0, max_duration_sec=60.0)
        golden_clips = miner.extract_golden_clips(blocks)
        
        # 6. Export Results
        print(f"Exporting results to {output_json_path.name}...")
        final_json_payload = {
            "video_id": "playground_test_video",
            "pipeline": "extraction_segmentation",
            "extracted_clips_count": len(golden_clips),
            "clips": [asdict(clip) for clip in golden_clips]
        }
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(final_json_payload, f, indent=4)
            
        print("\n======================================================================")
        print("SEGMENTATION SUCCESS!")
        print("======================================================================")
        
    finally:
        # Clean up the massive temporary WAV file
        if audio_wav_path.exists():
            audio_wav_path.unlink()
            print("Cleaned up temporary audio files.")


if __name__ == "__main__":
    run_segmentation_pipeline()
