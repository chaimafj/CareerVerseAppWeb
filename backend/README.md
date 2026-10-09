# CareerVerse Django API (MVP)

Backend only. Django 5.2, Django REST Framework, session authentication and CSRF.
SQLite is the default; all commands below run from this directory in PowerShell.
Python 3.11+ is required (verified with Python 3.13).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py seed_premium
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py test academy
# When you are ready to serve (not started as part of implementation):
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`seed_demo` atomically upserts Angular, Cloud and Cybersecurity, each with three
levels, a course per lab, three lessons and three questions per lab (27 questions
total, including multiple-choice questions). Reruns retain seeded IDs, reset demo
content, and leave user data and historical attempts intact. No users or passwords
are seeded. `/admin/` uses the superuser you create. Academy content models are registered;
career/lab/question editors have linked inlines; answer options are edited inside
the question editor. Attempts/results are read-only in admin to protect history.

### Environment

* `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/careerverse` switches to
  PostgreSQL. URL-encode credentials. Optional `POSTGRES_SSLMODE=require` (or a
  PostgreSQL-supported mode). Use a dedicated database/user; run `migrate` and
  `seed_demo` against it. SQLite defaults to `db.sqlite3`.
* `DJANGO_DEBUG=1` by default for local development.
* `DJANGO_SECRET_KEY`: set your own secret through the environment. When absent in
  debug mode, a cryptographically random key is generated once and persisted in
  `backend\.dev-secret-key` (ignored by Git). Subsequent processes read that same
  key, so database-backed sessions survive restarts. The file is atomically
  published without overwriting another process's key; malformed files fail
  explicitly rather than silently rotating. Environment keys always take
  precedence and do not create/read the development file.
  With `DJANGO_DEBUG=0`, a nonempty environment key is mandatory even if the
  development file exists, and cookies require HTTPS. There is no production
  fallback to the local file.
  Example: `$env:DJANGO_SECRET_KEY = '<your independently generated secret>'`.
  Do not commit or share the file/key. Changing/removing the key invalidates
  existing sessions. Sessions signed with the previous ephemeral development key
  cannot be recovered; sign in once after adopting this fix, then restarts retain
  authentication. On Windows the file inherits the backend directory's ACL;
  restrict that directory to your account.
* `DJANGO_ALLOWED_HOSTS`: optional comma-separated deployment hosts. `localhost`,
  `127.0.0.1` and `testserver` are always allowed. No `.env` auto-loading.

## Browser session + CSRF

Use a **same-origin frontend development proxy** for `/api/` to this backend,
preserving cookies and forwarding the browser's host/origin consistently.
There is intentionally no cross-origin CORS setup or bearer-token authentication.

## Stripe TEST-only 30-day premium

Install the updated `requirements.txt`, then run `manage.py migrate`. Billing
requires these process environment variables (no keys are included in source):

* `STRIPE_SECRET_KEY`: your **`sk_test_…`** key. Live keys disable billing.
* `STRIPE_WEBHOOK_SECRET`: the **`whsec_…`** signing secret from Stripe CLI or
  your test webhook endpoint. This is not the API secret.
* `STRIPE_PRICE_ID`: an active **test-mode, fixed, one-time** `price_…`.
  Amount and currency are retrieved from this price, never from the browser.
* `WEB_APP_ORIGIN`: defaults to `http://127.0.0.1:4200`; must be an origin
  without credentials/path/query/fragment. HTTPS is required except localhost
  and 127.0.0.1 development origins. Redirects use `/premium?checkout=success`
  or `/premium?checkout=cancelled`.

PowerShell example: `$env:STRIPE_SECRET_KEY = '<your test key>'` (and similarly
for the other variables). Optionally keep assignments in ignored
`backend\local-settings.ps1` and dot-source it in **each** API/worker shell.
`.env`/`.env.*` are ignored but are **not auto-loaded**. Never commit credentials.

For local signed webhooks, install/sign in to Stripe CLI, then:

```powershell
stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook/
```

