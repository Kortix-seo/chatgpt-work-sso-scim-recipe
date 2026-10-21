# chatgpt-work-sso-scim-recipe

The identity half of the ChatGPT Work comparison, as something you can test instead of read.

Most "open-source alternative" pages stop at "it supports SAML and SCIM". The question an IT lead actually has is narrower: if I enforce SSO, does group sync work, does the first admin still get in, and what breaks at 09:00 on a Monday? This repository is the recipe and the check script for that question on a self-hosted Kortix instance.

## What Kortix supports

- **SAML 2.0** single sign-on.
- **SCIM 2.0** provisioning for users and groups.
- **Group membership from a named claim.** This is where Entra bites: Entra sends **group object IDs** by default, not group names. Until the claim carries what the mappings expect, groups sync as identifiers nobody can read in the admin UI.
- **Enforce SSO** after domain verification. It refuses password sign-in, magic links and email codes for the verified domain, and ends existing sign-ins made another way. Turning it on before the identity provider is proven is how an admin locks themselves out.

## The Entra claim, in order

1. Verify the domain in Kortix first. Enforcement is unavailable until it is verified.
2. In Entra, edit the enterprise application's token configuration and add a group claim. Keep the default (group object IDs) only if your mappings use IDs.
3. Name the claim `memberOf` in Kortix's SSO settings. That is the claim Kortix reads for group membership.
4. Sign in once as the admin who will keep access, through the identity provider, before enforcement.
5. Run the check below. Then enforce.

## Run the check

```bash
SCIM_TOKEN=... python3 verify-identity.py --base https://kortix.example.com
```

It reads the SAML metadata document, calls the SCIM `ServiceProviderConfig` with the token, and exits non-zero for every failure. No dependencies beyond the standard library. Wire it into CI before an enforcement change request and the failure shows up at review time, not at sign-in time.

A quick manual version of the SCIM check, if you want to see it fail first:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $SCIM_TOKEN" \
  https://kortix.example.com/scim/v2/Users?count=1
```

401 means the token is wrong or SCIM is not enabled; 200 with an empty `Resources` list means it works and nobody is provisioned yet.

## Self-host first hour, because identity depends on it

On a fresh instance, until `EMAIL_URL` or `DISABLE_SIGNUP=true` is set, anyone who reaches it can create a confirmed account for any address — including the admin address. Set one of the two on the first run, before you add an identity provider:

```bash
curl -fsSL https://kortix.com/install.sh | bash -s -- --domain kortix.example.com --email ops@example.com
kortix self-host configure
kortix self-host start
kortix self-host doctor
```

`kortix self-host doctor` is the one to keep running until every check passes. Sessions run on sandboxes outside the instance, so the instance has to be reachable from the internet for them to call back; an identity provider that can reach it and a sandbox that cannot is a split-brain you find during the first session, not during setup.

## What this repository will not tell you

- It does not claim parity with any specific ChatGPT Enterprise identity feature. Read OpenAI's own admin documentation for what Work does; read [kortix.com/blog/chatgpt-work-for-enterprise](https://kortix.com/blog/chatgpt-work-for-enterprise) for the comparison with OpenAI's sentences quoted beside each row.
- It does not automate the identity provider side. Entra's UI changes; the five steps above are the order that matters.
- It does not test your recovery path. Do that by hand: remove the only admin from the IdP group and confirm you can still get back in as the instance operator.

Kortix is the open-source AI Operating System: agents, skills, company memory and connectors in one git repository you own. Free to start, free to self-host.

## Licence

MIT.
