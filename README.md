# Job Scout

Your own AI job scout. On the days you choose, it reads the job boards of 160+ Australian employers and searches the
web for more roles. It has the JEV scoring service rate every role against your profile, then sends you a short
list of your best new matches, with a note on why each one fits.

**To get started, follow [SETUP.md](SETUP.md).** You'll need a Claude Pro or Max plan (or ChatGPT with Codex) and a
JEV API key. It runs in the cloud on your own private copy on GitHub (a free account; SETUP.md explains everything,
no technical knowledge needed).
[PRIVACY.md](PRIVACY.md) explains what personal information goes where; JEV never gets your name or contact details.

## How it works

1. **Setup:** you open your copy of Job Scout in Claude Code (or Codex) and say "Set me up". The agent follows
   [AGENTS.md](AGENTS.md): it explains everything, interviews you, writes your `profile.json`, agrees the weights in
   `config.json` with you, and runs your first scout.
2. **Scheduled runs:** a Claude routine (or Codex automation) runs [ROUTINE.md](ROUTINE.md) on your schedule. It
   searches the web, runs `job_scout.py`, reviews the best new matches and saves everything to your private GitHub
   copy.
   It then emails you, or leaves the result in the app.
3. **Scoring:** JEV rates each role from 0 to 100 on seven questions: experience match, target fit, enjoyment,
   practicality, what you want, growth, and impact. Job Scout takes the weighted average using your weights. It
   also drops roles that fail any of five yes/no checks: not a real vacancy, a location you've ruled out, a kind of
   role you want to avoid, the wrong level, or a credential you don't have. Roles at 65% or more that you haven't
   seen before make the shortlist.

## Commands

```sh
python3 job_scout.py check                       # is the JEV key working, and can job boards be reached?
python3 job_scout.py run                         # gather, score and report
python3 job_scout.py run --web web-finds/DATE.json
python3 job_scout.py dismiss JOB_ID              # never show this role again
python3 job_scout.py discover "Employer name"    # find an employer's job board and add it
python3 -m unittest -q test_job_scout
```

Your data lives in `profile.json`, `config.json`, `data/jobs.sqlite` (history, so roles aren't scored or shown
twice) and `reports/`. Keep your copy of the repository private.
