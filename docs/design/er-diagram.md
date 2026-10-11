# Asset-Draw Entity Relationship Diagram

Generated from SQLAlchemy model metadata. Regenerate with `python scripts/generate_er_diagram.py`.

```mermaid
erDiagram
    asset_verifications {
        UUID id PK
        UUID asset_id FK
        UUID verified_by FK
        VARCHAR(16) result
        VARCHAR(32) custody_type
        VARCHAR(512) evidence_ref
        TEXT notes
        TIMESTAMP WITH TIME ZONE created_at
    }
    assets {
        UUID id PK
        UUID vendor_id FK
        VARCHAR(255) name
        TEXT description
        NUMERIC(18, 2) declared_value
        VARCHAR(3) currency
        VARCHAR(16) status
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    audit_logs {
        BIGINT seq
        UUID id PK
        UUID actor_user_id FK
        VARCHAR(24) actor_type
        VARCHAR(128) action
        VARCHAR(64) entity_type
        UUID entity_id
        VARCHAR(64) request_id
        INET ip_address
        TEXT user_agent
        VARCHAR(64) old_state_hash
        VARCHAR(64) new_state_hash
        JSONB metadata
        VARCHAR(64) prev_hash
        VARCHAR(64) row_hash
        TIMESTAMP WITH TIME ZONE created_at
    }
    campaign_counters {
        UUID campaign_id PK FK
        BIGINT next_entry_number
    }
    campaign_prizes {
        UUID campaign_id PK FK
        INTEGER prize_index PK
        UUID asset_id FK
    }
    campaign_rules {
        UUID id PK
        UUID campaign_id FK
        VARCHAR(64) rule_type
        JSONB params
    }
    campaign_status_history {
        UUID id PK
        UUID campaign_id FK
        VARCHAR(24) from_status
        VARCHAR(24) to_status
        UUID actor_user_id FK
        VARCHAR(8) actor_type
        TEXT reason
        TIMESTAMP WITH TIME ZONE created_at
    }
    campaigns {
        UUID id PK
        UUID vendor_id FK
        VARCHAR(255) title
        TEXT description
        VARCHAR(16) entry_mode
        NUMERIC(18, 2) entry_price
        INTEGER max_entries
        INTEGER per_user_limit
        TIMESTAMP WITH TIME ZONE start_at
        TIMESTAMP WITH TIME ZONE end_at
        TIMESTAMP WITH TIME ZONE draw_at
        VARCHAR(24) status
        UUID created_by FK
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    draw_entropy {
        UUID draw_id PK FK
        VARCHAR(128) source
        BIGINT round
        VARCHAR(512) value_hex
        INTEGER relays_confirmed
        TIMESTAMP WITH TIME ZONE fetched_at
    }
    draw_results {
        UUID id PK
        UUID draw_id FK
        INTEGER prize_index
        INTEGER remaining_count
        INTEGER winner_index
        UUID entry_id FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    draw_secrets {
        UUID draw_id PK FK
        BYTEA seed_ciphertext
        VARCHAR(128) key_id
        TIMESTAMP WITH TIME ZONE revealed_at
    }
    draw_snapshots {
        UUID id PK
        UUID draw_id FK
        INTEGER entry_count
        INTEGER[] entry_numbers
        VARCHAR(64) pool_hash
        TIMESTAMP WITH TIME ZONE created_at
    }
    draws {
        UUID id PK
        UUID campaign_id FK
        VARCHAR(16) status
        VARCHAR(24) stage
        VARCHAR(64) seed_commitment
        TIMESTAMP WITH TIME ZONE pool_locked_at
        UUID locked_by FK
        VARCHAR(128) planned_entropy_source
        BIGINT planned_entropy_round
        TIMESTAMP WITH TIME ZONE executed_at
        UUID executed_by FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    eligibility_records {
        UUID id PK
        UUID entry_id FK
        UUID campaign_id FK
        UUID user_id FK
        VARCHAR(64) rule_type
        VARCHAR(16) result
        JSONB evidence
        TIMESTAMP WITH TIME ZONE created_at
    }
    entries {
        UUID id PK
        UUID campaign_id FK
        UUID user_id FK
        INTEGER entry_number
        VARCHAR(16) status
        TIMESTAMP WITH TIME ZONE expires_at
        UUID payment_id FK
        VARCHAR(32) source_type
        VARCHAR(255) source_reference
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE confirmed_at
    }
    entry_mode_approvals {
        UUID id PK
        UUID campaign_id FK
        VARCHAR(16) entry_mode
        UUID approved_by FK
        TIMESTAMP WITH TIME ZONE approved_at
        VARCHAR(512) legal_reference
    }
    notification_templates {
        UUID id PK
        VARCHAR(100) template_key
        VARCHAR(16) channel
        VARCHAR(16) locale
        VARCHAR(255) subject
        TEXT body
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    notifications {
        UUID id PK
        UUID user_id FK
        UUID template_id FK
        VARCHAR(16) channel
        VARCHAR(16) status
        JSONB payload
        VARCHAR(128) provider_reference
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE sent_at
    }
    otp_challenges {
        UUID id PK
        VARCHAR(32) phone
        VARCHAR(255) code_hash
        TIMESTAMP WITH TIME ZONE expires_at
        INTEGER attempts
        TIMESTAMP WITH TIME ZONE consumed_at
        VARCHAR(45) ip_address
        TIMESTAMP WITH TIME ZONE created_at
    }
    payment_events {
        UUID id PK
        UUID payment_id FK
        VARCHAR(32) provider
        VARCHAR(128) provider_event_id
        VARCHAR(64) event_type
        VARCHAR(64) payload_sha256
        TIMESTAMP WITH TIME ZONE received_at
    }
    payments {
        UUID id PK
        UUID user_id FK
        UUID campaign_id FK
        VARCHAR(32) provider
        VARCHAR(128) merchant_reference
        VARCHAR(128) provider_reference
        NUMERIC(18, 2) amount
        VARCHAR(3) currency
        VARCHAR(16) status
        TIMESTAMP WITH TIME ZONE verified_at
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    prize_fulfillment_history {
        UUID id PK
        UUID fulfillment_id FK
        VARCHAR(16) status
        VARCHAR(512) evidence_ref
        UUID updated_by FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    prize_fulfillments {
        UUID id PK
        UUID winner_id FK
        VARCHAR(16) status
        VARCHAR(512) evidence_ref
        UUID updated_by FK
        TIMESTAMP WITH TIME ZONE updated_at
    }
    refresh_sessions {
        UUID id PK
        UUID user_id FK
        UUID family_id
        VARCHAR(64) token_hash
        TIMESTAMP WITH TIME ZONE expires_at
        TIMESTAMP WITH TIME ZONE revoked_at
        UUID replaced_by FK
        VARCHAR(45) ip_address
        TEXT user_agent
        TIMESTAMP WITH TIME ZONE created_at
    }
    refunds {
        UUID id PK
        UUID payment_id FK
        NUMERIC(18, 2) amount
        VARCHAR(512) reason
        VARCHAR(24) status
        UUID requested_by FK
        UUID approved_by FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    roles {
        UUID id PK
        VARCHAR(64) name
    }
    staff_mfa {
        UUID user_id PK FK
        BYTEA totp_secret_encrypted
        TIMESTAMP WITH TIME ZONE enabled_at
        TEXT[] recovery_code_hashes
    }
    user_roles {
        UUID user_id PK FK
        UUID role_id PK FK
        UUID granted_by FK
        TIMESTAMP WITH TIME ZONE granted_at
    }
    users {
        UUID id PK
        VARCHAR(320) email
        VARCHAR(32) phone
        TEXT password_hash
        TIMESTAMP WITH TIME ZONE phone_verified_at
        VARCHAR(16) status
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    vendor_documents {
        UUID id PK
        UUID vendor_id FK
        VARCHAR(64) kind
        VARCHAR(512) storage_key
        VARCHAR(64) sha256
        UUID uploaded_by FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    vendor_users {
        UUID vendor_id PK FK
        UUID user_id PK FK
        VARCHAR(16) role_in_vendor
        TIMESTAMP WITH TIME ZONE created_at
    }
    vendors {
        UUID id PK
        VARCHAR(255) legal_name
        VARCHAR(255) display_name
        VARCHAR(16) status
        VARCHAR(320) contact_email
        VARCHAR(32) contact_phone
        UUID approved_by FK
        TIMESTAMP WITH TIME ZONE approved_at
        TIMESTAMP WITH TIME ZONE created_at
        TIMESTAMP WITH TIME ZONE updated_at
    }
    verification_records {
        UUID id PK
        UUID draw_id FK
        JSONB package
        VARCHAR(64) package_sha256
        JSONB verifier_result
        TIMESTAMP WITH TIME ZONE published_at
    }
    winners {
        UUID id PK
        UUID draw_result_id FK
        UUID user_id FK
        UUID entry_id FK
        TIMESTAMP WITH TIME ZONE created_at
    }
    assets ||--o{ asset_verifications : "asset_id"
    assets ||--o| campaign_prizes : "asset_id"
    campaigns ||--o| campaign_counters : "campaign_id"
    campaigns ||--o{ campaign_prizes : "campaign_id"
    campaigns ||--o{ campaign_rules : "campaign_id"
    campaigns ||--o{ campaign_status_history : "campaign_id"
    campaigns ||--o| draws : "campaign_id"
    campaigns ||--o{ eligibility_records : "campaign_id"
    campaigns ||--o{ entries : "campaign_id"
    campaigns ||--o{ entry_mode_approvals : "campaign_id"
    campaigns ||--o{ payments : "campaign_id"
    draw_results ||--o| winners : "draw_result_id"
    draws ||--o| draw_entropy : "draw_id"
    draws ||--o{ draw_results : "draw_id"
    draws ||--o| draw_secrets : "draw_id"
    draws ||--o| draw_snapshots : "draw_id"
    draws ||--o| verification_records : "draw_id"
    entries ||--o{ draw_results : "entry_id"
    entries o|--o{ eligibility_records : "entry_id"
    entries ||--o{ winners : "entry_id"
    notification_templates o|--o{ notifications : "template_id"
    payments o|--o{ entries : "payment_id"
    payments o|--o{ payment_events : "payment_id"
    payments ||--o{ refunds : "payment_id"
    prize_fulfillments ||--o{ prize_fulfillment_history : "fulfillment_id"
    refresh_sessions o|--o{ refresh_sessions : "replaced_by"
    roles ||--o{ user_roles : "role_id"
    users ||--o{ asset_verifications : "verified_by"
    users o|--o{ audit_logs : "actor_user_id"
    users o|--o{ campaign_status_history : "actor_user_id"
    users ||--o{ campaigns : "created_by"
    users o|--o{ draws : "executed_by"
    users o|--o{ draws : "locked_by"
    users ||--o{ eligibility_records : "user_id"
    users ||--o{ entries : "user_id"
    users ||--o{ entry_mode_approvals : "approved_by"
    users ||--o{ notifications : "user_id"
    users ||--o{ payments : "user_id"
    users o|--o{ prize_fulfillment_history : "updated_by"
    users o|--o{ prize_fulfillments : "updated_by"
    users ||--o{ refresh_sessions : "user_id"
    users o|--o{ refunds : "approved_by"
    users ||--o{ refunds : "requested_by"
    users ||--o| staff_mfa : "user_id"
    users o|--o{ user_roles : "granted_by"
    users ||--o{ user_roles : "user_id"
    users o|--o{ vendor_documents : "uploaded_by"
    users ||--o{ vendor_users : "user_id"
    users o|--o{ vendors : "approved_by"
    users ||--o{ winners : "user_id"
    vendors ||--o{ assets : "vendor_id"
    vendors ||--o{ campaigns : "vendor_id"
    vendors ||--o{ vendor_documents : "vendor_id"
    vendors ||--o{ vendor_users : "vendor_id"
    winners ||--o| prize_fulfillments : "winner_id"
```
