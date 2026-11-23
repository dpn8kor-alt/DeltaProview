
import { useState, useEffect, useRef } from "react";

import {
  LayoutDashboard,
  Settings,
  ChevronRight,
  Layers,
  FileSpreadsheet,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  History as HistoryIcon,
  Info,
  Menu,
  X,
} from "lucide-react";

import "./App.css";

import boschLogo from "./assests/Bosch_symbol_logo_black_red.png";
import boschLine from "./assests/BoschSC.png";
import compareIcon from "./assests/compare.png";
import downloadIcon from "./assests/download.png";
import historyIcon from "./assests/history.png";

import {
  fetchConfig,
  fetchRootPages,
  fetchChildPages,
  fetchLiveRevisions,
  runComparison,
  fetchRecentComparisons,
  fetchComparisonHistory,
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
  const [activeView, setActiveView] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const workflow = useRef(null);
  const hierarchyRequest = useRef(0);
  const revisionRequest = useRef(0);

  const [stage, setStage] = useState("");

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

  // History state
  const [recentComparisons, setRecentComparisons] = useState([]);
  const [comparisonHistory, setComparisonHistory] = useState([]);

  const [loadingRecent, setLoadingRecent] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    return () => workflow.current?.abort();
  }, []);

  // --------------------------------------------------
  // LOAD CONFIGURATION
  // --------------------------------------------------

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
          setConfigError(
            err.message || "Failed to load process configuration."
          );
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
  }, []);

  // --------------------------------------------------
  // LOAD ROOT PAGES
  // --------------------------------------------------

  useEffect(() => {
    let mounted = true;

    fetchRootPages()
      .then((pages) => {
        if (mounted) {
          setRootPages(
            pages.map((page) => ({
              ...page,
              id: String(page.id),
            }))
          );

          setHierarchyError("");
        }
      })
      .catch((err) => {
        if (mounted) {
          setHierarchyError(
            err.message || "Failed to load process landscapes."
          );
        }
      })
      .finally(() => {
        if (mounted) {
          setLoadingHierarchy(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  // --------------------------------------------------
  // LOAD DASHBOARD - LATEST THREE COMPARISONS
  // --------------------------------------------------

  const loadRecentComparisons = async () => {
    setLoadingRecent(true);

    try {
      const data = await fetchRecentComparisons();

      setRecentComparisons(Array.isArray(data) ? data.slice(0, 3) : []);
    } catch (err) {
      console.error("Recent comparisons loading failed:", err);
      setRecentComparisons([]);
    } finally {
      setLoadingRecent(false);
    }
  };

  // --------------------------------------------------
  // LOAD COMPLETE HISTORY
  // --------------------------------------------------

  const loadComparisonHistory = async () => {
    setLoadingHistory(true);
    setHistoryError("");

    try {
      const data = await fetchComparisonHistory();

      setComparisonHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Comparison history loading failed:", err);

      setHistoryError(
        err.message || "Unable to load comparison history."
      );

      setComparisonHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeView === "dashboard") {
      loadRecentComparisons();
    }

    if (activeView === "history") {
      loadComparisonHistory();
    }
  }, [activeView]);

  // --------------------------------------------------
  // WORKFLOW HELPERS
  // --------------------------------------------------

  const methodOptions = methodPages;

  const cancelWorkflow = () => {
    workflow.current?.abort();
    workflow.current = null;

    setLoadingCompare(false);
    setStage("");
  };

  // --------------------------------------------------
  // LOAD REVISIONS
  // --------------------------------------------------

  const loadProcessRevisions = async (pageId) => {
    const requestId = ++revisionRequest.current;

    if (!pageId) {
      setRevisions([]);
      return;
    }

    setLoadingRevisions(true);
    setError("");

    try {
      const pageConfig = configPages.find(
        (item) =>
          String(
            item.page_id ||
              item.published_page_id ||
              item.pub_id ||
              item.id
          ) === String(pageId)
      );

      const detail = pageConfig
        ? pageConfig
        : await fetchLiveRevisions(pageId);

      if (requestId !== revisionRequest.current) return;

      const publishedPageId = String(
        detail.published_page_id || pageId
      );

      const historicalRevisions = (detail.revisions || []).map(
        (revision) => ({
          id: String(
            revision.revision_page_id ||
              revision.pageId ||
              revision.id
          ),
          version: String(revision.revision || revision.version),
          pageId: String(
            revision.revision_page_id ||
              revision.pageId ||
              revision.id
          ),
          isPublished: false,
        })
      );

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
      if (requestId !== revisionRequest.current) return;

      console.error("Revision loading failed:", err);

      setRevisions([]);
      setError(
        err.message || "Failed to load revisions for this process."
      );
    } finally {
      if (requestId === revisionRequest.current) {
        setLoadingRevisions(false);
      }
    }
  };

  // --------------------------------------------------
  // PROCESS LANDSCAPE CHANGE
  // --------------------------------------------------

  const handleRootChange = async (pageId) => {
    cancelWorkflow();

    revisionRequest.current++;

    const requestId = ++hierarchyRequest.current;

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

      if (requestId !== hierarchyRequest.current) return;

      setLevel2Options(
        pages.map((page) => ({
          ...page,
          id: String(page.id),
        }))
      );
    } catch (err) {
      if (requestId !== hierarchyRequest.current) return;

      setHierarchyError(
        err.message || "Failed to load processes."
      );
    } finally {
      if (requestId === hierarchyRequest.current) {
        setLoadingHierarchy(false);
      }
    }
  };

  // --------------------------------------------------
  // PROCESS CHANGE
  // --------------------------------------------------

  const handlePSL2Change = async (pageId) => {
    cancelWorkflow();

    revisionRequest.current++;

    const requestId = ++hierarchyRequest.current;

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

      if (requestId !== hierarchyRequest.current) return;

      setMethodPages(
        pages.map((page) => ({
          ...page,
          id: String(page.id),
        }))
      );
    } catch (err) {
      if (requestId !== hierarchyRequest.current) return;

      setHierarchyError(
        err.message || "Failed to load methods."
      );
    } finally {
      if (requestId === hierarchyRequest.current) {
        setLoadingHierarchy(false);
      }
    }
  };

  // --------------------------------------------------
  // METHOD CHANGE
  // --------------------------------------------------

  const handleMethodChange = async (pageId) => {
    cancelWorkflow();

    const method = methodOptions.find(
      (item) => item.id === pageId
    );

    setSelectedMethodId(pageId);
    setSelectedMethodName(method?.title || "");

    setSelectedRevisions([]);
    setDownloadBlob(null);
    setError("");
    setRevisions([]);

    await loadProcessRevisions(pageId);
  };

  // --------------------------------------------------
  // REVISION SELECTION
  // --------------------------------------------------

  const handleToggleRevision = (revision) => {
    cancelWorkflow();

    setError("");
    setDownloadBlob(null);

    const next = selectedRevisions.some(
      (item) => item.id === revision.id
    )
      ? selectedRevisions.filter(
          (item) => item.id !== revision.id
        )
      : [...selectedRevisions.slice(-1), revision];

    setSelectedRevisions(next);
  };

  // --------------------------------------------------
  // RUN COMPARISON
  // --------------------------------------------------

  const handleCompare = async () => {
    if (selectedRevisions.length !== 2 || workflow.current) {
      return;
    }

    const controller = new AbortController();

    workflow.current = controller;

    setStage("Fetching Process Compass content");
    setLoadingCompare(true);

    setError("");
    setDownloadBlob(null);

    const sorted = [...selectedRevisions].sort((a, b) => {
      if (a.isPublished !== b.isPublished) {
        return a.isPublished ? 1 : -1;
      }

      return compareVersions(a.version, b.version);
    });

    const [oldRev, newRev] = sorted;

    try {
      const blob = await runComparison(
        {
          method_page_id: selectedMethodId,
          method_name: selectedMethodName,
          published_page_id: newRev.pageId,
          outdated_page_id: oldRev.pageId,
          published_version: newRev.version,
          outdated_version: oldRev.version,
        },
        controller.signal,
        (message) => {
          if (!controller.signal.aborted) {
            setStage(message);
          }
        }
      );

      if (controller.signal.aborted) return;

      setDownloadBlob(blob);

      setDownloadName(
        `DeltaProView_${selectedMethodName
          .split(" ")[0]
          .replace(/[^a-zA-Z0-9._-]/g, "")}_v${oldRev.version}_vs_v${newRev.version}.xlsx`
      );

      if (activeView === "dashboard") {
        loadRecentComparisons();
      }
    } catch (err) {
      if (controller.signal.aborted) return;

      setError(
        err.message || "Comparison failed. Please try again."
      );
    } finally {
      if (workflow.current === controller) {
        workflow.current = null;
        setLoadingCompare(false);
      }
    }
  };

  // --------------------------------------------------
  // DOWNLOAD CURRENT REPORT
  // --------------------------------------------------

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

  // --------------------------------------------------
  // DOWNLOAD HISTORICAL REPORT
  // --------------------------------------------------

  const handleHistoryDownload = async (comparison) => {
    console.log("Historical report selected:", comparison);
  };

  // --------------------------------------------------
  // DATE FORMATTING
  // --------------------------------------------------

  const formatDate = (value) => {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "—";

    return date.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  const getStatusClass = (status) => {
    const value = String(status || "").toLowerCase();

    if (value === "completed" || value === "success") {
      return "status-completed";
    }

    if (value === "failed" || value === "error") {
      return "status-failed";
    }

    return "status-processing";
  };

  const getStatusLabel = (status) => {
    const value = String(status || "").toLowerCase();

    if (value === "success" || value === "completed") {
      return "Completed";
    }

    if (value === "failed" || value === "error") {
      return "Failed";
    }

    return status || "Unknown";
  };

  // --------------------------------------------------
  // HISTORY TABLE
  // --------------------------------------------------

  const renderHistoryTable = (items, compact = false) => {
    if (!items.length) {
      return (
        <div className="empty-history">
          <HistoryIcon size={34} />
          <h4>No comparisons available</h4>
          <p>
            Your previous comparisons will appear here
            once you run a comparison.
          </p>
        </div>
      );
    }

    return (
      <div className="history-table-wrapper">
        <table className="history-table">
          <thead>
            <tr>
              <th>Comparison</th>
              <th>Date &amp; Time</th>
              <th>Status</th>
              {!compact && <th>Changes Found</th>}
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {items.map((item) => {
              const status = String(item.status || "").toLowerCase();
              const isSuccessful =
                status === "success" || status === "completed";

              const comparisonName =
                item.comparison_name ||
                item.name ||
                (item.page_name
                  ? `${item.page_name} (${item.source_version || "—"} vs ${item.target_version || "—"})`
                  : "Version comparison");

              return (
                <tr key={item.id || item.comparison_id}>
                  <td>
                    <span className="comparison-name">
                      {comparisonName}
                    </span>
                  </td>

                  <td className="comparison-date">
                    <Clock size={14} />
                    {formatDate(
                      item.created_at ||
                        item.comparison_date ||
                        item.timestamp
                    )}
                  </td>

                  <td>
                    <span
                      className={`status-badge ${getStatusClass(
                        item.status
                      )}`}
                    >
                      {getStatusLabel(item.status)}
                    </span>
                  </td>

                  {!compact && (
                    <td>
                      {item.changes_found ?? "—"}
                    </td>
                  )}

                  <td>
                    <button
                      type="button"
                      className="history-download-button"
                      onClick={() => handleHistoryDownload(item)}
                      disabled={!isSuccessful}
                      title="Download comparison report"
                    >
                      <Download size={16} />
                      Download
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  // --------------------------------------------------
  // DASHBOARD
  // --------------------------------------------------

  const renderDashboard = () => (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow process-engineering-label">
            PROCESS ENGINEERING
          </div>

          <h2>Dashboard</h2>

          <p>
            Select process revisions and generate a comparison report.
          </p>
        </div>
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div className="section-icon">
            <Layers size={20} />
          </div>

          <div>
            <h3>Process Selection</h3>
            <p>Select the process hierarchy.</p>
          </div>
        </div>

        <div className="selection-grid">
          <div className="form-group">
            <label htmlFor="compare-landscape">
              PS Process Landscape
            </label>

            <select
              id="compare-landscape"
              value={selectedRootId}
              onChange={(e) => handleRootChange(e.target.value)}
              disabled={loadingHierarchy}
            >
              <option value="">
                {loadingHierarchy
                  ? "Loading..."
                  : "-- Select Process Landscape --"}
              </option>

              {rootPages.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="compare-process">
              PS Processes
            </label>

            <select
              id="compare-process"
              value={selectedPSId}
              onChange={(e) => handlePSL2Change(e.target.value)}
              disabled={!selectedRootId || loadingHierarchy}
            >
              <option value="">-- Select Process --</option>

              {level2Options.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="compare-method">
              PS Methods
            </label>

            <select
              id="compare-method"
              value={selectedMethodId}
              onChange={(e) => handleMethodChange(e.target.value)}
              disabled={
                !selectedPSId ||
                loadingHierarchy ||
                loadingConfig ||
                methodOptions.length === 0
              }
            >
              <option value="">
                {loadingConfig
                  ? "Loading methods..."
                  : methodOptions.length
                    ? "-- Select Method --"
                    : "No methods available"}
              </option>

              {methodOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        {hierarchyError && (
          <div className="connection-notice">
            <AlertCircle size={17} />
            <span>{hierarchyError}</span>
          </div>
        )}

        {configError && (
          <div className="connection-notice">
            <AlertCircle size={17} />
            <span>{configError}</span>
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
              <p>
                Choose exactly two versions to compare.
              </p>
            </div>

            <div className="selection-count">
              {selectedRevisions.length} / 2 Selected
            </div>
          </div>

          {loadingRevisions ? (
            <div className="empty-state">
              Loading revisions...
            </div>
          ) : revisions.length > 0 ? (
            <div className="revision-list">
              {revisions.map((revision) => {
                const checked = selectedRevisions.some(
                  (item) => item.id === revision.id
                );

                return (
                  <label
                    key={revision.id}
                    className={`revision-item ${
                      checked ? "revision-selected" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleRevision(revision)}
                    />

                    <span className="revision-name">
                      {revision.isPublished
                        ? "Published"
                        : `Version ${revision.version}`}
                    </span>

                    <span className="revision-id">
                      ID: {revision.id}
                    </span>
                  </label>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              No revisions are available for this process.
            </div>
          )}

          {revisions.length > 0 && (
            <div className="action-area">
              <div className="action-info" role="status">
                {loadingCompare && (
                  <RefreshCw size={17} className="spin" />
                )}

                {loadingCompare
                  ? stage
                  : selectedRevisions.length < 2
                    ? "Select two revisions to continue."
                    : ""}
              </div>

              <div className="action-buttons">
                {selectedRevisions.length === 2 && !downloadBlob && (
                  <button
                    type="button"
                    className="compare-button"
                    onClick={handleCompare}
                    disabled={loadingCompare}
                  >
                    <img
                      src={compareIcon}
                      alt=""
                      className="button-icon"
                    />
                    Compare
                  </button>
                )}

                {downloadBlob && (
                  <button
                    type="button"
                    className="download-button"
                    onClick={handleDownload}
                  >
                    <img
                      src={downloadIcon}
                      alt=""
                      className="button-icon"
                    />
                    Download Excel
                  </button>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="error-message" role="alert">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {downloadBlob && (
            <div className="success-message" role="status">
              <CheckCircle2 size={18} />
              <span>
                Comparison completed successfully.
                Your Excel report is ready.
              </span>
            </div>
          )}
        </section>
      )}

      <section className="content-card recent-comparisons-card">
        <div className="section-heading">
          <div className="section-icon">
            <HistoryIcon size={20} />
          </div>

          <div>
            <h3>Recent Comparisons</h3>
            <p>Your three most recent comparisons.</p>
          </div>

          <button
            type="button"
            className="view-all-button"
            onClick={() => setActiveView("history")}
          >
            View all
            <ChevronRight size={16} />
          </button>
        </div>

        {loadingRecent ? (
          <div className="empty-state">
            Loading recent comparisons...
          </div>
        ) : (
          renderHistoryTable(recentComparisons, true)
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // HISTORY PAGE
  // --------------------------------------------------

  const renderHistory = () => (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">COMPARISON RECORDS</div>
          <h2>History</h2>
          <p>
            View and access your previous version comparisons.
          </p>
        </div>

        <button
          type="button"
          className="refresh-button"
          onClick={loadComparisonHistory}
          disabled={loadingHistory}
        >
          <RefreshCw
            size={16}
            className={loadingHistory ? "spin" : ""}
          />
          Refresh
        </button>
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div className="section-icon">
            <HistoryIcon size={20} />
          </div>

          <div>
            <h3>All Comparisons</h3>
            <p>
              Complete record of previously executed comparisons.
            </p>
          </div>

          <div className="history-total">
            {comparisonHistory.length} Records
          </div>
        </div>

        {historyError && (
          <div className="error-message" role="alert">
            <AlertCircle size={18} />
            <span>{historyError}</span>
          </div>
        )}

        {loadingHistory ? (
          <div className="empty-state">
            Loading comparison history...
          </div>
        ) : (
          renderHistoryTable(comparisonHistory, false)
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // SETTINGS PAGE
  // --------------------------------------------------

  const renderSettings = () => (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">APPLICATION INFORMATION</div>
          <h2>Settings</h2>
          <p>Application information and configuration.</p>
        </div>
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div className="section-icon">
            <Info size={20} />
          </div>

          <div>
            <h3>About DeltaProView</h3>
            <p>Application information.</p>
          </div>
        </div>

        <div className="settings-information">
          <div>
            <span>Application</span>
            <strong>DeltaProView</strong>
          </div>

          <div>
            <span>Description</span>
            <strong>Compass Version Comparer</strong>
          </div>

          <div>
            <span>Organization</span>
            <strong>Robert Bosch GmbH</strong>
          </div>
        </div>
      </section>
    </>
  );

  // --------------------------------------------------
  // MAIN UI
  // --------------------------------------------------

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-inner">
          <button
            type="button"
            className="mobile-menu-button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation"
          >
            {sidebarOpen ? <X /> : <Menu />}
          </button>

          <div className="brand-section">
            <img
              src={boschLogo}
              alt="Bosch"
              className="bosch-logo"
            />

            <div className="brand-divider" />

            <div className="application-title">
              <h1>DeltaProView</h1>
              <span>Compass Version Comparer</span>
            </div>
          </div>
        </div>
      </header>

      <div className="bosch-header-line">
        <img src={boschLine} alt="" />
      </div>

      <div className="app-body">
        <aside
          className={`sidebar ${
            sidebarOpen ? "sidebar-open" : ""
          }`}
        >
          <nav className="sidebar-navigation">
            <button
              type="button"
              className={`nav-item ${
                activeView === "dashboard" ? "active" : ""
              }`}
              onClick={() => {
                setActiveView("dashboard");
                setSidebarOpen(false);
              }}
            >
              <LayoutDashboard size={20} />
              <span>Dashboard</span>
            </button>

            <button
              type="button"
              className={`nav-item ${
                activeView === "history" ? "active" : ""
              }`}
              onClick={() => {
                setActiveView("history");
                setSidebarOpen(false);
              }}
            >
              <img
                src={historyIcon}
                alt=""
                className="nav-image-icon"
              />
              <span>History</span>
            </button>

            <button
              type="button"
              className={`nav-item ${
                activeView === "settings" ? "active" : ""
              }`}
              onClick={() => {
                setActiveView("settings");
                setSidebarOpen(false);
              }}
            >
              <Settings size={20} />
              <span>Settings</span>
            </button>
          </nav>
        </aside>

        {sidebarOpen && (
          <button
            type="button"
            className="sidebar-overlay"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          />
        )}

        <main className="main-content">
          {activeView === "dashboard" && renderDashboard()}
          {activeView === "history" && renderHistory()}
          {activeView === "settings" && renderSettings()}
        </main>
      </div>

      <footer className="app-footer">
        <div className="footer-inner">
          <span>
            © Robert Bosch GmbH {new Date().getFullYear()}
          </span>

          <span>
            DeltaProView | Compass Version Comparer
          </span>

          <span className="version-label">
            POC v1.0
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
