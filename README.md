# nba_score_bluesky_bot
A bot that posts on Bluesky when an active player moves up the all time NBA Scoring list.

## Logging

The bot writes logs to stdout so they are visible in Docker and GitHub Actions logs.

- `INFO`: high-level run progress and successful post sends
- `DEBUG`: post content previews and detailed processing
- `WARNING`: recoverable issues (missing env vars, retries)
- `ERROR`: unrecoverable failures (auth/posting/fetch failures)

Control verbosity with `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

Logging is configured centrally in `utils/settings.py` via `configure_logging()`.

## Tests

Run the unit tests with `python3 -m unittest`.
