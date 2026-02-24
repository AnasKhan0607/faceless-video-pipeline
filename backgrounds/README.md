# Backgrounds

Gameplay footage for video backgrounds. Each file should be:
- **Resolution:** 720p or 1080p vertical (or will be cropped)
- **Format:** MP4 (H.264)
- **Length:** 2+ minutes (will loop if needed)
- **Audio:** Not needed (will be replaced)

```
backgrounds/
├── subway_surfers.mp4     ← Default
├── minecraft_parkour.mp4
├── gta_driving.mp4
├── temple_run.mp4
├── satisfying_slime.mp4
└── cooking_asmr.mp4
```

## Adding New Backgrounds

1. Download gameplay footage (YouTube, screen record, etc.)
2. Convert to proper format:
   ```bash
   ffmpeg -i input.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -r 30 -c:v libx264 -preset fast -crf 23 -an backgrounds/new_game.mp4
   ```
3. Or just drop the file here and the pipeline will handle it

## Where to Find Footage

- YouTube: Search "[game] gameplay no commentary"
- Record yourself playing
- Stock footage sites
