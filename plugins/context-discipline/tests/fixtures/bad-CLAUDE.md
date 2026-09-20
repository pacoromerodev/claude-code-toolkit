# Project instructions

IMPORTANT: Always handle errors properly and make sure the code is clean.
CRITICAL: You MUST ALWAYS write good tests. This is MANDATORY.
NEVER write bad code. IMPORTANT: follow best practices at all times.
ALWAYS use appropriate logging. This is REQUIRED.
IMPORTANT: NEVER skip this. CRITICAL: you MUST ALWAYS verify. MANDATORY.
IMPORTANT: ALWAYS check. NEVER assume. This is CRITICAL and REQUIRED.

Don't use field injection.

Avoid long methods.

The service layer exists because when we originally built this system back in the early days we had a monolith and we needed somewhere to put the business logic that wasn't the controller, and over time that layer grew to include a lot of things that arguably belong elsewhere, but for historical reasons they stayed, and so today the service layer is where most of the interesting code lives and you should generally look there first when trying to understand how something works.

@missing-file.md
