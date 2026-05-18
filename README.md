# 🎬 Mydemoproject — Movie M3U & JSON Collector

**GitHub:** [jahid2177/Mydemoproject](https://github.com/jahid2177/Mydemoproject)

Auto-collect করা Movies playlist — দিনে **৩ বার** GitHub Actions এর মাধ্যমে update হয়।

---

## 📂 Project Structure

```
Mydemoproject/
├── collector/
│   ├── Movies-Bollywood.py
│   ├── Movies-Hollywood.py
│   ├── Movies-Bengali.py
│   ├── Movies-SouthIndian.py
│   └── Movies-WorldwideVOD.py
├── Movies/
│   ├── Bollywood/
│   │   ├── Movies.m3u          ← M3U playlist
│   │   ├── Movies.json         ← Full JSON (date + channels)
│   │   └── Movies_app.json     ← Flat JSON (Android app এর জন্য)
│   ├── Hollywood/
│   ├── Bengali/
│   ├── SouthIndian/
│   └── WorldwideVOD/
├── .github/workflows/
│   ├── Movies-Bollywood.yml
│   ├── Movies-Hollywood.yml
│   ├── Movies-Bengali.yml
│   ├── Movies-SouthIndian.yml
│   └── Movies-WorldwideVOD.yml
└── logo/
    └── default-logo.png
```

---

## 🔗 Direct File URLs (Android App এ use করুন)

### Bollywood
```
M3U:  https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies.m3u
JSON: https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bollywood/Movies_app.json
```

### Hollywood
```
M3U:  https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies.m3u
JSON: https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Hollywood/Movies_app.json
```

### Bengali (BD)
```
M3U:  https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies.m3u
JSON: https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/Bengali/Movies_app.json
```

### South Indian
```
M3U:  https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies.m3u
JSON: https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/SouthIndian/Movies_app.json
```

### Worldwide VOD
```
M3U:  https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies.m3u
JSON: https://raw.githubusercontent.com/jahid2177/Mydemoproject/main/Movies/WorldwideVOD/Movies_app.json
```

---

## 📱 Android App এ JSON ব্যবহার

`Movies_app.json` এর format:
```json
[
  {
    "name": "Movie Title",
    "category": "Bollywood",
    "url": "https://stream.example.com/movie.m3u8",
    "logo": "https://example.com/logo.png"
  }
]
```

Retrofit দিয়ে fetch করুন:
```kotlin
// Retrofit interface
@GET("Movies/Bollywood/Movies_app.json")
suspend fun getBollywoodMovies(): List<MovieItem>
```

---

## ⏰ Auto Update Schedule

| Category     | Schedule (UTC)        |
|--------------|-----------------------|
| Bollywood    | 00:00 · 08:00 · 16:00 |
| Hollywood    | 00:00 · 08:00 · 16:00 |
| Bengali      | 00:00 · 08:00 · 16:00 |
| SouthIndian  | 00:00 · 08:00 · 16:00 |
| WorldwideVOD | 00:00 · 08:00 · 16:00 |

---

## 🚀 Setup করুন

1. এই সব file আপনার `jahid2177/Mydemoproject` repo-তে push করুন
2. GitHub → Settings → Actions → General → **Allow all actions** enable করুন
3. প্রথমবার manual run: Actions tab → যেকোনো workflow → **Run workflow**
4. এরপর প্রতিদিন auto-update হবে ✅
