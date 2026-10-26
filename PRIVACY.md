# What personal information goes where

Job Scout asks for your resume and some personal goals so it can judge which jobs suit you. Here's where that
information goes.

| Where | What it gets | Why |
| --- | --- | --- |
| **Your AI app** (Claude or ChatGPT) | Whatever you share in the chat: your resume, your answers, your profile and the job ads it finds. | The agent reads these to build your profile and write the notes on each job. Your plan's usual privacy settings apply. |
| **Your copy of Job Scout** (a private GitHub copy, or a folder on your computer) | `profile.json` (a summary of your background and goals), your settings, the jobs found and your shortlists. | So each run remembers what you've already seen. Your resume file itself is never saved here. |
| **JEV** (the scoring service run by TypeSafe) | Your profile **without** your name or contact details, plus one job ad at a time. | To rate how well each job fits you. |
| **Gmail** (only if you choose email) | The shortlist email, sent from your own Gmail to yourself. | So the shortlist reaches your phone. The scout doesn't read your inbox. |
| **Henry** | Nothing is sent to him. Requests to JEV use his key, so they're recorded against his TypeSafe account. | He shares the key so you don't need your own. |

## What's kept out of JEV

- `profile.json` doesn't store your name, email, phone number, address, date of birth, LinkedIn link or referees.
  The agent is told to leave them out when it writes your profile.
- As a backstop, `job_scout.py` removes those fields from what it sends to JEV. It also blanks out any email
  address, phone number or web link left in the text, for example from a pasted resume.
- What JEV does see is the substance of your profile: your experience (including employer names and dates), skills,
  the roles you want, what you enjoy, your goals, your general location (such as "Sydney"), your level, and what to
  avoid. Someone who knows you well might still recognise a detailed career history. If that matters to you, ask
  the agent to describe past employers in general terms, such as "a big four bank".

## Removing your information

- Delete your GitHub copy (repository **Settings**, then **Danger zone**, then **Delete this repository**), or
  delete the folder on your computer.
- Delete the scheduled run, and any chats about Job Scout, in your AI app.
