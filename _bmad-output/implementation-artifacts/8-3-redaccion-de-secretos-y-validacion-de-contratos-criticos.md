---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.3: Redaccion de secretos y validacion de contratos criticos

Status: done

## Story

Como operador del sistema,
Quiero que las integraciones criticas redacten secretos y validen contratos antes de activarse,
Para que auditoria, logs y respuestas no expongan credenciales ni acepten configuraciones invalidas.

## Acceptance Criteria

1. Dado que una integracion, pasarela de pago o webhook se crea o actualiza con campos sensibles, cuando el backend persiste la mutacion o registra auditoria, entonces ningun secreto queda en texto plano en la base de datos, en audit logs o en respuestas API.
2. Dado que un payload contiene `credentials`, `secret_token`, `verify_token`, `access_token`, `private_key`, `client_secret`, `api_key` o `signature`, cuando se serializa para auditoria o exportacion, entonces esos valores se redaccion de forma recursiva y solo quedan indicadores seguros como `credentials_configured`, `secret_configured` o `app_secret_configured` cuando aplique.
3. Dado que una integracion de pagos se crea o actualiza sin proveedor, con TTL invalido, con proveedor no soportado o con un proveedor local en produccion, cuando el backend valida el contrato, entonces rechaza la mutacion con 422 y no persiste credenciales invalidas.
4. Dado que una integracion de calendario se crea o actualiza con proveedor invalido, alias no soportado o credenciales insuficientes, cuando el backend valida el contrato, entonces rechaza la mutacion con 422 y normaliza solo configuraciones validas.
5. Dado que una cuenta de WhatsApp se crea o actualiza con `verify_token` faltante o con una combinacion invalida de datos tecnicos, cuando el backend procesa el payload, entonces rechaza la mutacion y solo almacena el secreto cifrado necesario para operar.
6. Dado que un usuario lee la configuracion operativa o un export al retiro del tenant, cuando consulta integraciones, WhatsApp o webhooks, entonces ve un contrato seguro y honesto sin secretos recuperados en claro.

## Tasks / Subtasks

- [x] Harden secret redaction across critical write paths. (AC: 1, 2, 6)
  - [x] Review `record_audit_best_effort()` usage in integrations, WhatsApp, payments and offboarding paths so no service bypasses the recursive sanitizer.
  - [x] Keep returning derived booleans and safe metadata only (`credentials_configured`, `secret_configured`, `app_secret_configured`) instead of raw secret values.
  - [x] Confirm that any nested secret-like keys inside payload JSON are redacted before audit or export serialization.

- [x] Tighten integration contract validation before persistence. (AC: 3, 4, 5)
  - [x] Reuse `validate_payment_integration_config()` and provider-specific adapter checks for payment create/update flows.
  - [x] Reuse `validate_calendar_integration_config()` and calendar normalization for calendar create/update flows.
  - [x] Keep WhatsApp setup validation strict enough to reject missing or malformed operational tokens before storing the account.
  - [x] Make sure a failed validation does not leave partial secrets written to the database.

- [x] Preserve safe API response shapes. (AC: 1, 6)
  - [x] Verify the read models for integrations, outbound webhooks and WhatsApp setup expose only intentional safe fields.
  - [x] Avoid returning decrypted credentials, private keys or webhook secrets from any list/detail endpoint.
  - [x] Keep the dedicated WhatsApp setup helper aligned with the onboarding flow, but do not leak access tokens or encrypted blobs.

- [x] Add regression coverage for redaction and contract rejection. (AC: 1-6)
  - [x] Add tests that prove integration and webhook audit entries do not contain secret-like keys.
- [x] Add tests that payment integration create/update rejects invalid provider, TTL and prod/local combinations.
- [x] Add tests that calendar integration validation rejects invalid contracts and normalizes valid aliases.
- [x] Add tests that WhatsApp setup/account flows keep secrets encrypted and responses safe.

- [x] Verify the backend slice end to end. (AC: 1-6)
  - [x] Run the targeted backend tests for integrations, WhatsApp setup, payments and offboarding export.
  - [x] Confirm no schema or route contract changed unless a specific redaction fix required it.
  - [x] Confirm MySQL-compatible persistence rules still hold and that SQLite tests remain deterministic.

### Review Findings

- [x] [Review][Patch] Recursive redaction now misses secret-like key variants [backend/app/audit/service.py:31-40]
- [x] [Review][Patch] WhatsApp verify-token field stays locked after phone number changes [frontend/src/App.tsx:8522-8723]
- [x] [Review][Patch] Legacy plaintext WhatsApp verify_token rows can fail update flows [backend/app/whatsapp/service.py:1180-1210]

