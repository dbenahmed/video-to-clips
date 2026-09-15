# 01 - The Genesis of the Decoupled Tracking Architecture

## The Origin of the Problem
When designing the "Brain" of the Video-to-Clips application, the initial approach was standard: the backend would analyze the video, generate 30-second clips, track the subjects *within* those 30 seconds, and send the final packaged clips to the frontend.

However, during the architectural planning phase, the lead developer identified several critical edge cases that would break this standard approach:
1. **The Extension Problem:** If the frontend only receives tracking data for a strict 30-second window, what happens if the user drags the timeline slider to extend the clip to 45 seconds? The frontend would crash or lose tracking because the extra 15 seconds of tracking data simply didn't exist.
2. **The Multiple Subjects Problem:** What happens if the crop center needs to change dynamically mid-clip because two different people are talking?
3. **The Manual Override Problem:** What if the user disagrees with the AI and wants to manually change the subject position? 

## The Breakthrough: Decoupling Boundaries from Tracking
To solve these edge cases, a brilliant architectural decision was made: **We must completely decouple the Clip Boundaries from the Tracking Data.**

Instead of tying tracking data to specific clips, the backend runs a global analysis step when the video is first uploaded. It creates a master map of the entire video.
- **The Segmenter** proposes the logical start and end times for the clips.
- **The Global Tracker** scans the entire video from start to finish and maps out the X and Y crop coordinates regardless of where the clips begin or end.

By delivering both of these data structures independently to the frontend, the user gains infinite flexibility. If they extend a clip, the frontend simply looks up the new timestamps in the Global Tracking Map. The data is always there.

## Optimization 1: Time Range Compression
Scanning a 10-minute video frame-by-frame generates a massive array of coordinates, which would bloat the JSON payload and slow down the API. 
The developer solved this by introducing **Ranged Timestamps**. Instead of sending an object for every single second, the backend compresses the data into ranges. If the subject sits still for 15 seconds, it is represented as a single block:
```json
"global_tracking": [
  {"start_time": 0.0, "end_time": 14.5, "center_x": 960, "center_y": 540},
  {"start_time": 14.5, "end_time": 18.2, "center_x": 1200, "center_y": 540}
]
```

## Optimization 2: Zero-CPU Frontend Preview
The second major concern was browser performance. Forcing React to mathematically calculate and crop a `<video>` element live while interpolating coordinates would cause severe lag.

Because the data is compressed into Time Ranges, a highly efficient **CSS Overlay Alternative** was chosen:
1. The frontend plays the standard horizontal (16:9) video.
2. It draws a glowing 9:16 CSS rectangle *on top* of the video player.
3. As the video plays, the browser checks the `currentTime`. If the time falls within the 14.5s to 18.2s range, the frontend simply applies a CSS rule: `transform: translateX(1200px)`.

Because the box jumps from range to range using hardware-accelerated CSS, the frontend requires zero CPU math. The user gets a lightning-fast, zero-lag editing experience.

## The Final Workflow
1. **Phase 1 (Backend Initialization):** The video is uploaded. The backend generates the Clip Boundaries and the compressed Global Tracking Map.
2. **Phase 2 (Frontend Editor):** The user receives the data. They use an interactive timeline slider to extend, shorten, or move clips. The CSS crop box smoothly follows the subject based on the global map.
3. **Phase 3 (Backend Rendering):** The user clicks "Export". The frontend sends the *final* timestamps back to the backend. The backend's FFmpeg binary physically slices and crops the high-res video exactly as the user previewed it.
