# Technical Product Review — Swaflow PRD

## Verdict

Adequate for architecture kickoff after a small set of clarifications. The PRD respects the existing backend constraints and avoids moving critical truth to n8n or IA. The highest implementation risks are provider abstraction, inventory semantics from Meta, tenant provisioning, and operational audit/export.

## High Findings

1. **Tenant provisioning is under-specified.**
   - Location: Product Scope, UJ-003.
   - Risk: V1 commercial launch needs an operational path to create tenants and admins even if the SuperUsuario panel is V2.
   - Recommended fix: declare V1 tenant provisioning as Swateck-operated/manual admin process, with self-service onboarding and SuperUsuario operations panel in V2.

2. **Payment gateway abstraction needs a V1 contract.**
   - Location: FR-110, FR-154, FR-145/146.
   - Risk: "cliente puede implementar la pasarela que desee" can explode scope unless V1 defines an adapter model.
   - Recommended fix: define a provider adapter contract: create payment link, expiration, webhook validation, status mapping, idempotency key/reference, refund/failed/expired semantics if supported.

## Medium Findings

1. **Meta availability may not equal reservable quantity.**
   - Location: FR-045 to FR-052.
   - Risk: If Meta provides availability status but not stock quantity, Swaflow's reservation math needs a local quantity source or conservative behavior.
   - Recommended fix: specify supported availability shapes: numeric quantity when available; otherwise availability status; if quantity is unknown, IA can show product but backend should avoid quantity-based reservation beyond configured rules.

2. **Export package needs minimum data set.**
   - Location: FR-160.
   - Risk: Support/offboarding will be ambiguous.
   - Recommended fix: minimum export includes contacts, conversations/messages, orders, payments metadata, appointments, events, products snapshot, inventory/reservations, user activity/audit, integration configs without secrets, and uploaded assets.

3. **Calendar availability needs timezone and conflict rules tied to tenant config.**
   - Location: FR-147 to FR-166.
   - Risk: Good defaults exist, but architecture needs conflict granularity.
   - Recommended fix: state that proposals use tenant timezone, avoid overlaps with existing citas/calendar events, and honor duration configured in Citas.

## Low Findings

1. **FR ID ordering should be normalized before epics.**
2. **Discovery intake should be demoted before final publication.**

