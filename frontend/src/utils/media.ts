const configuredMediaOrigin = import.meta.env.VITE_MEDIA_URL;

function getMediaOrigin() {
  if (configuredMediaOrigin) {
    return configuredMediaOrigin.replace(/\/$/, "");
  }

  const apiUrl = import.meta.env.VITE_API_URL;
  if (apiUrl?.startsWith("http://") || apiUrl?.startsWith("https://")) {
    return new URL(apiUrl).origin;
  }

  return window.location.origin;
}

export function normalizeMediaUrl(value?: string | null) {
  if (!value) {
    return null;
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    const url = new URL(value);
    const isLocalhost = url.hostname === "localhost" || url.hostname === "127.0.0.1";
    const currentIsLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

    if (isLocalhost && currentIsLocalhost && !url.port && window.location.port) {
      return `${window.location.origin}${url.pathname}${url.search}${url.hash}`;
    }

    return value;
  }
  const normalizedPath = value.startsWith("/") ? value : `/${value}`;
  return `${getMediaOrigin()}${normalizedPath}`;
}