Copy the CLI's signing secret into `STRIPE_WEBHOOK_SECRET`, restart the API,
and complete a checkout using Stripe's documented test payment methods.
The public webhook is signature-verified against the **raw request bytes** and
CSRF-exempt; other billing routes require authenticated sessions and checkout
requires CSRF. Live events/sessions/prices are rejected. Only a persisted own
checkout with matching paid completed session, user, price, quantity, amount
and currency grants premium. Signed event and Stripe-retrieved session are
validated. Duplicate events (including different event IDs for the same session)
grant nothing extra. Each distinct paid checkout atomically adds exactly 30 days
from `max(now, premium_until)`. Frontend redirects never grant access.

| Method / path | Request | Response |
|---|---|---|
| GET `/api/billing/status/` | none | `{configured: boolean, premium_until: ISO-string or null, is_premium: boolean}` |
| POST `/api/billing/checkout/` | `{}`; client pricing ignored | `{url: string}` |
| POST `/api/billing/webhook/` | Stripe signed event | `{received: true}` |

Unconfigured/invalid test settings return `configured:false` on status and
explicit 503 on checkout/webhook. Invalid signature/live/mismatched checkout
returns 400; unpaid or irrelevant test events are acknowledged without a grant.
Provider checkout failures return 502; webhook verification failures return 503
so Stripe retries.

## Real Web Push and durable notifications

Generate your own matching VAPID keys (command prints secrets; do not share output):

```powershell
.\.venv\Scripts\python.exe manage.py generate_vapid_keys
$env:VAPID_PUBLIC_KEY = '<generated public base64url key>'
$env:VAPID_PRIVATE_KEY = '<generated private base64url key>'
$env:VAPID_SUBJECT = 'mailto:your-contact@example.com'
```

`VAPID_SUBJECT` must be a contact `mailto:` address or HTTPS URL. Set these
variables in both API and worker processes; keep any local assignments in the
ignored `local-settings.ps1`. Invalid/missing/mismatched keys explicitly disable
push. Push requires browser notification permission, a service worker and
PushManager subscription on a secure browser origin (localhost is allowed by
browsers); the frontend must implement those browser pieces.

All following endpoints are owner-private and session-authenticated. Every
POST/DELETE requires the current CSRF token. No anonymous subscriptions:

| Method / path | Request | Response |
|---|---|---|
| GET `/api/push/config/` | none | `{configured: boolean, public_key: string}` (empty key when disabled) |
| POST `/api/push/subscriptions/` | `{endpoint, keys:{p256dh,auth}, language:'en'\|'fr'\|'ar'}` | same shape, 201 new / 200 updated |
| DELETE `/api/push/subscriptions/` | `{endpoint}` | 204, own subscription only |
| POST `/api/push/test/` | `{}` | 201 own notification; enqueue only, 400 if not subscribed |
| GET `/api/notifications/` | none | latest 50, bare array of `{id,title,body,path,read,created_at}` |
| POST `/api/notifications/<id>/read/` | `{}` | same notification shape; 404 for foreign/missing ID |

Subscribe/test returns 503 if push is disabled. Subscriptions are validated:
bounded base64url P-256 public key and 16-byte auth secret; HTTPS endpoint on
exact `fcm.googleapis.com`, `updates.push.services.mozilla.com` or
`web.push.apple.com`, or Microsoft Edge's single-label WNS hosts
`<host>.notify.windows.com`, port 443 only, no credentials/fragments/whitespace.
Local/private/IP/arbitrary-host endpoints are rejected; delivery never follows
redirects. Other browser push providers are deliberately unsupported until
explicitly reviewed/allowlisted. An endpoint owned by another account returns
409, never reassigned; unsubscribe in the browser and resubscribe after account
switching.

Each successfully submitted lab creates an inbox notification and transactional
outbox deliveries without network I/O in the submit request, preserving grading.
Notifications contain no private scores. Inbox copy uses the most recently
registered subscriber locale (English when none); each device delivery uses its
own EN/FR/AR locale. Test requests also only enqueue. Result paths are
`/results/<result-id>`; test path is `/notifications`. Worker payload is
`{title,body,path,tag}` with stable `notification-<id>` tag for deduplication.
Subscription POST ignores top-level extras such as browser `expirationTime`.

**Run a worker** with the same environment; API alone does not send push:

```powershell
.\.venv\Scripts\python.exe manage.py send_push_notifications --limit 100
# Local foreground loop (Ctrl+C to stop), or schedule this command every minute:
while ($true) {
  .\.venv\Scripts\python.exe manage.py send_push_notifications --limit 100
  Start-Sleep -Seconds 30
}
```

