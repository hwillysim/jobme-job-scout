# Set up your Job Scout

Job Scout finds jobs across Australia that suit you and sends you a shortlist on the days you choose. An AI agent
(Claude or ChatGPT's Codex) does the searching. A scoring service called JEV rates every role against your profile.

Setup takes about 20 minutes, plus the first scout, which runs on its own for 20 to 40 minutes. Steps 1 to 4 are
easiest on a computer, or in your phone's web browser. After that, everything works from your phone.

**Claude is the recommended way.** It keeps your API key hidden from the agent, can run on a schedule in the cloud,
and can email you the shortlist. Codex works too, with the differences noted below.

---

## 1. What you need

- **A Claude Pro or Max plan** (for Claude Code in the cloud and scheduled runs). Or, for Codex, **a ChatGPT plan
  that includes Codex**.
- **A free GitHub account.** GitHub is where your copy of Job Scout and your shortlists are kept. Sign up at
  [github.com/signup](https://github.com/signup).
- **The JEV API key from Henry.** He'll send it to you privately. Step 4 explains what it is and where it goes.

## 2. Make your own private copy

1. Sign in to GitHub and open **[github.com/hwillysim/jobme-job-scout](https://github.com/hwillysim/jobme-job-scout)**.
2. Tap **Use this template**, then **Create a new repository**.
3. Name it `job-scout` and choose **Private**. This matters: your copy will hold your profile and your
   shortlists.
4. Tap **Create repository**.

## 3. Connect GitHub to your AI app

**Claude:** go to [claude.ai/code](https://claude.ai/code) and sign in. The first time, it asks you to connect GitHub.
Follow the prompts, and when GitHub asks which repositories Claude can use, choose **Only select repositories**
and pick your `job-scout`.

**Codex:** go to [chatgpt.com/codex](https://chatgpt.com/codex), choose to connect GitHub, and give it access to your
`job-scout` repository.

## 4. Save the API key and switch on internet access

**What's an API key?** Job Scout sends each job ad to JEV, a scoring service run by a company called TypeSafe. JEV
only answers requests that come with a key, which is a long password that looks like a jumble of letters and
numbers. Henry's key is linked to his account, and he pays for what it's used for. So:

- Don't paste it into a chat, an email, a note or a file. **The only place it goes is the box described below.**
- If it ever ends up somewhere else, tell Henry so he can swap it for a new one.

You'll also give your agent full internet access, so it can read job boards and search the web.

### In Claude

1. At [claude.ai/code](https://claude.ai/code) (or the **Code** tab in the Claude app), go to the screen where you
   start a new session. Under the message box, tap the first control in the row. This is the **environment**
   picker, and it probably says **Default**.
2. Tap **New environment** at the bottom of the menu.
3. Name it `Job Scout`.
4. Tap **Network access** and choose **Full**.
5. Tap **Add environment**.
6. Open the picker again and find **Job Scout** under **Cloud** (tap **More** if it isn't shown). Tap the settings
   icon (⚙) on its row to edit it.
7. Tap **Network secrets**, then **Add secret**, and fill in:
   - **Name:** `JEV`
   - **Secret type:** leave it as **Bearer**
   - **Allowed websites:** `api.typesafe.ai`
   - **Custom headers:** leave **Name** as `Authorization` and **Prefix** as `Bearer`. Paste Henry's key into
     **Value**.
8. Tap **Add**. The secret now shows in the list. You can't view the key again, which is expected.

Claude adds the key to requests sent to JEV for you, so the agent never sees it.

### In Codex

1. In [chatgpt.com/codex](https://chatgpt.com/codex), open **Settings**, then **Environments**, and create an
   environment for your `job-scout` repository.
2. Under **Environment variables**, add one: name `JEV_API_KEY`, and paste Henry's key as the value. Use
   *Environment variables*, not *Secrets*. Codex removes secrets before the agent starts, so the scout couldn't
   use it there.
3. Set **Agent internet access** to **On**, the domain allowlist to **All (unrestricted)**, and allow **all HTTP
   methods**. JEV needs more than the read-only methods.
4. Save.

Codex shows environment variables to the agent, so it could see the key. It's told never to print it.

## 5. Start Job Scout and say "Set me up"

**Claude:** open the Claude app, go to the **Code** tab and start a new session. Pick your `job-scout` repository and
the **Job Scout** environment. Choose **Opus 5.5** as the model (with **medium** effort, if you're asked). Then type:

> Set me up

**Codex:** start a new task on your `job-scout` environment and choose **GPT 6.1 Sol** with **medium** reasoning.
Then type **Set me up**.

The agent will:

- explain how Job Scout works and what it scores
- ask about your experience (have your resume ready to paste or attach), what you enjoy, your life goals, what
  matters to you, and what to avoid
- show you how each job is weighted, and let you change the weights
- check that the API key and internet access work
- run your first scout and walk you through the results.

The model is your choice. Opus 5.5 or GPT 6.1 Sol on medium is recommended because it gives careful results without
using up your plan quickly.

## 6. Choose your schedule

The agent asks which days and time you'd like a fresh shortlist (for example Monday and Wednesday at 7:30 am), then
helps you set it up:

**Claude:** go to [claude.ai/code/routines](https://claude.ai/code/routines) and tap **New routine**.

- **Name:** `Job Scout`
- **Prompt:** copy everything in `ROUTINE.md` from your repository. The agent can show it to you.
- **Model:** the one you chose
- **Repository:** your `job-scout`
- **Environment:** **Job Scout**
- **Trigger:** **Schedule**, with your days and time. Pick a few minutes past the hour, such as 7:37, because runs
  on the hour can start a little late.
- **Connectors:** remove everything except **Gmail** (if you chose email in step 7), or remove them all.

Tap **Create**. You can use **Run now** on the routine's page to test it.

**Codex:** if your plan offers scheduled tasks (automations), the agent will help you set one up using `ROUTINE.md`.
If it doesn't, just say **run my job scout** in Codex whenever you want a fresh shortlist.

Each run uses some of your Claude or ChatGPT plan, so twice a week is a good start.

## 7. Email or notification

The agent asks how you'd like to hear about a new shortlist:

- **Email to yourself (Claude):** each run sends the shortlist from your Gmail to your own Gmail. Connect Gmail once
  at [claude.ai/customize/connectors](https://claude.ai/customize/connectors) (choose **Gmail** and sign in), and
  keep **Gmail** ticked under **Connectors** in your routine. The run only sends that one email to you. It doesn't
  read your inbox.
- **Notification in the app:** each run appears as a new session in the Claude app's **Code** tab, or as a task in
  Codex. **Turn notifications on** for the Claude or ChatGPT app so you notice it: on iPhone, go to **Settings →
  Notifications → Claude** (or ChatGPT) and turn on **Allow Notifications**; on Android, go to **Settings → Apps →
  Claude → Notifications**.

## Later on

Open your `job-scout` in the app and just ask, for example:

- "Run my job scout now."
- "Update my profile: I'd also consider product roles."
- "Make impact count for more."
- "Why did the Canva role score 82%?"
- "I've applied for the Atlassian one. Stop showing it."

Your profile, settings and shortlists live only in your private GitHub copy. Your profile is sent to JEV only to
score jobs.
