# Badges branch

Generated Shields.io endpoint JSON, published by `.github/workflows/build-and-release.yml`
on every release. This branch holds **only** these files and carries no source.

It exists because `main` is protected by a required status check, so a release run cannot
push generated metrics there — every attempt was rejected with
`GH006: Protected branch update failed`. Publishing here keeps the badges current without
weakening that protection.

Do not edit by hand; the next release overwrites it.
