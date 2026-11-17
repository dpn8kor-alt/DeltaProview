const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1/procman";
const API_ROOT = API_BASE.replace(/\/procman\/?$/, "");
const REVISION_CONFIG_BASE = `${API_ROOT}/revision-config`;

async function apiRequest(base, path, options = {}) {
  const { headers: optionHeaders = {}, ...fetchOptions } = options;
  const headers = { ...optionHeaders };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${base}${path}`, {
    headers,
    ...fetchOptions,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let message = "Request failed.";

    try {
      const payload = JSON.parse(errorText);
      message = payload.detail || payload.message || message;
    } catch {
      message = errorText || message;
    }

    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response;
}

export async function fetchConfig() {
  return apiRequest(API_BASE, "/configuration/pages");
}

export async function fetchRootPages() {
  return apiRequest(API_BASE, "/pages/root");
}

export async function fetchChildPages(pageId) {
  return apiRequest(API_BASE, `/pages/${encodeURIComponent(pageId)}/children`);
}

export async function fetchConfiguredRevisions(pageId) {
  return apiRequest(API_BASE, `/configuration/pages/${encodeURIComponent(pageId)}/revisions`);
}

export async function fetchRevisionRootPages() {
  return apiRequest(REVISION_CONFIG_BASE, "/pages/root");
}

export async function fetchRevisionChildPages(pageId) {
  return apiRequest(
    REVISION_CONFIG_BASE,
    `/pages/${encodeURIComponent(pageId)}/children`,
  );
}

export async function generateRevisionConfig(pages) {
  const response = await apiRequest(REVISION_CONFIG_BASE, "/xml/revision", {
    method: "POST",
    body: JSON.stringify({ pages }),
  });

  return response.blob();
}

export async function generateCompassConfig(level2PageIds) {
  const response = await apiRequest(REVISION_CONFIG_BASE, "/xml/compass", {
    method: "POST",
    body: JSON.stringify({ level2_page_ids: level2PageIds }),
  });

  return response.blob();
}

export async function uploadRevisionConfig(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest(API_BASE, "/configuration/upload", {
    method: "POST",
    body: formData,
  });
}

export async function runComparison(
  publishedPageId,
  outdatedPageId,
  methodName,
  publishedVersion,
  outdatedVersion,
) {
  const response = await fetch(`${API_BASE}/comparison/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      published_page_id: publishedPageId,
      outdated_page_id: outdatedPageId,
      method_name: methodName,
      published_version: publishedVersion,
      outdated_version: outdatedVersion,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let message = "Comparison failed.";

    try {
      const payload = JSON.parse(errorText);
      message = payload.detail || payload.message || message;
    } catch {
      message = errorText || message;
    }

    throw new Error(message);
  }

  return response.blob();
}
