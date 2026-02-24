# Characters

Each subfolder is a character duo. Add new pairs by creating a folder with:

```
characters/
├── peter_stewie/
│   ├── config.json      ← Voice IDs, colors, positions
│   ├── char1.png        ← First character image
│   └── char2.png        ← Second character image
├── babar_virat/
│   ├── config.json
│   ├── char1.png
│   └── char2.png
└── diddy_charlie/
    ├── config.json
    ├── char1.png
    └── char2.png
```

## config.json format

```json
{
  "duo_name": "peter_stewie",
  "char1": {
    "name": "peter",
    "display_name": "Peter Griffin",
    "voice_id": "d75c270eaee14c8aa1e9e980cc37cf1b",
    "image": "char1.png",
    "subtitle_color": "&H00FFFF",
    "position": {"x": 50, "y": 1350}
  },
  "char2": {
    "name": "stewie",
    "display_name": "Stewie Griffin",
    "voice_id": "e91c4f5974f149478a35affe820d02ac",
    "image": "char2.png",
    "subtitle_color": "&H5050FF",
    "position": {"x": 700, "y": 1350}
  }
}
```

## Finding Voice IDs

1. Go to https://fish.audio
2. Search for the character/person
3. Copy the ID from the URL (e.g., `fish.audio/m/VOICE_ID_HERE/`)
