name: Movies-Bollywood Update

on:
  schedule:
    - cron: '0 0,8,16 * * *'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: iptv-writes-bollywood  # Changed to avoid conflict
  cancel-in-progress: false

jobs:
  update-movies:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install requests pytz beautifulsoup4

      - name: Run Movies-Bollywood collector
        id: collector
        run: python collector/Movies-Bollywood.py
        continue-on-error: false

      - name: Commit and push output files
        if: success()
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git pull --rebase origin main || true
          
          # Only commit if files exist
          if [ -f "Movies/Bollywood/Movies.m3u" ]; then
            git add Movies/Bollywood/Movies.m3u Movies/Bollywood/Movies.json Movies/Bollywood/Movies_app.json
            git commit -m "🎬 Movies-Bollywood updated — $(date -u '+%Y-%m-%d %H:%M UTC')" || echo "No changes"
            git push origin main || (git pull --rebase origin main && git push origin main)
          else
            echo "No output files generated, skipping commit"
            exit 1
          fi

      - name: Send failure notification
        if: failure()
        run: |
          echo "Movies-Bollywood update failed!"
          exit 1