Each run claims pending deliveries with a five-minute lease and sends encrypted
Web Push using pywebpush, with a 20-second timeout. Failures are explicitly logged
by delivery ID/type/status without endpoint tokens or keys. At most five attempts
with exponential backoff; exhausted deliveries remain marked failed for inspection.
Only 404/410 retires a subscription; transient failures, 403 and redirects keep
it. Run repeatedly via cron/Task Scheduler, monitor errors and failed rows.
As with any external outbox, interruption after provider acceptance but before
DB acknowledgement may cause a duplicate; browser can deduplicate by notification
tag. All checkout/subscription/notification/outbox data cascades on account deletion.
Migration `0004` adds `User.premium_until`, `PremiumCheckout`, `PushSubscription`,
`Notification`, and unique-per-subscription `PushDelivery`; no existing data reset.

Provider behavior is covered with mocked tests, not a claim of real Stripe/push
delivery verification. No real provider requests occur in the automated suite.

1. `GET /api/csrf/` sets the readable `csrftoken` cookie.
2. Include session cookies and `X-CSRFToken: <csrftoken>` on every POST/PATCH.
3. Registration and login establish the session and **rotate the CSRF cookie**;
   read the current cookie again before the next unsafe request.
4. Logout ends the session. `sessionid` is HttpOnly; both cookies use SameSite=Lax.

```javascript
await fetch('/api/csrf/', {credentials: 'same-origin'});
const csrf = () => decodeURIComponent(
  document.cookie.split('; ').find(c => c.startsWith('csrftoken=')).split('=')[1]
);
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
  body: JSON.stringify({email: 'you@example.com', password: 'your password'})
});
```

Anonymous login/registration are explicitly CSRF-protected too. Use JSON bodies
and trailing slashes. Unsafe requests from untrusted origins are rejected.
Anonymous private requests return 403 with session authentication (not 401).
Invalid JSON, fields, password or answers return 400; foreign-owned/missing
attempts/results return 404; replay/unsupported snapshot versions return 409.
Errors use `{"detail": "..."}` or serializer field-error objects. CSRF failures
return 403 JSON, never successful writes.

## Exact API contract

The following notation shows field names and types, not literal placeholder data.
IDs are integers; percentages are numbers from 0 to 100; timestamps are UTC ISO
8601 strings. List responses are bare arrays, not paginated wrappers.

### Authentication and profile

`User = {id, email, name, interests: string[], university, specialty, study_level, bio}`.
All profile scalar values other than `id` are strings.

| Method / path | Request | Response |
|---|---|---|
| GET `/api/csrf/` | none | 200 `{"detail":"CSRF cookie set."}` + cookie |
| POST `/api/auth/register/` | `{name,email,password}` | 201 `User` + session |
| POST `/api/auth/login/` | `{email,password}` | 200 `User` + session |
| POST `/api/auth/logout/` | `{}` | 200 `{"detail":"Logged out."}` |
| GET `/api/me/` | none | 200 `User` |
| PATCH `/api/me/` | any subset of `{name,interests,university,specialty,study_level,bio}` | 200 `User` |

Emails are unique case-insensitively, canonicalized to lowercase and immutable
through `/me/`. Passwords use Django validators and hashing, never appear in
responses. Interests must be a list of at most 30 nonblank strings (100 characters
each), normalized to lowercase, trimmed and deduplicated. Profile field limits:
name 150, university/specialty 200, study_level 100, bio 2000. Unexpected profile,
registration, login and submission fields are rejected.

### Password recovery and Google sign-in

- POST `/api/auth/password-reset/` with `{email}` returns the same generic
  response for existing, missing, inactive and Google-only accounts.
- POST `/api/auth/password-reset/confirm/` with `{uid, token, password}`
  validates a one-hour, single-use Django token and the existing password rules.
  Changing the password invalidates previous sessions. Both endpoints require
  CSRF and are IP rate-limited (5 requests/hour, 20 confirmations/hour).
- In DEBUG mode the default Django file email backend writes messages to
  `backend/private-emails/` (ignored, not served). Open the local message file
  privately to use its link; no real e-mail is sent in this mode.
