# Grok handover

## Two ways Grok works

1. **Automated (preferred): Grok through the xAI API**, run by `.github/workflows/grok.yml`. Its operating instruction is `ops/GROK_SYSTEM_PROMPT.md`, sent with the editorial standards, the live in-stock catalogue and the list of published articles. Drafts and visitor-check findings land in the task register as issues, are validated automatically, and are fact-checked and published by Claude's cloud task. Nobody copies anything between systems.
   - Turned on by one secret, `XAI_API_KEY`, which Steve creates in his xAI developer account. The workflow uses it only to call xAI.
   - Schedule: Tue and Fri news, Wed buying guide, Thu next Monday's Watch of the Week, Sat visitor check. Any task can be run by hand from the Actions tab ("Grok editorial and visitor checks" > Run workflow).
   - Permissions: read the repository, write issues. No code push, no deploy, no other secrets.
2. **Conversational: Grok in Steve's Grok app**, for planning, research questions, customer-reply drafts and reports. Paste `ops/GROK_SYSTEM_PROMPT.md` as its instructions. An article written there can be submitted with the "Editorial submission" issue form. That is optional and needs a GitHub sign-in.

## Why not other routes (checked 17 November 2026)

| Route | Outcome |
| --- | --- |
| Grok's own GitHub account | Grok in the consumer app cannot sign in to sites or make authenticated requests, so an account would sit unused, and creating one needs a human. |
| Claude operating Grok's chat in a browser | xAI's consumer terms prohibit using bots to access the service. Not used. |
| A public web form that creates issues | Needs a server holding a GitHub token, an extra service and a spam risk. Not needed now the API route exists. |
| xAI API from GitHub Actions | Supported, metered, scoped to issues only. **Chosen.** |

## What Grok can reach

| System | Access |
| --- | --- |
| Live site, catalogue (`/data/products.json`), public repository and task register | Read, through web search in the API or browsing in the app |
| Task register | Write, through the API workflow (as issues) |
| Code, hosting, settings, Awin, Analytics, Search Console, email | None, by design |
