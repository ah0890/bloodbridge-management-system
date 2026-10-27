# Public data sources review

Reviewed 2026-10-27. The goal was to find authoritative, reusable data on Pakistani blood banks, hospitals or blood availability (spec §3.3). Searches were made through a web search tool; no site was scraped.

## Findings

| Source | Owner | Content | Access / licence | Live inventory? | Decision |
|---|---|---|---|---|---|
| [PBTA licensed blood banks list (PDF, Feb 2020)](https://pbta.punjab.gov.pk/system/files/LIST_OF_LICENSED_BLOOD_BANKS_29-02-2020.PDF) | Punjab Blood Transfusion Authority (Govt. of Punjab) | Names, addresses, districts and licence numbers of licensed blood banks in Punjab | Published PDF. No stated reuse licence and no API. About six years old. PBTA's own [newsletter](https://pbta.punjab.gov.pk/system/files/Newsletter.pdf) says its database of establishments is incomplete. | No | Not imported. Re-use needs PBTA's permission and a current list. |
| [opendata.com.pk health facility datasets](https://opendata.com.pk/dataset/pakistan-health-facility-locations/resource/d6235118-cef1-4753-a6f4-4bef51e562b7) | Third-party portal; several datasets appear to be OpenStreetMap-derived | Facility names, types and coordinates | Listed as "No License Provided". Official status unconfirmed. | No | Not imported. Terms are unclear, and it's facilities, not blood banks. |
| Safe Blood Transfusion Programme regional blood centres ([GIZ](https://giz.de/en/worldwide/18027.html), [Dawn](https://dawn.com/news/1160087/four-regional-blood-transfusion-centres-to-be-ready-by-september), [Tribune](https://tribune.com.pk/story/1111146/safe-blood-transfusion-work-second-phase-project-june?amp=1)) | Ministry of NHSR&C / provincial health departments, GIZ-supported | News reports and programme pages only. Counts are partial and conflicting. | No dataset | No | Not used. |

## Conclusion

- No source found publishes **live blood inventory**. BloodBridge must never claim real-time availability.
- The organisation directories found are either stale PDFs with no reuse licence or unlicensed third-party CSVs. None is suitable for automatic integration.
- BloodBridge therefore ships with:
  1. **Synthetic demo data**, clearly labelled everywhere (`provenance = synthetic`).
  2. An **authorised import interface** (CSV/JSON, planned for Milestone 6). Administrators can load organisation or inventory data they have permission to use. Each import records the source name, licence and provenance (`imported`), and rows are validated before they're accepted.
- City coordinates in the demo generator are approximate city-level centroids from general public geography. They're used only to rank synthetic donors by distance. Synthetic organisations are never placed on a map.

## Next steps toward real data (requires the project owner)

1. Ask PBTA and the provincial blood transfusion authorities (Sindh, KP, Balochistan) for a current, machine-readable list of licensed establishments and permission to reuse it.
2. Agree data-sharing terms with each participating blood bank before importing any inventory.
3. Import with `provenance = imported` and verify organisations before setting them to `verified`.
