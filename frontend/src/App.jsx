import { useState, useEffect } from "react";

import {
  GitCompareArrows,
  Download,
  RotateCcw,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Layers,
} from "lucide-react";

import "./App.css";
import ConfigBuilder from "./ConfigBuilder";
import {
  fetchConfig,
  fetchRootPages,
  fetchChildPages,
  fetchConfiguredRevisions,
  runComparison,
} from "./api";

const compareVersions = (a, b) => {
  const pa = String(a).split(".").map((n) => parseInt(n, 10) || 0);
  const pb = String(b).split(".").map((n) => parseInt(n, 10) || 0);
  const len = Math.max(pa.length, pb.length);

  for (let i = 0; i < len; i += 1) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff !== 0) return diff;
  }

  return 0;
};

function App() {
  const [activeView, setActiveView] = useState("compare");
  const [configRefreshKey, setConfigRefreshKey] = useState(0);
  const [configPages, setConfigPages] = useState([]);
  const [rootPages, setRootPages] = useState([]);
  const [level2Options, setLevel2Options] = useState([]);
  const [methodPages, setMethodPages] = useState([]);
  const [selectedRootId, setSelectedRootId] = useState("");
  const [selectedPSId, setSelectedPSId] = useState("");
  const [selectedMethodId, setSelectedMethodId] = useState("");
  const [selectedMethodName, setSelectedMethodName] = useState("");
  const [revisions, setRevisions] = useState([]);
  const [selectedRevisions, setSelectedRevisions] = useState([]);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingHierarchy, setLoadingHierarchy] = useState(true);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [loadingRevisions, setLoadingRevisions] = useState(false);
  const [error, setError] = useState("");
  const [configError, setConfigError] = useState("");
  const [hierarchyError, setHierarchyError] = useState("");
  const [downloadBlob, setDownloadBlob] = useState(null);
  const [downloadName, setDownloadName] = useState("DeltaProView.xlsx");

  useEffect(() => {
    let mounted = true;

    const loadConfig = async () => {
      setLoadingConfig(true);
      try {
        const rows = await fetchConfig();

        if (!Array.isArray(rows)) {
          throw new Error("Invalid configuration response");
        }

        if (mounted) {
          setConfigPages(rows);
          setConfigError("");
        }
      } catch (err) {
        console.error("Configuration loading failed:", err);

        if (mounted) {
          setConfigPages([]);
          setConfigError(err.message || "Failed to load process configuration.");
        }
      } finally {
        if (mounted) {
          setLoadingConfig(false);
        }
      }
    };

    loadConfig();

    return () => {
      mounted = false;
    };
  }, [configRefreshKey]);

  useEffect(() => {
    let mounted = true;

    fetchRootPages()
      .then((pages) => {
        if (mounted) {
          setRootPages(pages.map((page) => ({ ...page, id: String(page.id) })));
          setHierarchyError("");
        }
      })
      .catch((err) => {
        if (mounted) setHierarchyError(err.message || "Failed to load process landscapes.");
      })
      .finally(() => {
        if (mounted) setLoadingHierarchy(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const configuredMethodIds = new Set(configPages.map((item) =>
    String(item.page_id || item.published_page_id || item.pub_id || item.id),
  ));
  const methodOptions = methodPages.filter((page) => configuredMethodIds.has(String(page.id)));

  const loadProcessRevisions = async (pageId) => {
    if (!pageId) {
      setRevisions([]);
      return;
    }

    setLoadingRevisions(true);
    setError("");

    try {
      const pageConfig = configPages.find(
        (item) => String(item.page_id || item.published_page_id || item.pub_id || item.id) === String(pageId),
      );

      const detail = pageConfig
        ? pageConfig
        : await fetchConfiguredRevisions(pageId);

      const publishedPageId = String(detail.published_page_id || pageId);
      const historicalRevisions = (detail.revisions || []).map((revision) => ({
        id: String(revision.revision_page_id || revision.pageId || revision.id),
        version: String(revision.revision || revision.version),
        pageId: String(revision.revision_page_id || revision.pageId || revision.id),
        isPublished: false,
      }));

      setRevisions([
        {
          id: publishedPageId,
          version: "Published",
          pageId: publishedPageId,
          isPublished: true,
        },
        ...historicalRevisions,
      ]);
    } catch (err) {
      console.error("Revision loading failed:", err);
      setRevisions([]);
      setError(err.message || "Failed to load revisions for this process.");
    } finally {
      setLoadingRevisions(false);
    }
  };

  const handleRootChange = async (pageId) => {
    setSelectedRootId(pageId);
    setSelectedPSId("");
    setSelectedMethodId("");
    setSelectedMethodName("");
    setLevel2Options([]);
    setMethodPages([]);
    setSelectedRevisions([]);
    setDownloadBlob(null);
    setError("");
    setHierarchyError("");

    if (!pageId) {
      setRevisions([]);
      return;
    }

    setLoadingHierarchy(true);
    try {
      const pages = await fetchChildPages(pageId);
      setLevel2Options(pages.map((page) => ({ ...page, id: String(page.id) })));
    } catch (err) {
      setHierarchyError(err.message || "Failed to load processes.");
    } finally {
      setLoadingHierarchy(false);
    }
  };

  const handlePSL2Change = async (pageId) => {
    setSelectedPSId(pageId);
    setSelectedMethodId("");
    setSelectedMethodName("");
    setMethodPages([]);
    setSelectedRevisions([]);
    setRevisions([]);
    setDownloadBlob(null);
    setError("");
    setHierarchyError("");

    if (!pageId) return;

    setLoadingHierarchy(true);
    try {
      const pages = await fetchChildPages(pageId);
      setMethodPages(pages.map((page) => ({ ...page, id: String(page.id) })));
    } catch (err) {
      setHierarchyError(err.message || "Failed to load methods.");
    } finally {
      setLoadingHierarchy(false);
    }
  };

  const handleMethodChange = async (pageId) => {
    const method = methodOptions.find((item) => item.id === pageId);
    setSelectedMethodId(pageId);
    setSelectedMethodName(method?.title || "");
    setSelectedRevisions([]);
    setDownloadBlob(null);
    setError("");
    setRevisions([]);
    await loadProcessRevisions(pageId);
  };

  const handleToggleRevision = (revision) => {
    setError("");
    setDownloadBlob(null);

    setSelectedRevisions((previous) => {
      const alreadySelected = previous.some((item) => item.id === revision.id);

      if (alreadySelected) {
        return previous.filter((item) => item.id !== revision.id);
      }

      if (previous.length >= 2) {
        return [previous[1], revision];
      }

      return [...previous, revision];
    });
  };

  const handleCompare = async () => {
    if (!selectedMethodId || selectedRevisions.length !== 2) {
      return;
    }

    setLoadingCompare(true);
    setError("");
    setDownloadBlob(null);

    const sorted = [...selectedRevisions].sort((a, b) => {
      if (a.isPublished !== b.isPublished) return a.isPublished ? 1 : -1;
      return compareVersions(a.version, b.version);
    });
    const [oldRev, newRev] = sorted;

    try {
      const blob = await runComparison(
        newRev.pageId,
        oldRev.pageId,
        selectedMethodName,
        newRev.version,
        oldRev.version,
      );

      setDownloadBlob(blob);
      setDownloadName(
        `DeltaProView_${selectedMethodName
          .split(" ")[0]
          .replace(/[^a-zA-Z0-9._-]/g, "")}_v${oldRev.version}_vs_v${newRev.version}.xlsx`,
      );
    } catch (err) {
      console.error("Comparison failed:", err);
      setError(err.message || "Comparison failed. Please try again.");
    } finally {
      setLoadingCompare(false);
    }
  };

  const handleDownload = () => {
    if (!downloadBlob) return;

    const url = window.URL.createObjectURL(downloadBlob);
    const link = document.createElement("a");

    link.href = url;
    link.download = downloadName;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(url);
  };

  const handleReset = () => {
    setSelectedRootId("");
    setSelectedPSId("");
    setSelectedMethodId("");
    setSelectedMethodName("");
    setLevel2Options([]);
    setMethodPages([]);
    setSelectedRevisions([]);
    setRevisions([]);
    setDownloadBlob(null);
    setError("");
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-section">
            <div className="bosch-brand">BOSCH</div>
            <div className="brand-divider" />
            <div className="application-title">
              <h1>DeltaProView</h1>
              <span>Compass Version Comparer</span>
            </div>
          </div>

          <div className="header-right">
            <nav className="app-navigation" aria-label="Applications">
              <button className={activeView === "compare" ? "active" : ""} onClick={() => setActiveView("compare")}>Compare</button>
              <button className={activeView === "config" ? "active" : ""} onClick={() => setActiveView("config")}>Create XML</button>
            </nav>
            <span className="version-label">POC v1.0</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        {activeView === "compare" ? (
          <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">PROCESS ENGINEERING</div>
            <h2>Version Comparison</h2>
            <p>Select a process, choose two revisions and generate an Excel comparison report.</p>
          </div>

          <button className="reset-button" onClick={handleReset}>
            <RotateCcw size={16} />
            Reset
          </button>
        </div>

        <section className="content-card">
          <div className="section-heading">
            <div className="section-icon">
              <Layers size={20} />
            </div>

            <div>
              <h3>Process Selection</h3>
              <p>Select the process hierarchy</p>
            </div>
          </div>

          <div className="selection-grid">
            <div className="form-group">
              <label htmlFor="compare-landscape">PS Process Landscape</label>
              <select
                id="compare-landscape"
                value={selectedRootId}
                onChange={(e) => handleRootChange(e.target.value)}
                disabled={loadingHierarchy}
              >
                <option value="">{loadingHierarchy ? "Loading..." : "-- Select Process Landscape --"}</option>
                {rootPages.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="compare-process">PS Processes</label>
              <select
                id="compare-process"
                value={selectedPSId}
                onChange={(e) => handlePSL2Change(e.target.value)}
                disabled={!selectedRootId || loadingHierarchy}
              >
                <option value="">-- Select Process --</option>
                {level2Options.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="compare-method">PS Methods</label>
              <select
                id="compare-method"
                value={selectedMethodId}
                onChange={(e) => handleMethodChange(e.target.value)}
                disabled={!selectedPSId || loadingHierarchy || loadingConfig || methodOptions.length === 0}
              >
                <option value="">
                  {loadingConfig ? "Loading configuration..." : methodOptions.length ? "-- Select Method --" : "No configured methods"}
                </option>
                {methodOptions.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
              </select>
            </div>
          </div>

          {hierarchyError && (
            <div className="connection-notice"><AlertCircle size={17} /><span>{hierarchyError}</span></div>
          )}

          {!loadingConfig && configPages.length === 0 && (
            <div className="connection-notice">
              <AlertCircle size={17} />
              <span>
                {configError || "No configured process revisions were found. Upload the ProcMan XML configuration first."}
              </span>
            </div>
          )}
        </section>

        {selectedMethodId && (
          <section className="content-card">
            <div className="section-heading">
              <div className="section-icon red-icon">
                <FileSpreadsheet size={20} />
              </div>

              <div>
                <h3>Select Revisions</h3>
                <p>Choose exactly two versions to compare.</p>
              </div>

              <div className="selection-count">{selectedRevisions.length} / 2 Selected</div>
            </div>

            {loadingRevisions ? (
              <div className="empty-state">Loading revisions...</div>
            ) : revisions.length > 0 ? (
              <div className="revision-list">
                {revisions.map((revision) => {
                  const checked = selectedRevisions.some((item) => item.id === revision.id);

                  return (
                    <label
                      key={revision.id}
                      className={`revision-item ${checked ? "revision-selected" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => handleToggleRevision(revision)}
                      />

                      <span className="revision-name">
                        {revision.isPublished ? "Published" : `Version ${revision.version}`}
                      </span>
                      <span className="revision-id">ID: {revision.id}</span>
                    </label>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">No revisions are available for this process.</div>
            )}

            {revisions.length > 0 && (
              <div className="action-area">
                <div className="action-info">
                  {selectedRevisions.length === 2
                    ? "Two revisions selected. Ready to compare."
                    : "Select two revisions to continue."}
                </div>

                <div className="action-buttons">
                  <button
                    className="compare-button"
                    onClick={handleCompare}
                    disabled={selectedRevisions.length !== 2 || loadingCompare}
                  >
                    {loadingCompare ? (
                      <RefreshCw size={17} className="spin" />
                    ) : (
                      <GitCompareArrows size={17} />
                    )}

                    {loadingCompare ? "Comparing..." : "Compare Revisions"}
                  </button>

                  {downloadBlob && (
                    <button className="download-button" onClick={handleDownload}>
                      <Download size={17} />
                      Download Excel
                    </button>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="error-message">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            {downloadBlob && (
              <div className="success-message">
                <CheckCircle2 size={18} />
                <span>Comparison completed successfully. Your Excel report is ready.</span>
              </div>
            )}
          </section>
        )}
          </>
        ) : (
          <ConfigBuilder onConfigurationUpdated={() => setConfigRefreshKey((key) => key + 1)} />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-inner">
          <span>© Robert Bosch GmbH {new Date().getFullYear()}</span>
          <span>DeltaProView | Compass Version Comparer</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