## Dev Notes

### Business Context

- This is a hardening story. It does not add a new business capability; it closes secret-leak and invalid-contract gaps on already existing flows.
- The main product risk is exposure of operational secrets through API responses, audit metadata, exports or logs.
- The backend remains the source of truth. The fix must happen before persistence or at serialization boundaries, not in the frontend.
- Keep the dedicated operational setup fields that the product currently uses, but never widen exposure beyond what is necessary for onboarding.

### Current Code State

- `backend/app/integrations/service.py` already encrypts `credentials` and `secret_token` on write and uses `_safe_audit_metadata()` to drop top-level secret fields from audit payloads.
- `backend/app/audit/service.py` already redacts sensitive keys recursively by key name fragments, including `secret`, `token`, `signature`, `api_key`, `private_key` and `client_secret`.
- `backend/app/integrations/schemas.py` already exposes safe booleans such as `credentials_configured` and `secret_configured` instead of raw secrets.
- `backend/app/payments/contract.py` already validates provider support, TTL and provider-specific requirements, including Wompi event secrets and production restrictions for local providers.
- `backend/app/integrations/calendar.py` already normalizes provider aliases and requires credentials before a calendar integration can become active.
- `backend/app/whatsapp/service.py` already encrypts `access_token` and validates that a `verify_token` exists, but the response surface still needs to be treated carefully so no decrypted secret escapes outside the intended setup flow.
- `backend/app/whatsapp/schemas.py` and `backend/app/integrations/schemas.py` define the public read models that need to stay secret-free.
- `backend/app/offboarding/service.py` already exports integrations and webhooks with boolean secret indicators only; this is the correct pattern to preserve.
- Existing tests in `backend/tests/test_tenant_and_orders.py`, `backend/tests/test_whatsapp_setup.py` and `backend/tests/test_superadmin_offboarding.py` already cover some secret handling, but the current coverage should be extended to prove there is no regression in redaction or validation.

### Hidden Failure Modes to Prevent

- A nested secret-like field survives because a sanitizer only strips top-level keys.
- A service writes a bad integration payload first and rejects it later, leaving partial credentials persisted.
- A list or detail endpoint accidentally returns decrypted credentials because the response model is built from the ORM object directly.
- A payment integration accepts a provider/config combination that later fails only at runtime.
- A WhatsApp or outbound webhook setup path leaks a token in audit logs or export text.
- The offboarding export remains safe, but a new direct read path leaks what the export already hides.

### Implementation Guidance

- Prefer reusing the existing validators and safe response models instead of creating a second contract layer.
- Keep the secret story backend-only unless a response schema change makes a frontend adjustment unavoidable.
- Redaction should be recursive and defensive, not just a list of keys to pop in one service.
- Validation should happen before commit and before audit write. Do not rely on post-commit cleanup.
- Keep error messages user-facing and actionable, but do not echo secret values back in validation errors.
- Avoid schema churn unless a field is clearly unsafe and cannot be kept as an intentional operational token.

### Project Structure Notes

- Primary targets:
  - `backend/app/integrations/service.py`
  - `backend/app/payments/contract.py`
  - `backend/app/whatsapp/service.py`
  - `backend/app/audit/service.py`
  - `backend/app/offboarding/service.py`
- Secondary targets if validation or response shape needs adjustment:
  - `backend/app/integrations/schemas.py`
  - `backend/app/whatsapp/schemas.py`
  - `backend/app/integrations/routes.py`
  - `backend/app/whatsapp/routes.py`
- Tests should stay close to the affected domains:
  - `backend/tests/test_tenant_and_orders.py`
  - `backend/tests/test_whatsapp_setup.py`
  - `backend/tests/test_superadmin_offboarding.py`
- Do not introduce frontend or routing refactors for this story.

### Testing Standards Summary

