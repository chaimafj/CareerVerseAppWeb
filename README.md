# CareerVerse Web

A separate web implementation of CareerVerse, using **Ionic 8 + Angular 20**
for the frontend and **Django + Django REST Framework** for the API. The
existing Flutter application is not changed.

## Implemented scope

- Email registration/login/logout with Django sessions and CSRF protection.
- Editable student profile and canonical interest choices.
- Custom interests can be added alongside catalogue choices (30 selected maximum,
  100 characters each). Save profile also includes a pending custom entry; saved
  interests appear in the profile header and persist after reload. Canonical values
  remain trimmed/lowercase; custom interests match recommendations only when they
  overlap the catalogue's interest labels.
- Profile dashboard with personal details, interests, course/lab progress,
  career assessments and Premium expiry. Private profile photos support upload,
  replacement and removal (JPEG/PNG/WebP, max 5 MB and 16 megapixels).
  Pillow re-encodes images to JPEG, strips metadata and bounds dimensions to 512px.
  Photos are stored in the user's database record and served only through the
  authenticated `/api/me/photo/` endpoint, not a public media directory.
- Searchable career catalogue with category filters and detailed career pages.
- Courses with practical examples and persisted completion.
- Separate **Courses** and **Labs** navigation/catalogue pages. Finishing a course
  saves completion and stays on that course; it never starts or redirects to a lab.
  Career details also display courses and labs in separate sections. The existing
  preparation-course/lab relationship and Premium access rules remain unchanged.
  Both catalogues group their content into separate career sections, preserving
  order, completion status and Premium badges. Labs also retain correction links.
- Nine free beginner/intermediate/advanced labs with mission briefings and objectives.
- Three Premium workshops with five interactive tasks each, preparation courses,
  answer review navigation and detailed correction (selected versus expected choices).
- Server-side correction, timing, per-skill scores and immutable attempt snapshots.
- Persisted results, attempt history and best-attempt progress.
- Completed-lab badges with latest score and correction links on each learning path.
  Lab briefings list all your submitted attempts; retaking creates a separate result
  without deleting history. Result pages can show only mistakes and link back to retake.
  Completed means submitted, not necessarily passed.
- Explainable career recommendations: 75% performance + 25% interest fit
  when tested; 60% interest fit otherwise.
- Career final assessment after all three free labs: equally weighted mean of
  each lab's best score, rounded to two decimal places. Premium is optional.
  Below 60%, an improvement path prioritizes weak labs/skills, links corrections
  and preparation courses, and offers retakes. At exactly 60%, the warning is not
  shown. The current assessment appears on results, career details and Labs.
  This educational threshold is separate from each lab's 70% pass threshold.
- Responsive Ionic UI, persistent light/dark theme, explicit loading/error/empty states.
- Django administration for staff users to manage the catalogue and accounts.
- Local career chatbot with catalogue/course links, personal results explanations,
  interest guidance, limited career follow-up context and private saved history.
- FR/EN/AR interface, persistent language selector, Arabic RTL and localized dates.
- Private notification inbox, browser Web Push subscription and push delivery worker.
- Stripe test-mode Checkout with signed webhook verification for 30-day Premium access.

Seed content includes Angular development, cloud engineering and cybersecurity.
The nine original labs remain free. Active Premium unlocks **Launch-day checkout
rescue** (Angular), **Restore service under pressure** (Cloud) and **Investigate
a suspicious account** (Cybersecurity). Each capstone has a ten-minute recommended
duration. Django checks entitlement before opening its course, completing it or
starting the lab; a public catalogue preview does not expose lesson content or answers.
An attempt started while Premium is active can still be submitted after expiry,
and its owner's historical results remain readable. Progress counts all twelve labs.
Premium formats are distinct from free quizzes:
- Angular: type missing code fragments into a live code preview.
- Cloud: place components into highlighted slots in original SVG architecture diagrams.
- Cybersecurity: mark synthetic evidence rows, repair an owner check and review containment flow.

Scoring is unchanged: task accuracy contributes 80%, server-measured
timing contributes 20%, and the pass threshold is 70/100. Content is educational
workshop work, not an executable cloud or cybersecurity sandbox. Code tasks compare
the requested exact fragment after trimming leading/trailing whitespace; they do not
compile or execute arbitrary code or claim to accept every equivalent implementation.
Diagrams are simplified flow models, not drag-and-drop infrastructure deployment.
Corrections preserve the workspace and show the repaired code or expected architecture
flow. Migration `0006` and `seed_premium` update new attempts while retaining old snapshots.

This initial web version does **not** yet include Google login, password-reset
email UI, translated educational catalogue content, ESCO search,
generative AI, advertising or an offline/PWA installation workflow. These are
not represented by placeholder buttons or fake successful actions.

