# Owner TODO

Local commits on `rebuild` are authorized. Do not push. There is no remote
configured for this work.

## PART 4 approval gate

Do not start PART 4 until the owner sends the exact phrase:

```text
PREFERENCES APPROVED
```

Before approving, review `config/preferences.draft.yaml` and save the approved
version as `config/preferences.yaml`. The draft is not executable preferences
and must not be copied automatically.

PART 4, once approved, is limited to:

- Up to 25 Tier 1/2 companies, preferring known-ATS hosts.
- At most 1 request per second per host and a 300-request total cap.
- Respect robots.txt; skip a host after repeated 403 or 429 responses.
- Verify each adapter against a real response; keep it UNVERIFIED if it differs.
- The scope may widen by 25 more companies only under the later approved process.
- Never pad the candidate list, use placeholder data, or relax the score floor.
- No automatic applications or submissions.

The current correction explicitly does not authorize PART 4 or any LIVE
network requests.

## Remaining owner inputs

- Supply real labels before requesting real A-048 labeling.
- Decide the Batch 3 disposition of backups, the local starter workbook,
  browser_profile, proofs, and add_companies.py. No permanent deletion is
  allowed without an explicit decision.
- Review the adapter endpoint assumptions before authorizing any LIVE checks.
- G6 deletion decision: default is no deletion.
- Remove any Telegram keys from protected config.yaml manually; this repository
  must not edit that protected file.
- Approve terms separately for each open-feed candidate before any adapter is
  implemented or used.
- Set owner_has_account for portals in the local dashboard as applicable.
- Decide whether to enable the contract_optional Freelance/Contractor keywords.
- Review whether the keyword groups should later be connected to role relevance;
  they currently populate the checklist only.
- Provide real labels for approximately 50 jobs before real A-048 labeling.
