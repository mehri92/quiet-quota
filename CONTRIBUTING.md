# Contributing

Please keep the app quiet, small and read-only. New features must not send prompts,
read credential files or automatically change a user's Codex configuration.

Run `python -m unittest discover -v`. UI tests use Qt's offscreen platform by default.
For a Windows bug, include OS/Python/Codex versions, monitor scaling and minimal
steps. Do not include account credentials, tokens or personal logs.

Translations live in `i18n.py`, with native language names in `LANGUAGES` and one
row per message. Keep placeholder names such as `{value}` and `{date}` unchanged.
Keep `weekly_used` short enough for a compact popup. Include all keys when adding a
language; tests compare message coverage and formatting placeholders.

Manual checks before release: live usage against the account's displayed quota,
a real automatic threshold crossing, restart without duplicate alerts, reset,
language persistence, mixed-DPI monitors, input focus, fullscreen and clean exit.
Mocked tests or demo screenshots must not be described as successful live checks.
