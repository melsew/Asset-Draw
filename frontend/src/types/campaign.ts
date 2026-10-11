export interface Campaign {
  id: string;
  title: string;
  vendor: string;
  prize: string;
  description: string;
  entry_mode: "FREE" | "PROMOTIONAL" | "PURCHASE" | "PAID_ENTRY" | "REFERRAL";
  entries: number;
  max_entries: number;
  status: "ACTIVE" | "DRAFT" | "SCHEDULED" | "ENTRY_CLOSED" | "DRAWING" | "DRAW_COMPLETED" | "COMPLETED" | "SUSPENDED" | "CANCELLED";
  ends_at: string;
  draw_at?: string | null;
  prize_image_url?: string | null;
  entry_price?: number | null;
  vendor_id?: string;
  asset_id?: string;
  prize_value?: number | null;
  city?: string | null;
  prize_category?: string;
}

export interface Entry {
  id: string;
  entry_number: string;
  campaign_id: string;
  campaign_title: string;
  campaign_prize: string;
  status: "ACTIVE" | "ELIGIBLE" | "WINNER" | "CANCELLED";
  created_at: string;
  draw_at?: string | null;
  campaign_status: string;
  prize_image_url?: string | null;
}

export interface DrawVerification {
  draw_id: string;
  campaign_id: string;
  campaign_title: string;
  algorithm: string;
  pool_hash: string;
  seed_commitment: string;
  seed?: string | null;
  canonical_message: string;
  winner_index: number;
  winning_entry_number: string;
  total_entries: number;
  locked_at: string;
  completed_at: string;
  verified: boolean;
}

export interface Vendor {
  id: string;
  legal_name: string;
  display_name: string;
  status: string;
  contact_email?: string;
  contact_phone?: string;
  city?: string;
}

export interface Asset {
  id: string;
  vendor_id: string;
  name: string;
  description: string;
  declared_value: number;
  evidence_url?: string;
  status: string;
  category?: string;
}
