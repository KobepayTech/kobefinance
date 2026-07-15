# Code signing

The release workflow (`.github/workflows/build-release.yml`) builds installers
for **Windows, macOS and Linux** and has signing steps wired in for each. Every
signing step is **gated on repository secrets** — until you add them, builds
still succeed and produce *unsigned* installers. Add the secrets and the next
build is signed, with no workflow changes.

> Status today: **unsigned**. No signing secrets are configured, so users see
> the usual first-run warnings (Windows SmartScreen, macOS Gatekeeper). Adding
> certificates removes those.

## Windows (Authenticode)

Signs both the app `.exe` and the installer `.exe` with `signtool` + RFC-3161
timestamping.

Get a certificate: buy a **code-signing certificate** from a CA (Sectigo,
DigiCert, SSL.com, …). OV certs are cheapest; **EV** certs clear SmartScreen
reputation immediately. You receive a `.pfx`/`.p12` file and a password.

Set these repo secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
| --- | --- |
| `WINDOWS_CERT_BASE64` | `base64 -w0 cert.pfx` (the .pfx, base64-encoded) |
| `WINDOWS_CERT_PWD` | the .pfx password |

```bash
base64 -w0 cert.pfx    # copy output into WINDOWS_CERT_BASE64
```

## macOS (Developer ID + notarization)

Signs the `.app` with a **Developer ID Application** certificate (hardened
runtime), builds the `.dmg`, then notarizes and staples it with Apple.

Prerequisites: an **Apple Developer Program** membership ($99/yr).

1. Create a *Developer ID Application* certificate; export it from Keychain as a
   `.p12` with a password.
2. Create an **App Store Connect API key** (Users and Access → Integrations →
   Keys) with the *Developer* role. You get a `.p8` file, a Key ID, and an
   Issuer ID.

Set these repo secrets:

| Secret | Value |
| --- | --- |
| `MACOS_CERT_BASE64` | `base64 -i cert.p12` (Developer ID .p12, base64) |
| `MACOS_CERT_PWD` | the .p12 password |
| `MACOS_SIGN_IDENTITY` | e.g. `Developer ID Application: Your Name (TEAMID)` |
| `AC_API_KEY_ID` | App Store Connect API Key ID |
| `AC_API_ISSUER_ID` | App Store Connect Issuer ID |
| `AC_API_KEY_BASE64` | `base64 -i AuthKey_XXXX.p8` (the .p8, base64) |

Signing runs when `MACOS_CERT_BASE64` is set; notarization additionally requires
the `AC_*` secrets. Without them the DMG is built unsigned.

## Linux

There is no OS-level executable signing equivalent. The build publishes
`SHA256SUMS-linux.txt` so users can verify integrity. (Optional future step:
GPG-sign the checksums and/or ship an AppImage with embedded signature.)

## Verifying

- **Windows**: right-click the `.exe` → Properties → Digital Signatures, or
  `signtool verify /pa file.exe`.
- **macOS**: `codesign --verify --deep --strict file.app` and
  `spctl -a -t open --context context:primary-signature file.dmg`.
- **All**: `sha256sum -c SHA256SUMS-<platform>.txt`.