- Add regressions for both the rejection path and the persisted-safe path.
- Verify audit metadata, API JSON and export output separately; do not assume one protects the others.
- Keep tests deterministic and MySQL-aware even if they run on SQLite in memory.
- Prefer direct assertions on redacted keys, encrypted columns and safe booleans over string matching alone.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.3 and the acceptance criteria around redacting secrets and rejecting invalid contracts]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - integration, payments, WhatsApp and security requirements]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend remains source of truth and the frontend should not invent data]
- [Source: `_bmad-output/project-context.md` - MySQL decision, SQLAlchemy 2 conventions, encryption rules, and secret handling constraints]
- [Source: `backend/app/integrations/service.py` - create/update integration and webhook write paths]
- [Source: `backend/app/payments/contract.py` - payment provider contract validation and webhook requirements]
- [Source: `backend/app/whatsapp/service.py` - WhatsApp account creation and setup flow]
- [Source: `backend/app/audit/service.py` - recursive secret redaction for audit metadata]
- [Source: `backend/app/offboarding/service.py` - safe export pattern using boolean secret indicators]
- [Source: `backend/app/integrations/schemas.py` - safe integration read models]
- [Source: `backend/app/whatsapp/schemas.py` - WhatsApp setup and account read models]
- [Source: `backend/tests/test_tenant_and_orders.py` - payment and integration validation regressions]
- [Source: `backend/tests/test_whatsapp_setup.py` - WhatsApp setup and account secret handling regressions]
- [Source: `backend/tests/test_superadmin_offboarding.py` - export redaction regressions]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story target resolved from sprint status as `8-3-redaccion-de-secretos-y-validacion-de-contratos-criticos`.
- Reviewed the latest Epic 8 scope, the previous hardening story, and the current backend secret-handling paths before writing the story.
- Confirmed the main risk is not only persistence, but also audit metadata, API responses and export output.
- Hardened integration audit metadata to recursively sanitize nested secret-like keys before recording.
- Added regression coverage for invalid payment/calendar updates, nested audit redaction, and WhatsApp verify-token validation.
- Verified the backend with `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py backend/tests/test_whatsapp_setup.py backend/tests/test_superadmin_offboarding.py -q` and then `backend/.venv/bin/python -m pytest backend/tests -q`.
- Resolved the review finding by encrypting WhatsApp `verify_token` storage, removing it from public read models, and switching the setup response to a safe configuration flag.
- Revalidated the impacted surface with `backend/.venv/bin/python -m pytest backend/tests/test_whatsapp_setup.py -q`, `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py backend/tests/test_superadmin_offboarding.py -q`, `backend/.venv/bin/python -m pytest backend/tests -q`, and `npm run build` in `frontend/`.
- Fixed the follow-up storage issue by changing WhatsApp `verify_token` to text-backed storage and adding a migration so encrypted values fit safely in MySQL.
- Preserved existing WhatsApp `verify_token` values on update when the form does not resend them, which keeps edit flows usable without leaking the secret back to the UI.
- Tightened the nested audit regression so it asserts exact secret-key removal and does not false-positive on safe fields such as `signature_algorithm`.
- Revalidated the backend hardening slice with `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py::test_audit_logs_redact_integration_secrets -q` and `backend/.venv/bin/python -m pytest backend/tests -q`.

### Completion Notes List

- Implemented recursive redaction for integration and outbound-webhook audit metadata so nested secret-like keys are stripped before persistence.
- Kept payment and calendar contract validation paths intact and added regressions for invalid update payloads.
- Added WhatsApp setup regression coverage for invalid `verify_token` input while preserving encrypted storage for access tokens.
- Verified the backend test suite passed with 226 tests.
- Fixed the review finding by encrypting WhatsApp `verify_token` at rest, removing it from `WhatsAppAccountRead`, and exposing only a safe `verify_token_configured` flag in setup responses.
- Updated the frontend WhatsApp form to stop depending on a readable token value and confirmed the production build succeeds.
- Added regression coverage for text-backed verify-token storage and for updating an existing WhatsApp account without resupplying the token.
- Refined the nested audit redaction regression to verify exact key removal while preserving safe fields like `token_count` and `signature_algorithm`.
- Verified the full backend test suite passed with 230 tests.
- Story status set to `review`.

### File List

- `backend/app/integrations/service.py`
- `backend/app/whatsapp/models.py`
- `backend/app/whatsapp/routes.py`
- `backend/app/whatsapp/schemas.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/src/App.tsx`
- `backend/migrations/versions/20260715_0023_whatsapp_verify_token_text.py`
- `backend/tests/test_tenant_and_orders.py`
- `_bmad-output/implementation-artifacts/8-3-redaccion-de-secretos-y-validacion-de-contratos-criticos.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-07-15: Implemented recursive redaction for integration and webhook audit metadata, added contract validation regressions for payments/calendar, and covered WhatsApp verify-token rejection.
- 2026-07-15: Resolved the WhatsApp `verify_token` exposure by encrypting stored values, removing them from read responses, and updating the setup UX to use a safe configuration flag.
- 2026-07-15: Fixed WhatsApp `verify_token` storage length by switching to text-backed persistence, adding a migration, and preserving existing tokens on update when the UI omits them.
- 2026-07-15: Refined the nested audit regression to assert exact secret-key removal without flagging safe fields like `signature_algorithm`, then revalidated the full backend suite.
