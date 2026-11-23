
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api/v1/procman";

const API_ROOT = API_BASE.replace(/\/procman\/?$/, "");

const REVISION_CONFIG_BASE = `${API_ROOT}/revision-config`;

// Proposed History API endpoints.
// Align these paths with the backend when History routes are implemented.
const HISTORY_BASE = `${API_BASE}/history`;

// --------------------------------------------------
// COMMON API REQUEST HANDLER
// --------------------------------------------------

async function apiRequest(base, path, options = {}) {
  const { headers: optionHeaders = {}, ...fetchOptions } = options;

  const headers = { ...optionHeaders };

  // Set JSON content type only when sending a JSON body.
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${base}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();

    let message = "Request failed.";

    try {
      const payload = JSON.parse(errorText);

      message =
        payload.detail ||
        payload.message ||
        message;
    } catch {
      message = errorText || message;
    }

    throw new Error(message);
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response;
}

// --------------------------------------------------
// PROCESS CONFIGURATION
// --------------------------------------------------

export async function fetchConfig() {
  return apiRequest(
    API_BASE,
    "/configuration/pages"
  );
}

// --------------------------------------------------
// PROCESS COMPASS PAGE HIERARCHY
// --------------------------------------------------

export async function fetchRootPages() {
  return apiRequest(
    API_BASE,
    "/pages/root"
  );
}

export async function fetchChildPages(pageId) {
  return apiRequest(
    API_BASE,
    `/pages/${encodeURIComponent(pageId)}/children`
  );
}

// --------------------------------------------------
// CONFIGURED REVISIONS
// --------------------------------------------------

export async function fetchConfiguredRevisions(pageId) {
  return apiRequest(
    API_BASE,
    `/configuration/pages/${encodeURIComponent(pageId)}/revisions`
  );
}

// --------------------------------------------------
// REVISION CONFIGURATION PAGE HIERARCHY
// --------------------------------------------------

export async function fetchRevisionRootPages() {
  return apiRequest(
    REVISION_CONFIG_BASE,
    "/pages/root"
  );
}

export async function fetchRevisionChildPages(pageId) {
  return apiRequest(
    REVISION_CONFIG_BASE,
    `/pages/${encodeURIComponent(pageId)}/children`
  );
}

// --------------------------------------------------
// GENERATE REVISION CONFIGURATION XML
// --------------------------------------------------

export async function generateRevisionConfig(pages) {
  const response = await apiRequest(
    REVISION_CONFIG_BASE,
    "/xml/revision",
    {
      method: "POST",
      body: JSON.stringify({ pages }),
    }
  );

  return response.blob();
}

// --------------------------------------------------
// GENERATE COMPASS CONFIGURATION XML
// --------------------------------------------------

export async function generateCompassConfig(level2PageIds) {
  const response = await apiRequest(
    REVISION_CONFIG_BASE,
    "/xml/compass",
    {
      method: "POST",
      body: JSON.stringify({
        level2_page_ids: level2PageIds,
      }),
    }
  );

  return response.blob();
}

// --------------------------------------------------
// UPLOAD REVISION CONFIGURATION
// --------------------------------------------------

export async function uploadRevisionConfig(file) {
  const formData = new FormData();

  formData.append("file", file);

  return apiRequest(
    API_BASE,
    "/configuration/upload",
    {
      method: "POST",
      body: formData,
    }
  );
}

// --------------------------------------------------
// FETCH LIVE REVISIONS
// --------------------------------------------------

export async function fetchLiveRevisions(pageId) {
  const { published, history } = await apiRequest(
    REVISION_CONFIG_BASE,
    `/revisions/${encodeURIComponent(pageId)}`
  );

  return {
    published_page_id: published.pageId,

    revisions: history.map(({ version, pageId }) => ({
      revision: version,
      revision_page_id: pageId,
    })),
  };
}

// --------------------------------------------------
// RUN COMPARISON
// --------------------------------------------------

export async function runComparison(
  selection,
  signal,
  onStage = () => {}
) {
  const response = await apiRequest(
    API_BASE,
    "/comparison/workflow",
    {
      method: "POST",
      body: JSON.stringify(selection),
      signal,
    }
  );

  if (!response.body) {
    throw new Error(
      "The server returned an empty comparison response."
    );
  }

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();

  const parts = [];

  let pending = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Process any final message without a trailing newline.
        if (pending.trim()) {
          const message = JSON.parse(pending);

          if (message.error) {
            throw new Error(message.error);
          }

          if (message.stage) {
            onStage(message.stage);
          }

          if (message.data) {
            parts.push(
              Uint8Array.from(
                atob(message.data),
                (char) => char.charCodeAt(0)
              )
            );
          }

          if (message.ready && parts.length) {
            return new Blob(parts, {
              type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            });
          }
        }

        break;
      }

      const lines = (pending + value).split("\n");

      pending = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;

        const message = JSON.parse(line);

        if (message.error) {
          throw new Error(message.error);
        }

        if (message.stage) {
          onStage(message.stage);
        }

        if (message.data) {
          parts.push(
            Uint8Array.from(
              atob(message.data),
              (char) => char.charCodeAt(0)
            )
          );
        }

        if (message.ready) {
          if (!parts.length) {
            throw new Error(
              "Comparison completed, but no report data was received."
            );
          }

          return new Blob(parts, {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          });
        }
      }
    }

    throw new Error(
      "Report transfer ended before completion. Please retry the comparison."
    );
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

// ==================================================
// HISTORY APIs
// ==================================================

// --------------------------------------------------
// FETCH LATEST THREE COMPARISONS
// Dashboard uses this function.
// --------------------------------------------------

export async function fetchRecentComparisons() {
  const response = await apiRequest(
    API_BASE,
    "/history?limit=3"
  );

  // Supports either a direct array or an object
  // containing a comparisons array.
  const comparisons = Array.isArray(response)
    ? response
    : response.comparisons || response.items || [];

  return comparisons.slice(0, 3);
}

// --------------------------------------------------
// FETCH COMPLETE COMPARISON HISTORY
// History page uses this function.
// --------------------------------------------------

export async function fetchComparisonHistory() {
  const response = await apiRequest(
    API_BASE,
    "/history"
  );

  const comparisons = Array.isArray(response)
    ? response
    : response.comparisons || response.items || [];

  // Newest comparisons first.
  return [...comparisons].sort((a, b) => {
    const dateA = new Date(
      a.created_at ||
      a.comparison_date ||
      a.timestamp ||
      0
    ).getTime();

    const dateB = new Date(
      b.created_at ||
      b.comparison_date ||
      b.timestamp ||
      0
    ).getTime();

    return dateB - dateA;
  });
}

// --------------------------------------------------
// DOWNLOAD HISTORICAL COMPARISON REPORT
// --------------------------------------------------

export async function downloadHistoricalComparison(
  comparisonId
) {
  const response = await apiRequest(
    API_BASE,
    `/history/${encodeURIComponent(comparisonId)}/download`
  );

  return response.blob();
}
