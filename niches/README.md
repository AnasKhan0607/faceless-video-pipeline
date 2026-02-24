# Niches

Each niche has its own folder with:
- Topic list (100 topics)
- Preferred character duos
- Upload accounts
- Hashtag sets

```
niches/
├── tech/
│   ├── config.json       ← Accounts, duos, hashtags
│   └── topics.json       ← 100 topic ideas
├── cricket/
│   ├── config.json
│   └── topics.json
└── finance/
    ├── config.json
    └── topics.json
```

## config.json format

```json
{
  "niche": "tech",
  "name": "Tech Explainers",
  "character_duos": ["peter_stewie", "babar_virat"],
  "default_background": "subway_surfers.mp4",
  "accounts": {
    "tiktok": "@cooked_cs_kid",
    "youtube": "@cookedcskid",
    "instagram": "@cookedcskid"
  },
  "hashtags": {
    "tiktok": "#coding #programming #tech #developer #learntocode",
    "youtube": "#shorts #coding #programming #tech",
    "instagram": "#coding #programming #tech #developer #coder"
  }
}
```

## topics.json format

```json
{
  "niche": "tech",
  "topics": [
    {"id": 1, "topic": "What is an API", "used": true},
    {"id": 2, "topic": "What is recursion", "used": false},
    {"id": 3, "topic": "What is a database", "used": false}
  ]
}
```
