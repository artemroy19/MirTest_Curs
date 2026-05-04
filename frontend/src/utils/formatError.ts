export function formatError(error: unknown, fallback: string): string {
  const data = (error as any)?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data?.detail) return data.detail;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
    .join(" ");
}