- Real SMTP: set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`,
  `EMAIL_HOST`, `EMAIL_PORT` (587 default), `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS=1` and `DEFAULT_FROM_EMAIL` locally.
  Set `WEB_APP_ORIGIN` to the trusted frontend HTTPS origin in production.
  Never commit SMTP credentials, saved mails, reset tokens or links.
- GET `/api/auth/google/config/` supplies the public OAuth client ID and a
  random session-bound nonce. POST `/api/auth/google/` accepts `{credential}`.
  The server verifies the Google ID token's signature, expiry, issuer, audience,
  verified email and nonce; the nonce expires after ten minutes and is consumed
  on successful login. The POST requires CSRF and is limited to 30/hour.
- To enable Google, create a Google OAuth **Web application** client, configure
  the consent screen/test users and authorized JavaScript origins (local:
  `http://127.0.0.1:4200`, or `http://localhost:4200` if used), then set
  `GOOGLE_CLIENT_ID` locally and restart Django. No OAuth client secret is
  required by the GIS ID-token flow; never put one in the frontend.
  Google's hosted button is loaded only when configured.
- Migration `0009` stores a unique Google subject tied to the user, independent
  of email changes. New Google users have no password and receive the existing
  once-only welcome notification. Existing email/password accounts are **not**
  silently linked: sign in using their original password instead. Google-only
  users recover access through Google, not the local password reset form.

### Notification inbox deletion

Registration signs the user in and creates a welcome notification; an existing
account that has never signed in receives it on its first successful login.
The inbox copy uses the UI's `Accept-Language` (FR/EN/AR, English fallback).
The durable user flag prevents duplicates, including after **Delete all**;
creation and the flag update are atomic. Existing accounts with a previous
`last_login` are marked during migration `0008` and receive no retroactive welcome.
No Push permission is required: the message always appears in the private inbox.
Existing subscriptions also receive an outbox delivery in their device language.

DELETE `/api/notifications/` returns 204 and deletes all the current user's
notifications (read and unread, not just the latest 50). An empty inbox also
returns 204. Other users' records are untouched. Authentication and CSRF protect deletion.
Related outbox deliveries are deleted, but browser subscriptions are retained.
Already delivered OS notifications cannot be recalled by deleting an inbox record.

### Profile photos

Migration `0007` stores the normalized photo and version token on the user.
POST `/api/me/photo/` accepts multipart field `photo` only (JPEG/PNG/WebP,
5 MB maximum, 16 megapixels maximum). The decoder validates actual content,
applies EXIF orientation, drops metadata, resizes within 512x512 and converts to
JPEG. GET returns only the authenticated user's image with private/no-store caching;
no photo returns 404. DELETE removes it. Session authentication and CSRF protect
mutations. `/api/me/`, login and registration include nullable read-only `photo_url`.
Profile text edits cannot set photo storage or URLs. Database backups therefore
include photos. No public photo URL or filesystem serving setup is required.

### Catalog and courses

Authenticated GET `/api/careers/<slug>/assessment/` and GET
`/api/career-assessments/` return the current owner-only career assessment(s):
`{career_slug,career_title,completed_labs,required_labs,complete,final_score,
needs_improvement,learning_path}`. Career detail also includes `assessment`;
anonymous readers receive only empty personal progress.
All current free labs must have a result (Premium is excluded); otherwise
`final_score=null` and `learning_path=[]`. Final score is the mean of each free
lab's best score, rounded half-up to two decimals. A rounded score strictly below
60 triggers a path ordered by weakest best lab score, containing correction
`result_id`, `lab_id/title`, weak skills below 60, and nullable `course_id/title`
plus course completion. Completed courses can be reviewed again. Higher retakes
update the assessment; lower retakes never lower it. It is derived from saved
results, not a new client-supplied score or an immutable historical assessment.

Authenticated GET `/api/courses/` lists course summaries
`{id,title,career_slug,career_title,completed,is_premium,locked}` without lessons.
Authenticated GET `/api/labs/` lists mission summaries with completion/latest
result metadata, never quiz questions or answer keys. These power separate UI
catalogues. Finishing a course does not create an attempt or a result.

`Career = {slug,title,summary,description,category,tools: string[],interests:
string[],salary,education,outlook}`. Other fields are strings.

