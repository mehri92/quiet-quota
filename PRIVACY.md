# Privacy and local storage

Quiet Quota's own code has no telemetry, analytics, advertising or remote logging.
It starts a local Codex app-server over stdin/stdout and calls `initialize`,
`account/read` and `account/rateLimits/read`. It sends no chat messages, creates
no threads and performs no model inference. Unexpected server-initiated requests
are rejected. Codex itself connects to its service under its own settings/policies.

Quiet Quota does not read browser cookies or Codex credential files. Your existing
Codex CLI manages its own authentication. Keep it signed in to the intended account.

Local files under `%LOCALAPPDATA%\QuietQuota` contain settings, notification history
and a single-instance lock. History uses a hash of the returned account metadata;
it does not store that metadata in plain text. Hashes are identifiers, not a promise
of anonymity. The running process receives account data in memory to identify the
current quota state. Raw RPC errors and authentication data are not logged by the app.

Quitting terminates only the dedicated app-server process tree started by Quiet
Quota. Pausing notifications does not stop polling. No Windows auto-start entry
is created automatically. To remove the app, quit it, remove any shortcuts you
created, and delete its application folder. Remove the local data folder too if
you want to erase settings/history. This does not remove your independent Codex CLI.

Before reporting a problem, redact your account details and local paths. Never
attach auth.json, API keys, tokens, cookies or complete Codex logs to a public issue.
