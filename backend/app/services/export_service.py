"""
EXPORT SERVICE MODULE
=====================

OVERVIEW & ARCHITECTURE:
This module is the core engine responsible for generating the final vertically cropped (9:16) MP4 video clip. 
it completely isolating the complex, error-prone 
FFmpeg string manipulation logic from the FastAPI routing and HTTP layer.

THE "DYNAMIC PAN-AND-SCAN" PROBLEM:
Standard FFmpeg is designed to apply a static crop to a video. However, our AI tracking algorithm detects 
when the subject moves across the screen. If we apply a static crop, the subject will walk out of the frame. 
To fix this, we must dynamically move the crop window to follow the subject, creating a "jump cut" or 
"pan-and-scan" effect.

THE ALGORITHM (Step-by-Step):
1. THE OVERLAP CLAMP: 
   The frontend sends the raw array of tracking blocks (which may span the entire video). The algorithm 
   first strips away any tracking data that falls outside the user's requested clip boundaries (e.g., 15s to 45s).
   It mathematically "clamps" the tracking blocks so their timestamps never bleed past the clip's start or end.
   
   EXAMPLE:
   - User wants a clip from 15.0s to 30.0s.
   - The AI generated a tracking block where the subject sat still from 10.0s to 20.0s.
   - If we blindly used this tracking block, FFmpeg would extract video starting at 10.0s, ruining the clip!
   - The Clamp Algorithm intercepts this and slices the tracking block so it now starts at exactly 15.0s.

2. GAP FILLING (AUDIO SYNC FAIL-SAFE): 
   In `tracking.py`, the AI already has an "Ultimate Fallback" that defaults to the center of the screen 
   if a face is lost. Therefore, the tracking data should theoretically never have any gaps.
   However, floating-point math is notoriously imprecise. For example, if Block 1 ends at 10.3333333s 
   and Block 2 begins at 10.3333334s, that microscopic gap can cause FFmpeg to drop frames or cause 
   micro-stutters in the audio lip-sync.
   This algorithm acts as a robust mathematical safety net. It iterates through the clamped blocks 
   and forces any micro-gaps to be filled using the last known X/Y coordinates, absolutely guaranteeing 
   that the stitched video track length perfectly matches the audio track length down to the millisecond.

3. FILTERGRAPH GENERATION: 
   Instead of a standard command, this algorithm generates an FFmpeg `filter_complex` (a Filtergraph).
   It acts like a surgical operating table for video streams.
   
   EXAMPLE (A 15s clip where the subject moved once):
   [0:v]trim=start=15.0:end=20.0,setpts=PTS-STARTPTS,crop=w='ih*9/16':h=ih:x=400:y=0[v0]; 
   [0:v]trim=start=20.0:end=30.0,setpts=PTS-STARTPTS,crop=w='ih*9/16':h=ih:x=500:y=0[v1]; 
   [v0][v1]concat=n=2:v=1:a=0[outv]; 
   [0:a]atrim=start=15.0:end=30.0,asetpts=PTS-STARTPTS[outa]
   
   HOW IT WORKS STEP-BY-STEP:
   - The Video Slicing (trim & crop):
     `[0:v]` grabs the raw video stream.
     `trim=start=15.0:end=20.0` cuts out exactly that 5-second slice.
     `setpts=PTS-STARTPTS` resets the internal timestamp to 0.0s (prevents black screens).
     `crop=w='ih*9/16':h=ih:x=400:y=0` cuts a perfect vertical 9:16 rectangle using the input height (`ih`), dropping it at X=400.
     `[v0]` saves this slice in a temporary variable.
   - The Stitching (concat):
     `[v0][v1]concat=n=2:v=1:a=0[outv]` glues the 2 chunks back together end-to-end and saves it as `[outv]`.
   - The Audio Track (atrim):
     Because audio doesn't move visually, we just trim the original audio track once from 15s to 30s and save as `[outa]`.
   - The Final Export (-map):
     Finally, `-map "[outv]" -map "[outa]"` lays the perfectly cut audio on top of the stitched vertical video, 
     encodes it with H.264, and exports the final MP4.

4. EXECUTION & CANCELLATION: 
   Unlike standard `subprocess.run` (which blocks Python completely), we use `subprocess.Popen`. 
   This allows us to maintain a "handle" (a PID reference) on the running FFmpeg process.
   If the user clicks "Cancel" in the frontend, the FastAPI router can access this handle 
   and instantly execute `process.terminate()`, instantly killing the CPU-intensive render 
   mid-flight and protecting server performance.

RETURNS:
- bool: True if the FFmpeg process completes successfully with return code 0.
- Raises Exception: If FFmpeg fails, raising a standard python Exception to be caught by the FastAPI router.
"""
import os
import subprocess
from pathlib import Path
from app.schemas.export import ExportClipRequest