* GET `/api/careers/`: 200 `Career[]`, publicly readable.
* GET `/api/careers/<slug>/`: 200 `Career` plus:
  ```text
  courses: [{id, title, completed: boolean, lab_id, is_premium: boolean, locked: boolean}]
  labs: [{id, title, level: "Beginner"|"Intermediate"|"Advanced", question_count,
          best_score: number|null, is_premium: boolean, locked: boolean,
          scenario: string, objectives: string[], expected_seconds: number}]
  ```
  Publicly readable; anonymous users see `completed=false`, `best_score=null`.
  Personalized fields only consider the logged-in user's records.
* GET `/api/courses/<id>/` (authenticated):
  ```text
  {id,title,intro,lessons:[{title,body,example}],career_slug,lab_id,completed}
  ```
  Lesson values are strings.
* POST `/api/courses/<id>/complete/` with `{}`: 200 `{id,completed:true}`.
  Idempotent for the current user; MVP completion is self-declared.

Students cannot create/edit/delete catalog entries. Only staff with appropriate
Django admin permissions can maintain the catalog.

### Quizzes

`seed_demo` retains nine free labs. After it, `seed_premium` idempotently upserts
three advanced Premium workshops with five interactive tasks and one course each.
Both commands retain users and historical attempt snapshots. Migration `0005`
adds mission fields and separates free/Premium uniqueness within each career level.

GET `/api/labs/<id>/` (authenticated) returns `{id,title,career_title,career_slug,
level,is_premium,locked,scenario,objectives,expected_seconds,question_count}`.
This briefing contains no questions, answer keys or course lessons.
It also returns owner-only `completed`, `attempt_count`, `latest_result` and
`results` (newest first). Each summary has `id,score,passed,correct,total,completed_at`.
Career lab links include the same completion fields, except the full `results` list.
Anonymous catalogue readers see no personal results. Only submitted attempts count
as completed, even if below the pass threshold. Retakes retain all older results.

Premium course reads/completion and lab starts return 403 unless the authenticated
user's `premium_until` is strictly in the future. Free labs remain accessible.
Entitlement is checked at start: an existing attempt can be submitted after expiry;
its result remains owner-readable. Chat course suggestions skip locked courses.
Progress totals include free and Premium labs.

POST `/api/labs/<id>/start/` with `{}`: 201

```text
{id,lab_title,career_title,
 questions:[{id,prompt,options:[{id,text}],multiple:boolean,kind,workspace}],expected_seconds,
 scenario,objectives,is_premium}
```

The returned `id` is the **attempt ID**. No option answer flags, expected answers,
skills or explanations are exposed by this endpoint. A version-1 server snapshot
freezes titles, expected time, prompts, options, answer keys, explanations and
skills at start. Catalog edits/deletion cannot change correction or result text.
Migration `0006` adds task `kind` and validated JSON `workspace` fields:
`quiz` (empty workspace), `code` (`before,after` strings),
`architecture` (`nodes` string array and zero-based missing `gap`),
`evidence` (`context` string). No raw SVG/HTML is stored; Angular renders escaped
text within a fixed SVG template. Workspace validation rejects invalid configurations
before attempt creation. Old snapshots default to `quiz`.
An empty/misconfigured lab returns 400 without creating an attempt.
New result feedback also contains `selected_options` and `correct_options` text
arrays from the immutable snapshot, only after submission. Older saved results
without these optional fields continue to render.
Result responses include nullable `lab_id` for the retake link; deleted labs cannot
be retaken. For older results, expected choices are recovered from their immutable
snapshot, not today's catalogue. Original selections cannot be reconstructed when
they were never stored, and the UI explicitly indicates this.

POST `/api/attempts/<id>/submit/`:

```json
{"answers":[{"question_id":1,"option_ids":[2]}]}
```

For a code task use `{"question_id":1,"option_ids":[],"code_text":"switchMap"}`.
`code_text` is at most 500 characters and is required for code tasks only.
The server compares the trimmed fragment to its frozen accepted answer; it never
executes code. Public code tasks return an empty `options` array so accepted fragments
remain private until correction. Architecture/evidence tasks use existing option IDs;
exact evidence sets and single-slot placements are graded without partial credit.
Feedback includes task `kind` and `workspace`, preserving the exercise context.

