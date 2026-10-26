# Set up your Job Scout

Job Scout finds jobs across Australia that suit you and sends you a shortlist on the days you choose. An AI agent
(Claude, or ChatGPT's Codex) does the searching. A scoring service called JEV rates every role against your profile.
[PRIVACY.md](PRIVACY.md) explains what personal information goes where. In short, JEV never gets your name or
contact details.

You don't need any technical knowledge. Setup takes about 30 minutes, then the first scout runs on its own for 20
to 40 minutes. Steps 1 to 5 are easiest on a computer, though a phone's web browser works too. After that, you can
use it all from your phone.

**What you need:**

- **A Claude Pro or Max plan.** Claude is the recommended app. Codex in ChatGPT also works, with the differences
  noted below.
- **The JEV API key from Henry.** He'll send it to you privately. Step 4 explains what it is.
- **About 30 minutes**, and your resume (a Word document, PDF or LinkedIn profile is fine).

---

## Step 1. Create a free GitHub account

**What is GitHub?** It's a website for storing files online, a bit like Google Drive or Dropbox. Job Scout uses it
to keep your profile, settings and shortlists between runs, so it remembers which jobs you've already seen. You won't
need to use GitHub after setup. Claude looks after it for you.

1. Go to **[github.com/signup](https://github.com/signup)**.
2. Enter your email address, choose a password and pick a **username** (for example `jane-smith-jobs`). The
   username is public, so don't use anything you'd mind others seeing.
3. Complete the puzzle that checks you're a person, then tap **Create account**.
4. GitHub emails you a code. Type it in to confirm your email.
5. If it asks questions about how you'll use GitHub, you can skip them. Choose the **Free** plan if asked.

## Step 2. Make your own private copy of Job Scout

Henry has put Job Scout on GitHub as a **template**, which is a starting point you can copy. You'll make your own
copy, which GitHub calls a **repository** (or "repo"). Think of it as a private folder that only you, and the AI
you connect to it, can see.

1. While signed in to GitHub, open **[github.com/hwillysim/jobme-job-scout](https://github.com/hwillysim/jobme-job-scout)**.
2. Tap the green **Use this template** button near the top. On a phone you may need to scroll or turn the phone
   sideways to see it. Then tap **Create a new repository**.
3. On the next page:
   - **Owner:** leave it as your username.
   - **Repository name:** type `job-scout`.
   - Choose **Private**. This is important: your copy will hold your profile and shortlists, and "Private" means
     nobody else can see it.
   - Leave everything else as it is.
4. Tap **Create repository**. You'll see a page listing files such as `SETUP.md` and `job_scout.py`. That's your
   copy. You don't need to do anything with these files.

## Step 3. Connect GitHub to Claude

This lets Claude read and update your private copy.

1. Go to **[claude.ai/code](https://claude.ai/code)** and sign in with your Claude account. (This is Claude Code, the
   part of Claude that can work with files. It's included in Pro and Max.)
2. It asks you to **connect GitHub**. Tap the button and sign in to GitHub if asked.
3. GitHub asks you to **authorise** Claude, then asks which repositories Claude may use. Choose **Only select
   repositories**, pick **job-scout**, and tap **Install** (or **Save**).

You're back in Claude when it's done. The wording on these screens may differ slightly.

**Using ChatGPT instead?** Go to **[chatgpt.com/codex](https://chatgpt.com/codex)**, choose to connect GitHub, and
give it access to **job-scout** in the same way.

## Step 4. Save the API key and switch on internet access

**What's an API key?** Job Scout sends each job ad to JEV, a scoring service run by a company called TypeSafe. JEV
only answers requests that come with a key, which is a long password that looks like a jumble of letters and
numbers. Henry's key is linked to his account, and he pays for what it's used for. So:

- **Don't paste it into a chat, an email or a note.** It only goes in the box described below.
- If it ever ends up somewhere else, tell Henry so he can swap it for a new one.

You'll also give your scout full internet access, so it can read job boards and search the web. Claude keeps these
settings in an **environment**, which is a saved set of settings for your Claude Code sessions.

**In Claude:**

1. At [claude.ai/code](https://claude.ai/code) (or the **Code** tab in the Claude app), go to the screen where you
   start a new session, which has a message box. Just under the message box, tap the first button in the row. This
   is the **environment** picker, and it probably says **Default**.
2. Tap **New environment** at the bottom of the menu.
3. Name it `Job Scout`. Tap **Network access** and choose **Full**. Then tap **Add environment**.
4. Open the picker again and find **Job Scout** under **Cloud** (tap **More** if you can't see it). Tap the small
   settings icon (⚙) on its row.
5. Tap **Network secrets**, then **Add secret**, and fill in:
   - **Name:** `JEV`
   - **Secret type:** leave it as **Bearer**
   - **Allowed websites:** `api.typesafe.ai`
   - **Custom headers:** leave **Name** as `Authorization` and **Prefix** as `Bearer`. Paste Henry's key into
     **Value**.
6. Tap **Add**. The key is now saved. You can't view it again, which is expected. Claude attaches it to requests
   sent to JEV, so even the AI never sees it.

**In Codex (ChatGPT):**

1. At [chatgpt.com/codex](https://chatgpt.com/codex), open **Settings**, then **Environments**, and create an
   environment for **job-scout**.
2. Under **Environment variables**, add one called `JEV_API_KEY` and paste Henry's key as the value. Use
   *Environment variables*, not *Secrets*, because Codex removes secrets before the scout runs.
3. Set **Agent internet access** to **On**, the domain allowlist to **All (unrestricted)**, and allow **all HTTP
   methods**.
4. Save. Codex can see environment variables, but it's told never to show the key.

## Step 5. Start your scout and say "Set me up"

**In Claude:** open the Claude app on your phone (or claude.ai/code) and go to the **Code** tab. Start a new session:

- choose **job-scout** as the repository
- choose **Job Scout** as the environment
- choose **Opus 5.5** as the model (with **medium** effort if it asks)

Then type:

> Set me up

**In Codex:** start a new task on your job-scout environment, choose **GPT 6.1 Sol** with **medium** reasoning, and
type **Set me up**.

From here the agent guides you. It will:

1. explain how Job Scout works, what it scores, and what personal information goes where
2. ask about your experience (paste your resume or attach it), what you enjoy, your life goals, what matters to you,
   and what to avoid
3. show you how each job is weighted, and let you change the weights
4. check the key and internet access work
5. run your first scout and explain why the top matches scored highly
6. help you set up your schedule and choose how you hear about new shortlists (both covered below).

The model is your choice. Opus 5.5 or GPT 6.1 Sol on medium is recommended because it gives careful results without
using up your plan quickly.

## Step 6. Choose your schedule

The agent asks which days and time you'd like a fresh shortlist (for example Monday and Wednesday at 7:30 am). Each
run uses some of your plan, so twice a week is a good start. Then it walks you through this:

**In Claude:** go to **[claude.ai/code/routines](https://claude.ai/code/routines)** and tap **New routine**. A
**routine** is a task Claude runs by itself on a schedule. Fill it in:

- **Name:** `Job Scout`
- **Instructions:** paste everything from the file `ROUTINE.md`. The agent will show it to you to copy.
- **Model:** the one you chose
- **Repository:** **job-scout**
- **Environment:** **Job Scout**
- **Trigger:** **Schedule**, with your days and time. Pick a few minutes past the hour, such as 7:37, because runs
  on the hour can start a little late.
- **Connectors:** remove everything except **Gmail** if you want email (see step 7), or remove them all.

Tap **Create**. To test it straight away, tap **Run now** on the routine's page.

**In Codex:** if your plan offers scheduled tasks (automations), the agent helps you set one up. If it doesn't, just
say **run my job scout** whenever you want a fresh shortlist.

## Step 7. Email or notification

The agent asks how you'd like to hear about a new shortlist:

- **An email to yourself (Claude):** each run sends the shortlist from your Gmail to your own Gmail. Connect Gmail
  once at [claude.ai/customize/connectors](https://claude.ai/customize/connectors) (choose **Gmail** and sign in),
  and keep **Gmail** ticked under **Connectors** in your routine. The scout only sends that one email to you. It
  doesn't read your inbox.
- **A notification in the app:** each run appears as a new session in the Claude app's **Code** tab (or as a task in
  Codex). **Turn notifications on** for the app so you notice it:
  - **iPhone:** **Settings → Notifications → Claude** (or ChatGPT), then turn on **Allow Notifications**.
  - **Android:** **Settings → Apps → Claude → Notifications**.

## Later on

Open a new session on **job-scout** in the Claude app's **Code** tab and just ask, for example:

- "Run my job scout now."
- "Update my profile: I'd also consider product roles."
- "Make impact count for more."
- "Why did the Canva role score 82%?"
- "I've applied for the Atlassian one. Stop showing it."

You never need to touch GitHub yourself. Claude saves everything to your private copy as it goes.
