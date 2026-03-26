/** Matches backend Token response */
export interface AuthToken {
  access_token: string;
  token_type: string;
}

/** Matches backend UserResponse */
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  email_verified: boolean;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}
