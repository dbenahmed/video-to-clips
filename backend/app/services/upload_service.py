"""
================================================================================
SERVICE: Direct Local Video File Upload & Storage Persistence
================================================================================
Purpose:
    This service handles the business logic for receiving direct multipart video
    file uploads from the user's browser, validating the file format, preventing
    naming collisions with UUIDs, streaming the binary data to disk in small
    memory-safe chunks, and calculating the final file size.

Design Principles Followed:
    - This service ONLY manages the
      validation and persistence of directly uploaded video files.
    - Memory Safety (Zero RAM Spikes): Uses stream copying (shutil.copyfileobj)
      so that multi-gigabyte video uploads do not crash server memory.
    - Self-Documenting Naming: All variable names are intentionally explicit and
      descriptive to make the architecture transparent and easy to maintain.
================================================================================
"""

import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Import our centralized storage directory and allowed format constraints
from app.core.config import UPLOADS_DIR, ALLOWED_VIDEO_EXTENSIONS
from app.schemas.video import VideoUploadResponse


def save_uploaded_video(incoming_uploaded_file: UploadFile) -> VideoUploadResponse:
    """
    Validates, sanitizes, and persists an uploaded video file to local server storage.

    Detailed Step-by-Step Breakdown:
    --------------------------------
    Step 1: Extract and validate the file extension against ALLOWED_VIDEO_EXTENSIONS.
    Step 2: Generate a collision-resistant unique identifier (UUID) for this upload.
    Step 3: Sanitize the original filename by stripping directory traversals and spaces.
    Step 4: Combine the UUID and sanitized name into a safe destination filename on disk.
    Step 5: Stream the binary data to disk in buffer chunks to protect server memory.
    Step 6: Handle error cleanup (deleting partial files if the upload is aborted).
    Step 7: Calculate the final size in bytes and return a typed VideoUploadResponse model.

    :param incoming_uploaded_file: The FastAPI UploadFile object containing the uploaded binary stream.
    :return: A typed VideoUploadResponse containing the unique ID, path, and streaming URL.
    :raises HTTPException 400: If the uploaded file extension is not in ALLOWED_VIDEO_EXTENSIONS.
    :raises HTTPException 500: If an error occurs while writing the binary data to disk.
    """

    # -------------------------------------------------------------------------
    # STEP 1: Extract and Validate File Extension
    # -------------------------------------------------------------------------
    # Extract the file extension (e.g., '.mp4', '.mov') and convert it to lowercase
    # so that extensions like '.MP4' or '.Mov' are handled correctly.
    uploaded_file_extension: str = Path(incoming_uploaded_file.filename or "").suffix.lower()

    # Check if the extracted extension exists within our allowed whitelist
    if uploaded_file_extension not in ALLOWED_VIDEO_EXTENSIONS:
        # Create a readable string list of allowed extensions (e.g., ".avi, .mkv, .mov, .mp4, .webm")
        allowed_extensions_comma_separated_string: str = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file format '{uploaded_file_extension}'. "
                f"Allowed formats are: {allowed_extensions_comma_separated_string}"
            ),
        )

    # -------------------------------------------------------------------------
    # STEP 2: Generate a Collision-Resistant Unique Identifier (UUID)
    # -------------------------------------------------------------------------
    # A random UUID4 string (e.g., "7f8b9c1a-2d3e-4f5a-6b7c-8d9e0f1a2b3c").
    # This ensures that even if ten different users upload files named "video.mp4",
    # every single upload gets a unique namespace and will never overwrite existing files.
    unique_upload_identifier: str = str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # STEP 3: Sanitize the Original Filename
    # -------------------------------------------------------------------------
    # Path().name ensures any dangerous path traversal characters (like ../ or C:\) are removed.
    # We also replace spaces with underscores to ensure clean, browser-safe URLs.
    raw_original_filename: str = incoming_uploaded_file.filename or "uploaded_video"
    sanitized_original_filename: str = Path(raw_original_filename).name.replace(" ", "_")

    # -------------------------------------------------------------------------
    # STEP 4: Build Destination Filename and Absolute File Path on Disk
    # -------------------------------------------------------------------------
    # Combine the unique identifier with the sanitized filename
    # Example: "7f8b9c1a-2d3e..._podcast_episode_1.mp4"
    unique_destination_filename_on_disk: str = f"{unique_upload_identifier}_{sanitized_original_filename}"

    # Build the full absolute filesystem path inside backend/storage/uploads/
    absolute_destination_file_path: Path = UPLOADS_DIR / unique_destination_filename_on_disk

    # -------------------------------------------------------------------------
    # STEP 5: Stream Binary Data to Disk in Memory-Safe Chunks
    # -------------------------------------------------------------------------
    # CRITICAL ARCHITECTURE NOTE:
    # Instead of doing `incoming_uploaded_file.file.read()`, which loads the ENTIRE
    # multi-gigabyte video into the server's RAM at once and can crash the machine,
    # `shutil.copyfileobj` reads and writes in small buffer chunks (typically 64KB).
    try:
        with open(absolute_destination_file_path, "wb") as disk_binary_write_buffer:
            shutil.copyfileobj(incoming_uploaded_file.file, disk_binary_write_buffer)

    except Exception as file_writing_exception:
        # STEP 6: Clean up partial or corrupted files if disk writing fails
        if absolute_destination_file_path.exists():
            absolute_destination_file_path.unlink()  # Deletes the incomplete file from disk

        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving the video file to storage: {str(file_writing_exception)}"
        )

    finally:
        # Always close the underlying temporary file handle to free operating system resources
        incoming_uploaded_file.file.close()

    # -------------------------------------------------------------------------
    # STEP 7: Measure File Size and Return Typed Response
    # -------------------------------------------------------------------------
    # Query the operating system for the exact file size on disk in bytes
    total_saved_file_size_in_bytes: int = absolute_destination_file_path.stat().st_size

    # The relative URL that our mounted FastAPI static files route exposes
    # (e.g., "/storage/uploads/7f8b9c1a..._video.mp4")
    frontend_video_streaming_relative_url: str = f"/storage/uploads/{unique_destination_filename_on_disk}"

    # Return the standardized, typed Pydantic response schema
    return VideoUploadResponse(
        status="success",
        id=unique_upload_identifier,
        original_name=incoming_uploaded_file.filename or "unknown",
        saved_filename=unique_destination_filename_on_disk,
        url=frontend_video_streaming_relative_url,
        size_bytes=total_saved_file_size_in_bytes,
    )
