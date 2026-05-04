interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function extractList<T>(response: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(response)) {
    return response;
  }
  return response.results || [];
}