Exactly one entry is required for **every snapshot question**; use `option_ids:[]`
for unanswered questions. IDs must be JSON integers (not booleans/strings/floats).
Unknown/repeated questions, foreign/repeated options, unexpected fields and more
than one selected option on a single-choice question are rejected without
consuming the attempt. Multiple-choice answers must match the full correct set;
there is no partial credit. Submitted attempts cannot be replayed (409).

Submission returns 201 `Result`; GET `/api/results/<id>/` returns 200 the same:

```text
{id,career_title,career_slug,lab_title,correct,total,score,time_score,
 duration_seconds,passed:boolean,skills:{skill_name:accuracy_percentage},
 feedback:[{prompt,correct:boolean,explanation,selected_options:string[],correct_options:string[],kind,workspace}]}
```

The returned `id` is the **result ID**, not the attempt ID. Attempts/results are
owner-only, including feedback. Elapsed time is measured from the server's start
timestamp to receipt of a valid submission, rounded down to whole seconds and
clamped at zero. Client time/score fields are rejected.

```text
accuracy = correct / total
time_score = 100 * clamp(2 - duration_seconds / expected_seconds, 0, 1)
score = round(80 * accuracy + 0.20 * time_score, 2)
passed = score >= 70
```

At or below the expected time the time bonus is 100; it falls linearly to 0 at
twice the expected time and stays bounded. Skill percentages measure accuracy
only. Submission and result creation are transactional with a one-to-one result,
a conditional submission claim and PostgreSQL row locking.

### Progress and recommendations

GET `/api/progress/` (authenticated): 200

```text
{completed_labs,total_labs,average_score,completed_courses,
 results:[{id,career_title,lab_title,score,completed_at}]}
```

`completed_labs` counts distinct currently existing labs with a submitted result,
regardless of passing; `total_labs` counts current catalog labs.
`average_score` averages **all** the user's results, including retries, or 0.
Results are newest first; deleting a catalog lab preserves history but removes it
from the completed-lab count. Course counts refer to existing courses.

GET `/api/recommendations/` (authenticated): 200

```text
[{career_slug,career_title,score,tested:boolean,performance,shared_interests:string[]}]
```

One recommendation per current career, descending score then slug for ties.
`performance` is the mean best score per attempted lab for that career, or 0.
`tested` means at least one submitted result. Interest overlap is case-insensitive:
`interest_score = round(100 * shared_count / career_interest_count)` (0 for no tags).
The denominator is the count of unique normalized **career** interests, not the
union of profile and career interests (not Jaccard). Matching is exact after
normalization: `"Web"` does not match `"web development"`.
As in Flutter, tested recommendation scores are
`round(0.75 * performance + 0.25 * interest_score)`; untested scores are
`round(0.6 * interest_score)` (maximum 60). Both rounds use nearest whole number,
with halves rounded up. For performance 100 and one shared Angular interest out
of three, interest fit rounds to 33 and the match score is 83.
Shared interests are sorted. Historical results remain useful even if their
original lab was deleted.

## Scope and limitations

This is a learning MVP, not a proctored exam or labor-market prediction service.
Demo salaries are deliberately nonnumeric and local-market-dependent. Courses
teach quiz concepts; there is no anti-cheating, resume upload, email verification,
password recovery, billing, rate limiting, frontend or external AI integration.
Attempts can be started/retried freely and have no expiry; repeated submission of
the same attempt is prohibited. Time includes reading and network delay. Arrays
are unpaginated and unsuitable for very large histories without further work.
SQLite supports local development, not high-concurrency submission workloads;
use PostgreSQL for concurrent deployment (not integration-tested here). Snapshot
schema upgrades need explicit backward-compatible grading before accepting older
versions. Catalog authors must keep list JSON fields and question answer sets
valid; the start endpoint validates quiz configuration.

Before production: provision a stable secret, HTTPS, restricted host/proxy
configuration, backups, production WSGI serving, static collection, request/rate
limits, monitoring and deployment-specific security settings. Run
`manage.py check --deploy` in that configuration. Development defaults are not
production-ready. Local venv, SQLite files, caches, environment files and uploads
are ignored by the backend `.gitignore`.
