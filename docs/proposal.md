# UOS Inventory Manager — proposal and next steps

15 October 2026 · Justin van Dijk

_Snapshot of the shared Claude doc; edit the doc, not this file, and re-export if it changes._

## What it is

A web app, already built and running, that tracks donated or bought clothing and kit from the moment it arrives to the moment it is handed to someone on a walk. Volunteers use it on their phones, with nothing to install. I propose we agree the rules and a short data agreement, then try it on the Waterloo route (see Next steps).

## What do we need?

The first question is not which tool, but how we want to run outreach. Agree the list below, then check every option against it. If the commercial system UOS already pays for does all of this without workarounds, we should use it: the goal is a better experience for volunteers and the people we support, not this particular app.

The test for any tool: does it fit how we work, or do we change how we work to fit it? Workarounds (a spreadsheet next to the system, a manual check someone has to remember) are where requests get lost and people wait longer than they should.

| What we need | Why it matters | UOS app | Commercial system |
| --- | --- | --- | --- |
| Reserve an item for a named person, on a route, for a walk date | Volunteers promise items on the walk; the promise has to be recorded | Yes | Not yet checked |
| Packing list per walk and route, ticked off as items are packed | Whoever packs needs one list, not a scroll through stock | Yes | Not yet checked |
| See today's collections and mark items collected, on a phone | This happens on the street, often in the cold | Yes | Not yet checked |
| Re-assign on the walk when an item goes to someone else | Happens every week; the original person must not be forgotten | Yes | Not yet checked |
| Cancel a reservation, item straight back to stock | People's needs change | Yes | Not yet checked |
| Missed collections: one grace week, then back to stock automatically | Stops items being held forever for people we no longer see | Yes | Not yet checked |
| Fair queue for scarce items (phones, SIMs, tents, sleeping bags) | First come, first served, assigned automatically when stock arrives | Yes | Not yet checked |
| Queue stays current: requests lapse unless confirmed every 4 weeks | No months-old requests nobody can vouch for | Yes | Not yet checked |
| Quick filters by category, size and route | Finding a men's L coat in seconds, not minutes | Yes | Not yet checked |
| Volunteer sign-up with admin approval; admin and volunteer roles | Only approved people see names of the people we support | Yes | Not yet checked |
| Overview: stock, shortfall for scarce items, items handed out | Donor appeals and reports to funders | Yes | Not yet checked |
| UOS controls the data and can change the rules | Data protection, and adapting as the service changes | Yes | Not yet checked |

The last column is for whoever knows the commercial system best to fill in. "Workaround needed" means a manual step outside the system.

## Why it fits UOS

The app was built around how the walks actually run, so everything in the list above is part of the design rather than added on afterwards.

- **Fair queues for scarce items.** Today someone can wait months for a phone while a newer request gets the one that happens to arrive. In the app, the person who has waited longest gets it automatically the moment it is added. Volunteers confirm every 4 weeks that the person still needs it, so the queue stays real.
- **Demand you can show donors.** The Overview shows each scarce item's shortfall (e.g. "Phones: 6 waiting, 0 in stock"), which is a specific, ready-made appeal.
- **Nothing slips through.** A missed collection gets one grace week, then the item returns to stock. If an item goes to someone else on the walk, the original person is moved to a replacement, put back in the queue, or recorded as missed. Every action is logged.
- **Built for volunteers on a phone.** Filter by category, size and route in a tap; collection date and route fill themselves in; today's collections have their own tab.
- **Numbers for funders and trustees.** Items handed out, people helped and the missed-collection rate, by month and year, without anyone counting.
- **Changes in days, not contracts.** On 15 October, feedback on size lists, route filters and the admin start page was built, tested and live the same day.
- **Tested.** More than 50 automated checks (queues, lapses, re-assigning, every button) run before every change.

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
