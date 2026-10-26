Run my Job Scout. The goal is to gather as many current roles as possible so the JEV scoring service can rate them all, then report only my best NEW matches. Breadth matters more than precision when gathering, because JEV does the judging.

Write in Australian English, in plain, direct sentences: no filler, no opening pleasantries, no closing summary that repeats the content. Keep exact names, URLs and numbers.

You are in a checkout of my private Job Scout copy on GitHub (Python 3, standard library only). Read AGENTS.md, profile.json (my background, the roles I want, what I enjoy, my goals and purpose, what to avoid) and config.json (weights, the 65% threshold, shortlist size, employers to leave out, and how I want the results delivered). Don't change profile.json, config.json or the scoring code. If something about them looks wrong, say so at the end instead.

JEV access: job_scout.py finds the key itself (Claude's cloud adds it to requests; in Codex it is the JEV_API_KEY environment variable). Never look for, open or print the key. My profile goes to JEV without my name or contact details; don't add any to profile.json.

Fair use: gather roles from employers' own public job-board feeds (job_scout.py does this) and from ordinary web searches and page fetches. Don't script the internal or undocumented APIs of job sites such as LinkedIn, SEEK or Indeed, and don't work around blocks. If a site answers 403, 429 or a captcha, move on, and look for the employer's own careers page for the same role.

Steps:

0. Make sure you're on main and up to date: `git checkout main && git pull --ff-only origin main`. If your session can only push to its own claude/ branch, stay on that branch, and first merge the newest run state: run `git fetch origin`, then `git merge` the newest origin/claude/* branch whose last commit starts with "Job Scout run", if main doesn't already contain it. Then run `python3 job_scout.py check`. If JEV isn't working, stop and report that the JEV key needs checking (step 4 of SETUP.md). If the job boards aren't reachable, stop and report that internet access needs switching on.

1. Web sweep. Run at least 30 varied web searches for CURRENT open roles (posted or updated in roughly the last 10 days) that match profile.json target_roles and location. Cover SEEK, LinkedIn Jobs, Indeed AU, recruiter sites, startup and VC job boards, and employers' own careers pages, across the industries and kinds of organisation in my profile. Don't reject roles by title or keyword. Only skip roles that are clearly outside my locations, pages that aren't a specific vacancy, and employers in config.json exclude_employers. Aim for 100+ roles. Where the site allows it, fetch the listing for its description; otherwise use the best search snippet.

2. Save the finds as a JSON list in web-finds/YYYY-MM-DD.json (today's date in config.json schedule.timezone; create the folder if needed). Each item is {"company", "title", "location", "url", "description"}. Prefer the employer's own or job-board URL over an aggregator's.

3. Grow the list of job boards: `python3 job_scout.py discover --file web-finds/YYYY-MM-DD.json`.

4. Run the pipeline: `python3 job_scout.py run --web web-finds/YYYY-MM-DD.json`. It reads every job board, adds your web finds, sends new or changed roles to JEV, writes reports/YYYY-MM-DD.md and reports/YYYY-MM-DD-all-assessed.csv, and tidies the database. It can take 10 to 30 minutes, so let it finish. If it fails, report the exact error and stop. Don't work around authentication.

5. Check each role under "New matches": open the listing. Leave out any role that is filled, closed, a repeat of one already sent under another URL, outside my locations, or one I'm clearly not eligible for. List those in one line under the matches, and run `python3 job_scout.py dismiss ID ...` with their job IDs so they never come back. You may fill their places with the next unreported roles at or above the threshold from the all-assessed CSV, dismissing those too once reviewed.

6. Write a short note for each remaining match, based only on the listing and profile.json:
### N. [Title — Company](url) — score%
One line: when it opened or was checked, if known.
**Why it scored highly:** the two or three JEV ratings that lifted it most (from the "JEV dimensions" line), with their weights from config.json, in one sentence.
**Why it fits:** 2 to 4 bullets linking the role's real responsibilities to specific things in my profile.
**Gaps:** honest gaps (experience, skills, office days, pay if advertised).
**Recommendation:** Apply / Worth a look / Probably skip, with one sentence of reasoning.
Don't invent achievements or claim anything the listing doesn't say.

7. Save the notes as reports/YYYY-MM-DD-review.md, then save the state: `git add data reports sources.json web-finds && git commit -m "Job Scout run YYYY-MM-DD" && git push origin HEAD:main`. The next run relies on this push to avoid repeats. If the push is rejected, retry once after `git pull --rebase origin main`. If it still fails, push to your own claude/ branch and say in plain words that this run's results weren't saved properly, so the next run may repeat some roles.

8. Your final message is what I read on my phone. Output the full review: "## New matches" (or one line saying nothing new cleared the threshold this run), then one closing line with the counts: roles gathered (boards and web), new job boards found, roles sent to JEV, and roles at or above the threshold.

9. Delivery, from config.json "delivery":
- "email": use ToolSearch with the query "gmail send" to load the Gmail connector's send tool (connectors can take a moment to connect, so search rather than assume it's missing). Send exactly one email to delivery.email with the subject "Job Scout D Mon YYYY" and the full review as the body, keeping every link, score and word. Use simple HTML if the tool accepts it. If the run stopped early, still send one email, with the subject "Job Scout D Mon YYYY: run problem" and the problem in a few lines. If no Gmail tool is available, say so in one line at the end of your final message.
- "app" or anything else: send nothing. The final message is the delivery.

I'm not technical: in your final message, don't mention git, commits, branches or pull requests, and never open a pull request.

Never apply for jobs, contact employers or recruiters, or send anything anywhere except JEV calls made by job_scout.py, the git push to this repository, and the one email above. Don't read, reply to, label or delete any email.