## Prerequisites

- Node.js supported by Angular 20 (Node 24 is used locally).
- Python 3.12+.
- PostgreSQL is optional for local development; SQLite is the default.

## Run on Windows

Open two PowerShell terminals inside `CareerVerseAppWeb`.

### Backend

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py seed_premium
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### Frontend

```powershell
Set-Location .\frontend
npm ci
npm start
```

Open **http://127.0.0.1:4200**. Register your own student account. There is no
hardcoded demo password.

Development creates an ignored local session-signing key in
`backend/.dev-secret-key`. Preserve it to keep sessions valid across restarts.
Production requires your own `DJANGO_SECRET_KEY` and `DJANGO_DEBUG=0`.

The frontend dev server proxies `/api/`, `/admin/` and `/static/` to Django.
Use the frontend origin for student requests so Django session and CSRF cookies
work together. Do not switch between `localhost` and `127.0.0.1` mid-session.

### Administration

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Visit **http://127.0.0.1:4200/admin/** and sign in with the staff account.
Student accounts cannot write catalogue content. Angular navigation guards are
only UX controls; actual access permissions are enforced by Django.

## Architecture

```text
frontend/src/app/
  core/              typed API client, session service, auth guard, models
  pages/             authentication, dashboard, careers, courses, quizzes,
                     results, recommendations, profile, career assistant
  app.component.ts   responsive navigation and theme
  app.routes.ts      Angular routes and unfinished-quiz exit guard
backend/
  config/            Django settings and URL configuration
  academy/           domain models, API views, serializers, admin, migrations,
                     catalogue seed command and automated tests
```

See [the backend README](backend/README.md) for the exact API and environment
configuration.

### PostgreSQL

SQLite requires no extra configuration. To use an existing PostgreSQL database,
set `DATABASE_URL` before running migrations and starting Django:

