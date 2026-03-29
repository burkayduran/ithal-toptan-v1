/**
 * Campaign domain utilities — pure functions, no side effects.
 */
import type { Campaign } from "@/features/campaigns/types";

/**
 * Returns true only when the campaign's real participant count
 * meets or exceeds its MOQ.
 *
 * This is the canonical check. Do NOT use `status === "moq_reached"` alone
 * because DB state can be inconsistent (e.g. stale data, manual transitions).
 * Callers that need a boolean for badges, CTAs, and section grouping
 * should use this function.
 */
export function isCampaignReached(campaign: Campaign): boolean {
  if (campaign.moq == null || campaign.current_participant_count == null) {
    return false;
  }
  return campaign.current_participant_count >= campaign.moq;
}
