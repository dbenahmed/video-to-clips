"""
================================================================================
SERVICE: YouTube Video Downloader & Metadata Extractor
================================================================================
Purpose:
    This service is responsible for taking a raw YouTube video URL, validating it,
    downloading the best quality video and audio streams using the third-party
    library 'yt-dlp', merging them into a standard MP4 file using an isolated
    FFmpeg binary, and saving the resulting file into the server's uploads folder.

Design Principles Followed:
    - This file ONLY handles downloading
      and inspecting YouTube videos. It does not handle HTTP request parsing or
      database logic.
    - Descriptive Naming: All variable names are intentionally long and explicit
      to make the codebase crystal clear for clients and other developers.
================================================================================
"""

import uuid
from pathlib import Path
from fastapi import HTTPException
import yt_dlp

# Import our centralized storage directory and isolated FFmpeg binary location
from app.core.config import UPLOADS_DIR, FFMPEG_PATH
from app.schemas.video import YouTubeDownloadResponse


def download_from_youtube(raw_youtube_url_string: str) -> YouTubeDownloadResponse:
    """
    Downloads a video from YouTube given its public URL and saves it to local disk.

    Detailed Step-by-Step Breakdown:
    --------------------------------
    Step 1: Sanitize and validate that the incoming URL string is not empty.
    Step 2: Generate a collision-resistant unique identifier (UUID) for this video.
    Step 3: Define the exact disk file path template where the file will be saved.
    Step 4: Configure yt-dlp with explicit options (format, isolated FFmpeg, silent logging).
    Step 5: Execute the download and extract video metadata (title, duration in seconds).
    Step 6: Verify the physical file exists on disk, handling container format fallback.
    Step 7: Return a typed YouTubeDownloadResponse schema with public streaming URL.

    :param raw_youtube_url_string: The raw string containing the YouTube URL provided by the user.
    :return: A typed YouTubeDownloadResponse instance containing all video metadata.
    :raises HTTPException 400: If the URL is empty or metadata could not be fetched.
    :raises HTTPException 500: If network, disk, or merging errors occur during download.
    """

    # -------------------------------------------------------------------------
    # STEP 1: Input Sanitization & Empty Check
    # -------------------------------------------------------------------------
    # Remove leading and trailing whitespaces from the user's input string
    sanitized_youtube_url: str = raw_youtube_url_string.strip()

    # If the user submitted an empty string or just whitespace, reject it immediately
    if not sanitized_youtube_url:
        raise HTTPException(
            status_code=400,
            detail="The provided YouTube URL is empty. Please provide a valid link."
        )

    # -------------------------------------------------------------------------
    # STEP 2: Unique Identifier (UUID) Generation
    # -------------------------------------------------------------------------
    # We generate a unique UUID4 string (e.g., "e4d909c2-90c3-4d64-9b22-83b567d26456").
    # This guarantees that even if two users download the exact same YouTube video,
    # or videos with identical titles, they will never overwrite each other on the server.
    unique_video_identifier: str = str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # STEP 3: Define the Output File Naming Template
    # -------------------------------------------------------------------------
    # yt-dlp uses '%(ext)s' as a dynamic placeholder for the file extension
    # Example template result: "C:\...\backend\storage\uploads\e4d909c2...%(ext)s"
    output_disk_filename_template: str = str(UPLOADS_DIR / f"{unique_video_identifier}.%(ext)s")

    # -------------------------------------------------------------------------
    # STEP 4: Configure yt-dlp Execution Options
    # -------------------------------------------------------------------------
    # Detailed explanation of every configuration parameter passed to yt-dlp:
    youtube_dlp_configuration_options = {
        # 1. 'outtmpl': Where to save the downloaded file on the local hard drive
        "outtmpl": output_disk_filename_template,

        # 2. 'format': Format selection rule
        #    - 'bestvideo[ext=mp4]+bestaudio[ext=m4a]': Selects highest resolution H.264 video
        #      and highest quality AAC audio track.
        #    - '/best[ext=mp4]/best': Fallback to pre-merged streams if separate streams are unavailable.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",

        # 3. 'merge_output_format': The final container format to merge video and audio into
        "merge_output_format": "mp4",

        # 4. 'ffmpeg_location': Crucial configuration! Points to the isolated FFmpeg binary
        #    located inside the Python virtual environment (backend/venv). This avoids requiring
        #    a system-wide installation or touching Windows PATH.
        "ffmpeg_location": FFMPEG_PATH,

        # 5. 'noplaylist': Ensures that if a user pastes a playlist link, only the single video is fetched
        "noplaylist": True,

        # 6. 'quiet' & 'no_warnings': Suppresses noisy terminal progress lines so our server logs stay clean
        "quiet": True,
        "no_warnings": True,
    }

    # -------------------------------------------------------------------------
    # STEP 5: Execute Download and Extract Metadata
    # -------------------------------------------------------------------------
    try:
        # Open yt-dlp context manager with our custom configuration options
        with yt_dlp.YoutubeDL(youtube_dlp_configuration_options) as youtube_downloader_instance:

            # download=True tells yt-dlp to both extract metadata AND download the video file
            extracted_video_metadata_dictionary = youtube_downloader_instance.extract_info(
                sanitized_youtube_url,
                download=True
            )

            # If metadata extraction returned None, the video might be private, deleted, or geoblocked
            if not extracted_video_metadata_dictionary:
                raise HTTPException(
                    status_code=400,
                    detail="Could not retrieve metadata for this YouTube video. It may be private or restricted."
                )

            # -----------------------------------------------------------------
            # STEP 6: Determine Final Filename and Verify Disk File Path
            # -----------------------------------------------------------------
            # Determine the file extension reported by yt-dlp (typically 'mp4')
            downloaded_file_extension: str = extracted_video_metadata_dictionary.get("ext") or "mp4"
            final_saved_disk_filename: str = f"{unique_video_identifier}.{downloaded_file_extension}"
            target_file_path_on_disk: Path = UPLOADS_DIR / final_saved_disk_filename

            # Fallback verification: Sometimes yt-dlp merges into an .mp4 container even if 'ext' reported 'mkv'
            if not target_file_path_on_disk.exists():
                fallback_mp4_disk_path: Path = UPLOADS_DIR / f"{unique_video_identifier}.mp4"
                if fallback_mp4_disk_path.exists():
                    final_saved_disk_filename = f"{unique_video_identifier}.mp4"
                    target_file_path_on_disk = fallback_mp4_disk_path

            # Extract user-friendly metadata values with sensible defaults
            video_title_string: str = extracted_video_metadata_dictionary.get("title") or "YouTube Video"
            video_duration_in_seconds: int = int(extracted_video_metadata_dictionary.get("duration") or 0)

            # -----------------------------------------------------------------
            # STEP 7: Return Standardized Typed Response
            # -----------------------------------------------------------------
            # Construct the relative URL used by the React frontend to stream the video
            # (e.g. "/storage/uploads/e4d909c2...mp4")
            frontend_streaming_relative_url: str = f"/storage/uploads/{final_saved_disk_filename}"

            return YouTubeDownloadResponse(
                status="success",
                id=unique_video_identifier,
                title=video_title_string,
                duration_seconds=video_duration_in_seconds,
                saved_filename=final_saved_disk_filename,
                url=frontend_streaming_relative_url,
            )

    except HTTPException:
        # Re-raise explicit HTTP errors as-is without wrapping them in 500
        raise

    except Exception as general_download_operation_error:
        # Catch unexpected errors (network drops, invalid links, yt-dlp parser exceptions)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download YouTube video: {str(general_download_operation_error)}"
        )


# Backward compatibility function alias
download_youtube_video = download_from_youtube
