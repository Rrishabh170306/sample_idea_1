# Phase-1 Flow Contract (Frontend)

## Scope
Phase-1 builds a chatbot-first skeleton only:

1. `Home` intro + chatbot style preview
2. `Auth` screen with Google OAuth2 placeholder
3. `Profile Setup` placeholder with required field list
4. `Chat` placeholder with composer-level upload affordance

No backend or RAG pipeline code changes are included.

## Locked Flow
`/` -> `/auth` -> `/profile` -> `/chat`

## Data Contract (To wire in Phase-2)
- Auth identity from Google OAuth2 (email-based)
- Profile inputs:
  - full_name
  - dob
  - address
  - city
  - pin_code
  - income
  - locale_background (rural|urban)
  - education_background
- Chat input:
  - `message_text`
  - optional `files[]` (pdf, docx, jpg)
  - optional `language`
  - optional `voice_enabled`

## UI Principles
- Keep layout minimal and centered around chatbot interaction.
- Keep intro concise and trust-focused.
- Treat document upload as a chat composer action, not a separate module.
- Preserve room for citation and confidence indicators in later phases.

## Out of Scope in Phase-1
- Real OAuth2 callback handling
- Live LLM/RAG response streaming
- File upload API integration
- Translation and voice implementation
