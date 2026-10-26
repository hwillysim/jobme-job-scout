# Set up your Job Scout

Job Scout finds jobs across Australia that suit you and sends you a shortlist on the days you choose. An AI agent
(Claude, or ChatGPT's Codex) does the searching. A scoring service called JEV rates every role against your profile.
[PRIVACY.md](PRIVACY.md) explains what personal information goes where. In short, JEV never gets your name or
contact details.

## Choose your route

Job Scout needs somewhere to keep its memory between runs (your profile and the jobs you've already seen). There are
two options:

| | **A. In the cloud** | **B. On your computer** |
| --- | --- | --- |
| Needs a GitHub account | Yes (free) | **No** |
| Runs when your computer is off | Yes | No: your computer has to be on and awake, with the app open |
| Where you use it | Phone or computer | Set up on a computer; results reach your phone by email |
| Apps | Claude app (recommended), or Codex in ChatGPT | Claude desktop app (recommended), or the Codex app |
| Plan | Claude Pro or Max, or a ChatGPT plan with Codex | The same |

Pick **A** if you want it to run reliably from your phone. Pick **B** if you'd rather not deal with GitHub and your
computer is usually on in the mornings. Setup takes about 20 minutes either way, plus the first scout, which runs on
its own for 20 to 40 minutes.

You'll also need **the JEV API key from Henry**, which he'll send you privately.

---

## About the API key (read this first)

Job Scout sends each job ad to JEV, a scoring service run by a company called TypeSafe. JEV only answers requests
that come with a key, which is a long password that looks like a jumble of letters and numbers. Henry's key is
linked to his account, and he pays for what it's used for. So:

- Don't paste it into a chat, an email or a note. **It only goes in the one place your route's steps describe.**
- If it ever ends up somewhere else, tell Henry so he can swap it for a new one.

---

## Route A: in the cloud (with GitHub)

### A1. Make your own private copy

1. Create a free GitHub account at [github.com/signup](https://github.com/signup) if you don't have one.
2. Open **[github.com/hwillysim/jobme-job-scout](https://github.com/hwillysim/jobme-job-scout)**, tap **Use this
   template**, then **Create a new repository**.
3. Name it `job-scout` and choose **Private**. This matters: your copy will hold your profile and shortlists.
4. Tap **Create repository**.

### A2. Connect GitHub to your AI app

- **Claude:** go to [claude.ai/code](https://claude.ai/code) and sign in. The first time, it asks you to connect
  GitHub. When GitHub asks which repositories Claude can use, choose **Only select repositories** and pick your
  `job-scout`.
- **Codex:** go to [chatgpt.com/codex](https://chatgpt.com/codex), connect GitHub, and give it access to your
  `job-scout`.

### A3. Save the API key and switch on internet access

**In Claude:**

1. At [claude.ai/code](https://claude.ai/code) (or the **Code** tab in the Claude app), go to the screen where you
   start a new session. Under the message box, tap the first control in the row. This is the **environment**
   picker, and it probably says **Default**.
2. Tap **New environment**, name it `Job Scout`, set **Network access** to **Full**, and tap **Add environment**.
3. Open the picker again and find **Job Scout** under **Cloud** (tap **More** if it isn't shown). Tap the settings
   icon (⚙) on its row.
4. Tap **Network secrets**, then **Add secret**, and fill in:
   - **Name:** `JEV`
   - **Secret type:** leave it as **Bearer**
   - **Allowed websites:** `api.typesafe.ai`
   - **Custom headers:** leave **Name** as `Authorization` and **Prefix** as `Bearer`. Paste Henry's key into
     **Value**.
5. Tap **Add**. You can't view the key again, which is expected. Claude adds it to requests sent to JEV, so the
   agent never sees it.

**In Codex:**

1. In [chatgpt.com/codex](https://chatgpt.com/codex), open **Settings**, then **Environments**, and create an
   environment for your `job-scout`.
2. Under **Environment variables**, add `JEV_API_KEY` with Henry's key as the value. Use *Environment variables*,
   not *Secrets*: Codex removes secrets before the agent starts, so the scout couldn't use it there.
3. Set **Agent internet access** to **On**, the domain allowlist to **All (unrestricted)**, and allow **all HTTP
   methods**.
4. Save. Codex shows environment variables to the agent, which is told never to print it.

### A4. Start it and say "Set me up"

- **Claude:** in the Claude app's **Code** tab, start a new session with your `job-scout` repository and the **Job
  Scout** environment. Choose **Opus 5.5** (with **medium** effort if you're asked), then type **Set me up**.
- **Codex:** start a new task on your `job-scout` environment with **GPT 6.1 Sol** on **medium** reasoning, then type
  **Set me up**.

### A5. Your schedule

The agent asks which days and time you'd like a fresh shortlist, then helps you set it up:

- **Claude:** go to [claude.ai/code/routines](https://claude.ai/code/routines) and tap **New routine**. Fill it in
  like this:
  - **Name:** `Job Scout`
  - **Prompt:** everything in `ROUTINE.md`
  - **Model:** the one you chose
  - **Repository:** your `job-scout`
  - **Environment:** **Job Scout**
  - **Trigger:** **Schedule** with your days and time. Pick a few minutes past the hour, such as 7:37, because runs
    on the hour can start a little late.
  - **Connectors:** remove everything except **Gmail** if you want email (see "Email or notification" below).

  Then tap **Create**.
- **Codex:** if your plan offers scheduled tasks (automations), the agent helps you set one up. If it doesn't, say
  **run my job scout** whenever you want a fresh shortlist.

---

## Route B: on your computer (no GitHub)

### B1. Download Job Scout

1. On your computer, open **[github.com/hwillysim/jobme-job-scout](https://github.com/hwillysim/jobme-job-scout)**.
   You don't need an account.
2. Tap the green **Code** button, then **Download ZIP**.
3. Open the downloaded file to unzip it. Move the folder into your **Documents** folder and rename it `job-scout`.

### B2. Save the API key

1. Open a plain text editor:
   - **Mac:** open **TextEdit**, then choose **Format → Make Plain Text**.
   - **Windows:** open **Notepad**.
2. Paste Henry's key and nothing else. No spaces, no new line.
3. Save it inside your `job-scout` folder as **`jev_key.txt`**. On a Mac, if TextEdit offers to add ".txt" again,
   keep just one.

The scout reads the key from this file. The file stays on your computer and is never uploaded anywhere.

### B3. Start it and say "Set me up"

- **Claude:** install the [Claude desktop app](https://claude.ai/download) and sign in. Open the **Code** tab, choose
  **Local**, pick your `job-scout` folder, and choose **Opus 5.5** (with **medium** effort if you're asked). Type
  **Set me up**. When Claude asks to run commands in the folder, allow them.
- **Codex:** open the Codex app, open your `job-scout` folder, choose **GPT 6.1 Sol** on **medium** reasoning, and
  type **Set me up**.

The scout needs Python 3, which most Macs already have. If it's missing, the agent will tell you and help you install
it.

### B4. Your schedule

The agent asks which days and time you'd like a fresh shortlist, then sets it up with you:

- **Claude:** in the desktop app's **Code** tab, go to **Routines**, tap **New routine**, and choose **Local**. Use
  `ROUTINE.md` as the instructions and your `job-scout` folder, then set your days and time. The agent can also
  create it for you if you ask in a desktop session. Tap **Run now** once and choose **Always allow** for each
  permission it asks for, so future runs don't stop to ask.
- **Codex:** set up an automation in the Codex app with `ROUTINE.md` as the prompt.

Runs only happen while your computer is on, awake and the app is open. If your computer was asleep at the scheduled
time, Claude does one catch-up run when it wakes. In the Claude app's **Settings → This computer → System**, you can
turn on **Keep computer awake**.

---

## What happens when you say "Set me up"

The agent will:

- explain how Job Scout works, what it scores, and what personal information goes where
- ask about your experience (have your resume ready to paste or attach), what you enjoy, your life goals, what
  matters to you, and what to avoid
- show you how each job is weighted, and let you change the weights
- check that the API key and internet access work
- run your first scout and explain why the top matches scored highly
- set up your schedule and how you'll hear about new shortlists.

The model is your choice. Opus 5.5 or GPT 6.1 Sol on medium is recommended because it gives careful results without
using up your plan quickly. Each run uses some of your plan, so twice a week is a good start.

## Email or notification

The agent asks how you'd like to hear about a new shortlist:

- **Email to yourself (Claude, either route):** each run sends the shortlist from your Gmail to your own Gmail.
  Connect Gmail once at [claude.ai/customize/connectors](https://claude.ai/customize/connectors) (choose **Gmail**
  and sign in). For route A, keep **Gmail** ticked under **Connectors** in your routine. The scout only sends that
  one email to you. It doesn't read your inbox. This is the best way to get route B's results on your phone.
- **Notification in the app:** for route A, each run appears as a new session in the Claude app's **Code** tab, or
  as a task in Codex. For route B, it appears in the desktop app. **Turn notifications on** for the Claude or
  ChatGPT app so you notice it:
  - **iPhone:** **Settings → Notifications → Claude** (or ChatGPT), then turn on **Allow Notifications**.
  - **Android:** **Settings → Apps → Claude → Notifications**.
  - **Mac:** **System Settings → Notifications**.

## Later on

Open Job Scout in your app and just ask, for example:

- "Run my job scout now."
- "Update my profile: I'd also consider product roles."
- "Make impact count for more."
- "Why did the Canva role score 82%?"
- "I've applied for the Atlassian one. Stop showing it."
