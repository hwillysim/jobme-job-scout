# Job Scout

Your own AI job scout. On the days you choose, it reads the job boards of 150+ Australian employers, searches the web
for more roles, and has the JEV scoring service rate each one against your profile. You get a shortlist of your best
new matches, with a note on why each one fits.

**To get started, follow [SETUP.md](SETUP.md).** You need a Claude Pro or Max plan (or ChatGPT with Codex), a free
GitHub account and a JEV API key. No technical knowledge is needed: SETUP.md walks through every step.

[PRIVACY.md](PRIVACY.md) explains where your personal information goes. JEV never receives your name or contact
details.

## How it works

1. **Setup.** You open your copy of Job Scout in Claude Code (or Codex) and say "Set me up". The agent follows
   [AGENTS.md](AGENTS.md): it explains how Job Scout works, interviews you, writes your `profile.json`, agrees the
   weights in `config.json` with you, and runs your first scout.
2. **Scheduled runs.** A Claude routine (or Codex automation) runs [ROUTINE.md](ROUTINE.md) on your schedule. It
   searches the web, runs `job_scout.py`, reviews the best new matches and saves everything to your private copy.
   The shortlist arrives by email or in the app, whichever you prefer.
3. **Scoring.** JEV rates each role from 0 to 100 on seven questions: experience match, target fit, enjoyment,
   practicality, what you want, growth and impact. Job Scout combines them using your weights. Roles that fail any
   of five yes/no checks are dropped: not a real vacancy, a location you've ruled out, a kind of role you want to
   avoid, the wrong level, or a credential you don't have. Roles scoring 65% or more that you haven't seen before
   make the shortlist.

## Commands

```sh
python3 job_scout.py check                       # is the JEV key working, and can job boards be reached?
python3 job_scout.py run                         # gather, score and report
python3 job_scout.py run --web web-finds/DATE.json
python3 job_scout.py dismiss JOB_ID              # never show this role again
python3 job_scout.py discover "Employer name"    # find an employer's job board and add it
python3 -m unittest -q test_job_scout
```

Your data lives in `profile.json`, `config.json`, `data/jobs.sqlite` (the history that stops roles being scored or
shown twice) and `reports/`. Keep your copy private.
