# Preferences draft (NOT APPROVED)

This is a draft derived from `config/preferences.example.yaml`. It is not the owner's
real preference file. Scoring tests use the example file only.

To approve the draft, the owner must reply with the exact line:

```text
PREFERENCES APPROVED
```

Until then, Stage F stops here and PART 4 must not start.

## Draft values

| Setting | Draft value |
|---|---|
| Accepted roles | software engineer, software developer, developer, programmer, SDE, frontend, backend, full stack, data engineer, ML engineer, DevOps, site reliability, QA engineer, automation engineer, intern |
| Excluded titles | senior, staff, principal, architect, manager, director, head of, sales engineer, support engineer, civil engineer, mechanical engineer |
| Required skills | python, javascript, typescript, node.js, react, java, C++, C#, .NET, SQL, git |
| Preferred skills | docker, kubernetes, AWS, postgresql, mongodb, redis, fastapi, django, express, REST API |
| Experience ceiling | 2 years |
| Acceptable levels | internship, fresher, 0-1, 1-2 |
| Countries | IN |
| Cities | Bengaluru, Bangalore, Hyderabad, Pune, Chennai, Noida, Gurugram, Remote |
| Weights | role 30, skills 25, experience 20, location 10, education 5, tier 5, recency 5 |
| Daily quota | 30 total |
| Per-tier quota | Tier 1: 10, Tier 2: 10, Tier 3: 7, Tier 4: 3 |
| Per-company quota | 2 |
| Thresholds | auto 70, manual 50 |

## Questions for the owner

1. Are the accepted/excluded role lists correct?
2. Is the 2-year experience ceiling correct?
3. Should remote outside India be allowed, rejected, or case-by-case?
4. Are the per-tier quotas correct?
5. Should internships count toward the daily quota?
6. Is the education weight of 5 acceptable, or should education be zero?
7. Is the auto-apply threshold 70 too high or too low? (Auto-apply is still not implemented.)
8. Should any company be permanently suppressed?
9. Should Keka/Zoho stay disabled?
10. Should the dashboard remain loopback-only?
