# How it works

This page lists every outside request the project makes, what each one is for, and where it lives in the code.

## The daily run

`.github/workflows/daily.yml` runs five times a day, at 04:47, 08:17, 11:47, 15:17 and 17:17 UTC (10:17, 13:47, 17:17, 20:47 and 22:47 IST), and can also be started by hand from the Actions tab. Pushes do not trigger it. GitHub sometimes starts a scheduled run hours late, so the extra runs make sure one lands before the day ends. Each run rewrites the same day's entry with everything so far. Only the last run, at 22:47 IST, sends the Telegram message. A run that starts between midnight and 06:00 IST finishes the previous day's entry. The steps:

1. `python bot/devlog.py` writes today's entry.
2. `python bot/context.py` rebuilds `context.md`.
3. The workflow commits `log/` and `context.md` as `log: YYYY-MM-DD` and pushes.
4. `python bot/notify.py daily` sends the Telegram message. If any step fails, `notify.py failure` sends an alert with a link to the run.

## Requests the bot makes

| Request | Used by | Purpose |
|---|---|---|
| `POST https://api.github.com/graphql` | `bot/devlog.py` | Reads `contributionsCollection` for one day: commits per repository, pull request, issue and review counts, and the count of contributions GitHub hides in private repositories |
| `GET https://api.github.com/repos/{user}/dev-log/commits?author=&since=&until=` | `bot/devlog.py` | Counts real work in this repository, skipping the bot's own `log:` commits |
| `GET https://api.github.com/users/{user}/repos?type=owner&sort=pushed` | `bot/context.py` | Lists public repositories for the chat bot's context |
| `GET https://api.github.com/repos/{owner}/{repo}/commits?per_page=5` | `bot/context.py` | Takes the latest commit messages of each public repository |
| `POST https://api.telegram.org/bot{token}/sendMessage` | `bot/notify.py`, `chat/api/telegram.py` | Sends pings and chat replies |
| `GET https://raw.githubusercontent.com/{user}/dev-log/main/context.md` | `chat/core.py` | Loads the chat bot's context |
| `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `chat/core.py` | Asks Gemini a question, with the context and safety filters attached |
| `POST https://api.groq.com/openai/v1/chat/completions` | `chat/core.py` | Optional fallback when Gemini fails and a `GROQ_API_KEY` is set |

GitHub calls use the `ACTIVITY_TOKEN` secret and are read-only. The workflow pushes with its own built-in token, which can write to this repository only.

## The one request the bot receives

Telegram sends each message you write to `POST /api/telegram` on the Vercel project.

| Case | Response |
|---|---|
| Missing or wrong `X-Telegram-Bot-Api-Secret-Token` header | `403`, nothing else happens |
| Message from any chat id except the owner's | `200`, no reply |
| Normal message | `200`, and the reply is sent through `sendMessage` |
| An error while answering | `200` (so Telegram does not retry), and the owner gets `Something went wrong (<error type>)` |
| `GET` | `404` |

The secret token is derived from the bot token, so it is not stored anywhere else.

## Chat guards, in the order they run

1. Header check: the request must carry the derived secret.
2. Owner check: the chat id must match `TELEGRAM_CHAT_ID`.
3. Input check: empty or over 500 characters is answered with a fixed message.
4. Pattern block: instructions to forget or ignore rules, requests for the system prompt, and anything mentioning keys, passwords, secrets or tokens get a fixed refusal. The model never sees them.
5. Model call: Gemini with safety filters set to block low-level harm, a system prompt that limits answers to the context, and the context and question wrapped as data.
6. Output scrub: anything shaped like a GitHub, Google, Telegram or API key is replaced with `[removed]`, and replies are cut at 1500 characters.

`/status` skips the model and prints the facts at the top of `context.md`.

## Configuration

| Name | Where | Needed for |
|---|---|---|
| `ACTIVITY_TOKEN` | Actions secret | Reading GitHub activity |
| `TELEGRAM_BOT_TOKEN` | Actions secret, Vercel env | Sending and receiving Telegram messages |
| `TELEGRAM_CHAT_ID` | Actions secret, Vercel env | Knowing who the owner is |
| `GEMINI_API_KEY` | Vercel env | Answers |
| `GEMINI_MODEL` | Vercel env, optional | Overrides the default model |
| `GROQ_API_KEY`, `GROQ_MODEL` | Vercel env, optional | Fallback answers |

Constants in the code: `USER` and `TZ` in `bot/devlog.py`, and `TOKEN_EXPIRES`, `IDLE_AFTER` and `WARN_DAYS` in `bot/notify.py`.

## Telegram messages

- Daily: the entry text, plus a line after three or more quiet days in a row.
- Token expiry: a warning 30, 7, 3, 2, 1 and 0 days before `TOKEN_EXPIRES`.
- Failure: a link to the failed run.

## Known limits

- The chat bot forgets each message as soon as it answers.
- On a quiet day the bot's own commit is the only contribution, so that square is the lightest green.
- GitHub may start scheduled runs late, and a repository with no activity for 60 days has its schedules switched off. The daily commit keeps this one active.
