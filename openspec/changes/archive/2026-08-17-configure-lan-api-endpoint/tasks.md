## 1. Client API configuration

- [x] 1.1 Read `API_BASE_URL` from `--dart-define` in `app_core`, preserve the loopback default, and normalize trailing slashes.
- [x] 1.2 Add API client tests covering the default address, configured address, and trailing-slash normalization.

## 2. LAN development server

- [x] 2.1 Add `SERVER_HOST` to server settings and use it from both the direct Python entrypoint and the Makefile Uvicorn command.
- [x] 2.2 Add server configuration coverage and document `SERVER_HOST=0.0.0.0` LAN startup plus `/health/live` verification.

## 3. Android development transport

- [x] 3.1 Allow cleartext HTTP in Android debug and profile manifests only, leaving the main/release manifest unchanged.
- [x] 3.2 Document the complete real-device LAN command using the Mac IP and `--dart-define=API_BASE_URL=...`.

## 4. Verification

- [x] 4.1 Run OpenSpec strict validation and the affected client/server tests.
- [x] 4.2 Run Dart formatting, Flutter analysis, and the client test suites; inspect the final diff for secrets, fixed LAN IPs, and unrelated changes.
