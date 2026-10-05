/** Backend base URL. Always comes from the environment; never hardcode a host here. */
export function apiBaseUrl(): string {
  const server = typeof window === "undefined" ? process.env.API_URL : undefined;
  const url = server || process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.example to frontend/.env.local and set it.",
    );
  }
  return url.replace(/\/+$/, "");
}
