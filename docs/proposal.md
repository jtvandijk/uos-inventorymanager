# UOS Inventory Manager — proposal and next steps

15 October 2026 · Justin van Dijk

_Snapshot of the shared Claude doc; edit the doc, not this file, and re-export if it changes._

## What it is

A web app, already built and running, that tracks donated or bought clothing and kit from the moment it arrives to the moment it is handed to someone on a walk. Volunteers use it on their phones, with nothing to install. I propose we agree the rules and a short data agreement, then try it on the Waterloo route (see Next steps).

## Why it fits UOS

Generic inventory tools count stock. This one tracks a specific item for a specific person on a specific walk, with rules built around how outreach actually works.

- **Reservations by person, route and date.** A volunteer meets someone on Monday and reserves a coat for next Monday's walk.
- **Run sheet.** Whoever packs gets a per-walk list and ticks items off as they go in the bag.
- **A grace week for missed collections.** First miss: the reservation moves to the same walk next week. Second miss: the item goes back to stock. Nothing sits reserved forever, and nobody loses out over one missed week.
- **Re-assign on the walk.** If an item goes to someone else, the app finds an identical replacement or records the miss.
- **Queue for scarce items** (tents, sleeping bags, backpacks, phones, SIMs). First come, first served; items are assigned automatically when stock arrives; requests lapse if not confirmed within 4 weeks.
- **Accountability.** Activity log, missed-collections report, and volunteer sign-up with admin approval.

## Cost and value

Running cost is about $6 (≈ £5) a month for the server, plus a few dollars a month for daily backups. Commercial inventory and CRM tools mostly charge per user per month, and none do the queue and grace-week rules without paid customisation.

- **Replacement value: roughly £15k.** That is what commissioning it from a freelance developer would cost (about 30–40 days of work at UK rates). It is offered free.
- **UOS owns it.** No vendor lock-in, the data belongs to UOS, and rules can be changed when they don't fit.
- **Insight.** It shows what is requested, missed and running low, which supports targeted appeals ("we need sleeping bags").

## Risks and how we'd handle them

The biggest risk is people, not technology: one maintainer, and volunteers needing to use it on every walk.

| Risk | How we'd handle it |
| --- | --- |
| One volunteer maintains it | Code is on GitHub and documented, so any Django developer could take it over. |
| The trial runs on my personal server | Covered by the data agreement (see Next steps). If we continue, UOS rents its own server and I move everything across. |
| It holds names of people we support, plus volunteer contact details | UOS is the data controller. First name and initial only, no sensitive details in notes, and automatic deletion of old data. |
| Data loss | Daily server backups, plus a nightly offsite copy of the database (a single file). |
| Something breaks quietly | A free uptime monitor emails me if the site goes down; I check the daily job log regularly. |
| Volunteers don't use it consistently | Short training at the start of the trial; one person on the route owns keeping it up to date. |
| Learning curve for the rules | Start with the basics (reserve, pack, collect); the rest runs automatically. |

Domain: the trial can use the app's current address. If we continue, a subdomain of the UOS website (e.g. inventory.underoneskytogether.com) needs only one DNS record from whoever manages the domain, however the main site is hosted.

## Potential next steps

Agree the first three, then run Waterloo through the app for 2–3 months on my existing server.

1. **Agree the functionality for the trial.** Which rules stay on (grace week for missed collections, special-request queue, request lapses) and which logs UOS wants (activity log, missed collections). Fewer rules is fine for a first trial.
2. **Sign a short data agreement between UOS and me.** One page that protects both of us, mostly UOS:
   - UOS is the data controller; I hold the data only on UOS's behalf.
   - What is stored, where (UK or EU server), and who can access it.
   - I tell UOS straight away if something goes wrong; UOS has 72 hours to decide whether to report it to the ICO.
   - At the end, the data moves to a UOS server or is deleted, backups included.
3. **Build retention into the app.**
   - Volunteer accounts unused for 6 months are deleted automatically.
   - Names on old reservations and requests are removed after an agreed period.
   - Volunteers record sizes and preferences in notes, never health or immigration details.
4. **Run the Waterloo trial**, replacing the Google Form for that route rather than running alongside it.
5. **Review together** and decide whether to extend, change or stop. If we continue, move to a UOS-owned server and subdomain.

**What success looks like**

- All Waterloo reservations and requests go through the app, not the Google Form.
- Missed collections and outstanding requests are visible each week.
