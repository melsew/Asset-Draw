export interface AuthUser {
  id: string;
  phone: string | null;
  display_name?: string;
  email?: string;
  role:
    | "PARTICIPANT"
    | "VENDOR"
    | "ADMIN"
    | "SUPER_ADMIN"
    | "CAMPAIGN_MANAGER"
    | "FINANCE"
    | "AUDITOR"
    | "CUSTOMER_SUPPORT";
  status: "active" | "suspended" | "pending";
}

export interface AuthTokens {
  access_token: string;
  token_type: "bearer";
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface RegisterRequest {
  phone: string;
  password: string;
  display_name: string;
}

export interface OtpVerifyRequest {
  phone: string;
  otp: string;
}
