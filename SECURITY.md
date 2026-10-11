# Security policy

## Supported versions

Security fixes go into the latest release and the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately through
[GitHub security advisories](https://github.com/SanTiwari07/NarraReel/security/advisories/new).
Include the steps to reproduce it, the output of `narrareel doctor`, and what an attacker could do with it.

We will reply as soon as we can. Once a fix is released, we credit you in the release notes unless you prefer
not to be named.

NarraReel's web server listens on `127.0.0.1` by default and is meant for your own computer. It refuses to listen on
any other address until you set `NARRAREEL_TOKEN` to a secret; keep that secret private.