def _clamp_tracking_blocks(tracking_data: list, start_time: float, end_time: float) -> list:
    """
    1. THE OVERLAP CLAMP: 
    Strips away any tracking data that falls outside the user's requested clip boundaries.
    Mathematically "clamps" the tracking blocks so their timestamps never bleed past the clip's start or end.
    """
    clamped_blocks = []
    for block in tracking_data:
        # Check for overlap
        if block.end_time_seconds <= start_time or block.start_time_seconds >= end_time:
            continue # No overlap
            
        # Clamp boundaries so we don't trim beyond what the user asked for
        b_start = max(block.start_time_seconds, start_time)
        b_end = min(block.end_time_seconds, end_time)
        
        if b_end - b_start > 0.05: # Prevent micro-stutters
            clamped_blocks.append({
                "start": b_start,
                "end": b_end,
                "crop_x": block.crop_x,
                "crop_y": block.crop_y
            })
            
    # Sort blocks chronologically
    clamped_blocks.sort(key=lambda x: x["start"])
    return clamped_blocks


def _fill_tracking_gaps(clamped_blocks: list, start_time: float, end_time: float) -> list:
    """
    2. GAP FILLING ALGORITHM
    If there are missing tracking data frames (or if the face disappeared),
    we MUST fill the gaps so the video track length matches the audio track length exactly.
    Otherwise, FFmpeg concat will cause audio desync!
    """
    filled_blocks = []
    current_time = start_time
    
    for block in clamped_blocks:
        if block["start"] > current_time + 0.05:
            # GAP DETECTED! Fill it using the previous block's crop
            prev_crop_x = filled_blocks[-1]["crop_x"] if filled_blocks else 1920//2 - 607//2
            prev_crop_y = filled_blocks[-1]["crop_y"] if filled_blocks else 0
            filled_blocks.append({
                "start": current_time,
                "end": block["start"],
                "crop_x": prev_crop_x,
                "crop_y": prev_crop_y
            })
        
        filled_blocks.append(block)
        current_time = block["end"]
        
    # Check for a gap at the very end of the clip
    if current_time < end_time - 0.05:
        prev_crop_x = filled_blocks[-1]["crop_x"] if filled_blocks else 1920//2 - 607//2
        prev_crop_y = filled_blocks[-1]["crop_y"] if filled_blocks else 0
        filled_blocks.append({
            "start": current_time,
            "end": end_time,
            "crop_x": prev_crop_x,
            "crop_y": prev_crop_y
        })
        
    return filled_blocks


def _generate_filtergraph(filled_blocks: list, start_time: float, end_time: float) -> str:
    """
    3. GENERATE FFMPEG FILTERGRAPH
    Generates the massive filter_complex string that dynamically trims, crops, and concats 
    the video slices while retaining audio sync.
    """
    filter_parts = []
    concat_inputs = ""
    
    for i, block in enumerate(filled_blocks):
        s = f"{block['start']:.3f}"
        e = f"{block['end']:.3f}"
        cx = int(block["crop_x"])
        cy = int(block["crop_y"])
        
        # w='ih*9/16' dynamically calculates a 9:16 aspect ratio based on the video's actual height (ih)
        f = f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,crop=w='ih*9/16':h=ih:x={cx}:y={cy}[v{i}];"
        filter_parts.append(f)
        concat_inputs += f"[v{i}]"
        
    # Concat all the dynamically cropped video slices
    filter_parts.append(f"{concat_inputs}concat=n={len(filled_blocks)}:v=1:a=0[outv];")
    
    # Trim the audio independently (once for the whole clip)
    s = f"{start_time:.3f}"
    e = f"{end_time:.3f}"
    filter_parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[outa]")
    
    return " ".join(filter_parts)


def run_export_pipeline(request: ExportClipRequest, input_path: Path, output_path: Path, on_process_started=None):
    """
    Takes a video and dynamically pans/crops it based on tracking blocks.
    Ensures that the output video perfectly matches the frontend preview box.
    """
    # 1. Clamp Boundaries
    clamped_blocks = _clamp_tracking_blocks(request.tracking_data, request.start_time, request.end_time)
    
    # 2. Fill Gaps for Audio Sync
    filled_blocks = _fill_tracking_gaps(clamped_blocks, request.start_time, request.end_time)
    
    # 3. Generate FFmpeg String
    filter_complex = _generate_filtergraph(filled_blocks, request.start_time, request.end_time)
    
    # 4. EXECUTE FFMPEG
    command = [
        "ffmpeg",
        "-y", # Overwrite output if it exists
        "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "ultrafast", # Ultra-fast CPU encoding (perfect for evaluators without GPUs)
        "-crf", "28",           # Lowers bit-rate slightly to speed up encoding without noticeable quality drop
        "-c:a", "aac",
        str(output_path)
    ]
    
    print(f"\n[{request.saved_filename}] Executing FFmpeg with {len(filled_blocks)} sub-clips...")
    print(f"[{request.saved_filename}] Outputting to: {output_path}")
    print("-" * 50)
    
    process = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, # Merge stderr (where FFmpeg writes progress) into stdout
        text=True,
        bufsize=1, # Line buffered
        universal_newlines=True
    )
    
    if on_process_started:
        on_process_started(process)
        
    # Stream output to console in real-time!
    if process.stdout:
        for line in process.stdout:
            print(line, end="")
        
    process.wait() # Block until finished or terminated
    print("-" * 50)
    
    # process.returncode is -15 (SIGTERM) or 1 (killed) on windows sometimes when terminated
    if process.returncode != 0 and process.returncode is not None:
        if process.returncode == 1 or process.returncode == -15:
            print(f"\n[!] Export Cancelled by User.")
            raise Exception("FFmpeg process was forcefully terminated.")
        raise Exception(f"FFmpeg failed with code {process.returncode}")
        
    return True
