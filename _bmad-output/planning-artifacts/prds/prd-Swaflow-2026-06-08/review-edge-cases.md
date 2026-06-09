# Edge Case Review — Swaflow PRD

## Verdict

The PRD covers major happy paths and several failure paths. Remaining edge cases are mostly operational and integration-bound, not conceptual.

## High Findings

1. **One additional user auto-assignment can surprise tenants.**
   - Location: FR-021.
   - Risk: If exactly one additional user exists, all chats go to that user by default, even if admin expects shared visibility or temporary user coverage.
   - Recommended fix: add admin override and visibility: admin can disable auto-assignment, reassign, and see all chats.

## Medium Findings

1. **IA reactivation context needs boundary rules.**
   - Location: FR-014.
   - Risk: Reactivating IA after human intervention should not cause it to contradict human promises or repeat the welcome funnel.
   - Recommended fix: state that IA must summarize/reuse recent human context, avoid re-running welcome when already completed, and respect commitments recorded in the chat only when they do not violate backend truth.

2. **Payment expiry follow-up needs cadence limit.**
   - Location: FR-145.
   - Risk: IA could spam follow-ups after expiry.
   - Recommended fix: add a configurable or default follow-up limit, e.g. one follow-up after expiry unless customer responds.

3. **Appointment options in different days can fail in sparse availability.**
   - Location: FR-150, FR-166.
   - Risk: In the next 7 days there may be fewer than three distinct days available.
   - Recommended fix: define fallback: propose fewer options with clear message, or allow multiple slots same day if configured.

## Low Findings

1. **Manual chat reassignment should notify or visibly update the previous assignee.**
   - Location: FR-026.
   - Recommended fix: require realtime update/notification when admin reassigns.

2. **Users with access to Products but not WhatsApp may see Meta sync status but not credentials.**
   - Location: Roles/Productos.
   - Recommended fix: clarify read-only catalog visibility vs WhatsApp configuration access.

