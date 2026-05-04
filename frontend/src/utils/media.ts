
const API_ORIGIN = import.meta.env.VITE_MEDIA_URL || "http://localhost:8000";

export function normalizeMediaUrl(value?: string | null) {
  if (!value) {
    return null;
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }
  const normalizedPath = value.startsWith("/") ? value : `/${value}`;
  return `${API_ORIGIN}${normalizedPath}`;
}