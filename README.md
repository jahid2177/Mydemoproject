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
