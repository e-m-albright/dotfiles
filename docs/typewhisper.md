# TypeWhisper

TypeWhisper provides local system-wide dictation. The tracked host configuration keeps Apple SpeechAnalyzer selected, enables deterministic filler-word removal and automatic correction learning, and leaves Parakeet disabled.

## Supported automation

Prefer TypeWhisper's supported interfaces for routine work:

- Use the `typewhisper` CLI for status, model inspection, and file transcription.
- Use the loopback HTTP API for documented operations that the installed CLI does not expose.
- Use the TypeWhisper interface for settings without a documented API endpoint.

The tracked offline reconciler under `macos/typewhisper/` remains the fresh-Mac and recovery path. It applies preferences, workflows, dictionary state, and snippets while TypeWhisper is stopped. Do not edit TypeWhisper's SQLite stores ad hoc while the application is running.

## First-time setup

1. Install and launch TypeWhisper.
2. Grant Microphone and Accessibility permissions when macOS prompts.
3. Open **Settings > Advanced**.
4. Enable **API Server**.
5. Enable **Require API Token**.
6. Under **CLI Tool**, click **Install**. This creates `/usr/local/bin/typewhisper` as a link to the CLI bundled inside the application.
7. Keep TypeWhisper running and verify the connection:

```bash
typewhisper status
typewhisper models
```

The API listens only on `127.0.0.1`. While it is running, TypeWhisper writes the active port and generated token to:

```text
~/Library/Application Support/TypeWhisper/api-discovery.json
```

The CLI discovers this file automatically. Treat it as a credential: do not print, copy, or commit its token.

## Recovery on a reset Mac

After installing and opening TypeWhisper once, restore the tracked configuration from the dotfiles repository:

```bash
macos/typewhisper.sh apply --quit --reopen
```

Then repeat the **CLI Tool > Install** step if `typewhisper status` reports that the command is missing. Confirm that the API server and token requirement remain enabled and run the status and model checks above.

The tracked preferences live in `macos/typewhisper/settings.json`. Workflows, dictionary entries, and snippets live beside it. Review those files rather than relying on a machine-local settings export.

## Security and backups

- Keep the API bound to loopback and token authentication enabled.
- Do not proxy or expose the API over a local network, Tailscale, or the public internet.
- TypeWhisper settings exports can include transcription history, prompts, app rules, and other personal data. Keep temporary exports outside source control and delete them when finished.
- Stop TypeWhisper before using the offline reconciler so its in-memory state cannot overwrite the restored configuration.

Official API documentation: https://www.typewhisper.com/en/docs/mac/api