```powershell
$env:DATABASE_URL = 'postgresql://careerverse:<password>@127.0.0.1:5432/careerverse'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py seed_premium
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Replace the connection values with your own credentials. For a hosted database,
set `POSTGRES_SSLMODE` according to your provider's requirements.

## Quiz behavior

1. Starting a quiz creates a server-side attempt and a snapshot of its content.
2. Initial API responses contain options but never the correct answer flags.
3. The browser collects selections; Django validates question and option IDs.
4. On submission, Django determines elapsed time and calculates the score.
5. Each multiple-choice question requires the exact correct selection.
6. Submission is final; the result cannot be rewritten by another submission.
7. Feedback and explanations are returned after grading.

Default score:

```text
accuracy = correct / total * 100
time score = 100 within expected time
time score = max(0, min(100, 100 * (2 - elapsed / expected))) otherwise
overall = round(0.8 * accuracy + 0.2 * time score, 2)
passed = overall >= 70
```

Elapsed time is measured at the server, not trusted from browser input.
This is an educational quiz app, not a proctored exam platform.
Leaving or refreshing an unfinished quiz discards the current browser selections.
The server retains the unfinished attempt, which is not counted as a completion.
Finishing an attempt counts as completed even when its score is below the pass mark.

## Career assistant

The floating purple robot button opens the assistant in an Ionic modal without
leaving the current page. It is available to signed-in students, not in the
AppBar or main navigation. Suggested links close the modal and open the relevant
page; the saved conversation is restored when reopened. `/chat` remains a
direct full-page route and hides the floating button to avoid duplicate chats.

The assistant uses an authenticated Django endpoint:
`GET /api/chat/` loads history, `POST /api/chat/` accepts a `message`,
and `DELETE /api/chat/` clears only the signed-in student's history.
Messages are limited to 2,000 characters; the latest 50 exchanges are retained.
Replies, suggested routes and timestamps are saved alongside each message.

This is a transparent **rule-based assistant**, not a trained model or an
autonomous agent. It uses catalogue data and the student's own profile/results,
does not reveal quiz answers, and sends no data to external services.
English replies recognize some French topic keywords; full translated dialogue
is not implemented. Unknown topics receive an explicit limitations message.
Deleting an account also deletes its chat history.

## Languages

Choose English, French or Arabic in the header, including before sign-in.
The choice is persisted locally; Arabic sets the document to RTL. Interface
labels, controls, confirmation dialogs and dates follow the selected language.
Profile interests retain canonical stored values rather than translated IDs.
User-entered text is not translated.

Catalogue lessons, quiz questions/explanations and the local chatbot's replies
remain in English. A translated notice makes this limitation explicit.
Administrators may author additional content, but this version does not provide
automatic translation of database text or Django administration.

## Web Push and Stripe

These integrations require server configuration; they do not simulate successful
delivery or payment when credentials are missing. See
[backend setup](backend/README.md) for VAPID keys, the push delivery worker, test
Stripe credentials/price and Stripe CLI webhook forwarding.

### Password recovery and Google

The login page includes **Forgot your password?**, localized request/reset forms
and a **Continue with Google** integration. Development reset emails are saved
privately in the ignored backend mailbox, rather than sent over SMTP.
Google is disabled with an explanation until `GOOGLE_CLIENT_ID` is configured;
it is not a simulated login. See the backend README for SMTP/OAuth setup.
Existing email/password accounts are not automatically merged with Google accounts.

### Visual design and accessibility

The interface combines professional cards, blue/violet gradients and playful
original SVG illustrations (launch, code, Cloud, security and Premium).
Navigation uses consistent decorative icons; the dashboard, sign-in and Premium
pages feature gently animated artwork. Career cards remain static by default.
All artwork is bundled locally: no remote images, tracking or new dependencies.
Responsive layouts preserve light/dark themes and Arabic RTL. Page transitions,
hover effects and illustration animations respect `prefers-reduced-motion`.
Icons and illustrations are decorative; text labels remain available to assistive technology.

First-time sign-in creates a single welcome message in the UI language (FR/EN/AR),
including the automatic sign-in after registration. It is not recreated after
deletion or subsequent logins; previously signed-in accounts are not welcomed retroactively.

Clicking a notification card marks it as read. **Explore** saves its read status
before navigating; failed saves retain the unread state and display an error.

The **Notifications** page focuses on the private inbox, with all/unread filters,
read status and a single **Delete all** button with confirmation. It deletes all
the user's read and unread notifications, including those outside the latest 50
shown in the inbox. The Push configuration
and test panel has been removed from this page; existing browser subscriptions
remain active, but this page no longer offers new subscription setup. Notifications are queued after
lab submission and can be delivered by the worker while the page is closed.
Browser/OS background support is required; production must use HTTPS. Disabling
push or signing out removes this browser's subscription to avoid cross-account
notifications. Other registered devices are unaffected.

**Premium** opens Stripe's hosted test-mode Checkout. Only the server's verified
paid webhook activates or extends access; returning to the app never grants it.
After successful Checkout return, the page checks server status up to ten times
over about 30 seconds, then offers a manual refresh if confirmation is pending.
Active Premium displays a confirmation and expiry date instead of a payment
button; pending successful returns also hide payment to discourage duplicates.
Cancelled returns do not show payment success. This is a one-off purchase, not a
recurring subscription. Nine original labs are free; the three workshops require Premium.

### Local integration configuration (PowerShell)

From the backend directory, generate your own VAPID pair into an ignored file:

```powershell
.\.venv\Scripts\python.exe manage.py generate_vapid_keys > vapid-keys.local
```

Create the ignored `local-settings.ps1` locally and fill it with your own values:

```powershell
$env:VAPID_PUBLIC_KEY = '<generated public key>'
$env:VAPID_PRIVATE_KEY = '<generated private key>'
$env:VAPID_SUBJECT = 'mailto:<your contact email>'
$env:STRIPE_SECRET_KEY = '<your sk_test_ key>'
$env:STRIPE_WEBHOOK_SECRET = '<your test webhook signing secret>'
$env:STRIPE_PRICE_ID = '<your one-off test price ID>'
$env:WEB_APP_ORIGIN = 'http://127.0.0.1:4200'
```

This file is not loaded automatically. In each API/worker PowerShell terminal,
load it before starting the process:

```powershell
. .\local-settings.ps1
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Use another terminal for delivery (the command is single-run, not a daemon):

```powershell
. .\local-settings.ps1
while ($true) {
  .\.venv\Scripts\python.exe manage.py send_push_notifications --limit 100
  Start-Sleep -Seconds 30
}
```

For Stripe test events, with the Stripe CLI installed and authenticated:

```powershell
stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded --forward-to http://127.0.0.1:8000/api/billing/webhook/
```

Use the signing secret from this listener in your local server environment,
then restart Django. No VAPID or Stripe credentials are supplied by the
repository. Never commit the local settings or key file. Tests mock providers;
they do not prove real payment or browser delivery.

## Validate

```powershell
# backend directory
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check

# frontend directory
npm run typecheck
npm run build
npm test
```

## Production checklist

Local development settings are not a production deployment.
Configure an environment-provided secret key, disable DEBUG, use HTTPS,
configure hosts and secure cookies, migrate PostgreSQL, serve the built Ionic
frontend and API on the same origin, collect/serve Django static files, configure
backups and add operational rate limiting and monitoring. Do not commit `.env`,
local databases, virtual environments or user data.

Ionic is used as a web UI framework; no Capacitor native mobile project is
generated here. SQLite does not replace PostgreSQL in the proposed production
architecture, but makes a local checkout immediately runnable.
