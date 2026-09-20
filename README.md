# Tiny Links

A deliberately small self-hosted bookmark organizer.

## v3

- Dark UI by default
- Subtle Matrix-style green accent
- Folder explorer on the left
- Links appear directly underneath their containing folder in the explorer
- Clicking a link opens it in a new browser tab
- Clicking a folder navigates to that folder
- Nested folders
- SQLite database
- Single password
- No trackers, thumbnails, page archiving, tags, or external services
- Works in any browser
- One Docker container

## Run

Edit `docker-compose.yml` and change `APP_PASSWORD` and `SECRET_KEY`.

```bash
docker compose up -d --build
```

Open `http://YOUR-SERVER:8080`.

## Updating later

The application is intentionally simple. Keep these files somewhere safe (or put the project in a private Git repository):

- `app.py` — application/backend
- `templates/` — HTML
- `static/style.css` — appearance
- `Dockerfile` and `docker-compose.yml` — deployment
- `data/links.db` — **your actual bookmarks**

When updating the application, replace the code/templates/static files and rebuild the container. Keep `data/links.db`.

```bash
docker compose up -d --build
```

Your database is mounted separately, so rebuilding the application does not erase it.

## Backup

Back up `data/links.db`. It contains the complete folder/link tree.

## If you come back to ChatGPT later

You do not need this conversation. Upload the project ZIP (or the project files) and say what you want changed. The README describes the architecture and update process.

For long-term reliability, a private Git repository is even better: commit each version so you can roll back if an update breaks something.


## v4 UI

- Dark mode with subtle Matrix-green accents
- Folder tree can expand/collapse individually
- Links are shown underneath their folders in the tree
- Expand/collapse-all control in the sidebar
- Neutral light-grey link text instead of browser-style blue
