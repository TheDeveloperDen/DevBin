// general types and decontstucted types to reduce complexity
import * as ApiService from "../client";

export type ExpiryValues = "never" | "5m" | "15m" | "30m" | "1h" | "3h" | "1d";

export type ContentLanguage = ApiService.CreatePaste["content_language"];

export type Paste = {
  id: string;
  title: string;
  content: string;
  content_language: string;
  expires_at: string;
  created_at: string;
};
