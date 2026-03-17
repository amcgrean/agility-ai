# Agility AI UI

React + Vite + Tailwind frontend for an Agility private assistant backed by FastAPI.

## Features

- ChatGPT-style chat layout with collapsible sidebar
- Conversation management (new, rename, delete)
- Backend-powered Q&A via `POST /ask`
- Streaming-like response rendering
- Markdown + syntax highlighting + copy buttons for code blocks
- Conversation persistence through backend endpoints (`/conversations`, `/messages`) with local fallback stubs
- Shareable read-only conversation route (`/share/:conversation_id`)
- PDF export for the active conversation
- Dark / light mode support

## Backend assumptions

Default backend URL: `http://localhost:8000`

Endpoints used:
- `POST /ask`
- `GET/POST/PATCH/DELETE /conversations` (stub fallback to local storage)
- `POST /messages` (stub fallback to local storage)

Set `VITE_API_URL` to override the backend URL.

## Development

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
```

Output directory: `dist/`

You can copy the static build into:

`/home/amcgrean/agility-ai/ui`

and serve it from FastAPI/static hosting.

## Future-ready architecture

The app is organized by `components`, `hooks`, `pages`, and `services` to make future additions straightforward:

- citations for doc sources
- screenshot uploads
- voice input
- multi-model switching
- admin dashboard
