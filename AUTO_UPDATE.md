# Automatic contribution updates

The workflow checks the GitHub profile calendar approximately every five minutes.
It reads only the public calendar cells: dates, counts and intensity levels.
To include anonymized private activity, enable **Private contributions** in
the profile's **Contribution settings**. Repository names, source code and
credentials are not read by the calendar updater.

When the calendar changes, GitHub Actions generates a new GIF, saves the assets
as `github-actions[bot]`, and deploys the interactive graph to GitHub Pages.
The bot's generated commits do not add contributions to trynabe's calendar.
Unchanged calendars keep their existing images and update timestamp.

The interactive page checks for a newer published snapshot every minute and
when it regains focus. Refresh the GitHub profile page to load the latest GIF.
GitHub processing, Actions queues, deployment and image caching can add delay.
The five-minute schedule is an update target, not an instantaneous guarantee.

The workflow's write permissions are limited to this profile repository and
its Pages deployment. It does not need a personal access token or read access
to private repositories. Pull requests run checks with read-only permissions.

GitHub may disable schedules on public repositories after 60 days without
repository activity. Failed calendar requests preserve the previous assets;
the next scheduled run retries automatically.
