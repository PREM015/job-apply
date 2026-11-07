# BLOCKED

This file distinguishes offline FIXTURE coverage from LIVE validation. No LIVE
source request or job submission is authorized by this document.

## BLOCKED

- **A-029 - LIVE source spike:** Not run. Network access is prohibited for this
  correction. Adapter endpoints and URL patterns are unverified and were taken
  from memory.
- **A-030..A-033 - LIVE verification:** Offline normalization, validation,
  experience classification, and software classification are implemented;
  real-source verification remains blocked. These IDs are not extra-source
  adapter tasks in the current task board.
- **A-034 - LIVE verification:** The fixture-only work-mode and country
  classifier is implemented, but no real job input has been used.
- **Real A-048 labeling request:** Not completed. The task board assigns A-048
  to scheduler-safe launchers (implemented); the separate owner request for
  real labels is blocked because no owner-provided real labels are available.
- **Batch 3 cleanup:** Blocked pending owner decisions for backups, local
  starter workbook, browser_profile, proofs, and add_companies.py. No files
  were permanently deleted.
- **PART 4 - LIVE proof:** Not started, per owner instruction. It can start
  only after the owner sends the exact phrase `PREFERENCES APPROVED`.

## FAILED / NOT BUILT

- **LIVE adapter verification:** Not built or run because network access is
  prohibited. Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Keka/Zoho,
  JSON-LD, and sitemap endpoints remain UNVERIFIED; configured endpoint
  patterns are from memory.
- **Real A-048 labels:** Not built because real owner labels were not supplied.
- **PART 4 LIVE job proof:** Not built because the owner explicitly prohibited
  starting PART 4 in this correction.
- **Batch 3 destructive cleanup:** Not built because the owner has not chosen
  which listed local files to retain or move. Permanent deletion remains
  prohibited.
- **Search-keyword scoring integration:** Not built; keyword groups populate
  the Saved Alert Checklist only and do not bypass the existing role,
  experience, or score-floor gates.

Offline FIXTURE tests and outputs must never be described as real jobs or
LIVE verification.
