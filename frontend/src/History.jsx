
import { useEffect, useMemo, useState } from "react";
import {
    AlertCircle,
    CalendarDays,
    ChevronLeft,
    ChevronRight,
    Clock,
    Download,
    FileSpreadsheet,
    History as HistoryIcon,
    RefreshCw,
} from "lucide-react";

import { fetchComparisonHistory } from "./api";
import { comparisonLabel as getComparisonName } from "./comparisonLabels";
import "./App.css";

/* =========================================================
   CONFIGURATION
   ========================================================= */

const ITEMS_PER_PAGE = 10;

/* =========================================================
   HELPER FUNCTIONS
   ========================================================= */

function getComparisonDate(item) {
    return (
        item.created_at ||
        item.createdAt ||
        item.timestamp ||
        item.comparison_date ||
        item.comparisonDate ||
        item.date ||
        null
    );
}

function getComparisonStatus(item) {
    return String(item.status || "Unknown").toLowerCase();
}

function formatDateTime(value) {
    if (!value) return "Date unavailable";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
    });
}

function getReportUrl(item) {
    return (
        item.download_url ||
        item.downloadUrl ||
        item.report_url ||
        item.reportUrl ||
        null
    );
}

function normalizeHistoryResponse(response) {
    if (Array.isArray(response)) {
        return response;
    }

    if (Array.isArray(response?.items)) {
        return response.items;
    }

    if (Array.isArray(response?.history)) {
        return response.history;
    }

    if (Array.isArray(response?.comparisons)) {
        return response.comparisons;
    }

    if (Array.isArray(response?.data)) {
        return response.data;
    }

    return [];
}

/* =========================================================
   STATUS COMPONENT
   ========================================================= */

function StatusBadge({ status }) {
    const normalizedStatus = getComparisonStatus({ status });

    let statusClass = "history-status-unknown";
    let label = status || "Unknown";

    if (["completed", "success", "successful"].includes(normalizedStatus)) {
        statusClass = "history-status-completed";
        label = "Completed";
    } else if (["failed", "error"].includes(normalizedStatus)) {
        statusClass = "history-status-failed";
        label = "Failed";
    } else if (
        ["running", "processing", "in_progress", "pending"].includes(
            normalizedStatus
        )
    ) {
        statusClass = "history-status-running";
        label = "In Progress";
    }

    return (
        <span className={`history-status ${statusClass}`}>
            <span className="history-status-dot" />
            {label}
        </span>
    );
}

/* =========================================================
   HISTORY COMPONENT
   ========================================================= */

function History({ onDownload }) {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [downloadingId, setDownloadingId] = useState(null);

    /* -----------------------------------------------------
       FETCH COMPLETE COMPARISON HISTORY
       ----------------------------------------------------- */

    const loadHistory = async () => {
        try {
            setLoading(true);
            setError("");

            const response = await fetchComparisonHistory();
            const records = normalizeHistoryResponse(response);

            const sortedRecords = [...records].sort((a, b) => {
                const dateA = new Date(getComparisonDate(a) || 0).getTime();
                const dateB = new Date(getComparisonDate(b) || 0).getTime();

                return dateB - dateA;
            });

            setHistory(sortedRecords);
            setCurrentPage(1);
        } catch (err) {
            console.error("Unable to fetch comparison history:", err);

            setError(
                err?.response?.data?.detail ||
                    err?.message ||
                    "Unable to load comparison history. Please try again."
            );
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    /* -----------------------------------------------------
       PAGINATION
       ----------------------------------------------------- */

    const totalPages = Math.max(
        1,
        Math.ceil(history.length / ITEMS_PER_PAGE)
    );

    const paginatedHistory = useMemo(() => {
        const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;

        return history.slice(startIndex, startIndex + ITEMS_PER_PAGE);
    }, [history, currentPage]);

    const firstRecord =
        history.length === 0
            ? 0
            : (currentPage - 1) * ITEMS_PER_PAGE + 1;

    const lastRecord = Math.min(
        currentPage * ITEMS_PER_PAGE,
        history.length
    );

    /* -----------------------------------------------------
       DOWNLOAD REPORT
       ----------------------------------------------------- */

    const handleDownload = async (item) => {
        const comparisonId =
            item.id ||
            item.comparison_id ||
            item.comparisonId;

        try {
            setDownloadingId(comparisonId || getComparisonName(item));

            if (onDownload) {
                await onDownload(item);
                return;
            }

            const reportUrl = getReportUrl(item);

            if (!reportUrl) {
                throw new Error(
                    "The report download URL is not available for this comparison."
                );
            }

            const link = document.createElement("a");
            link.href = reportUrl;
            link.download = "";
            link.target = "_blank";
            link.rel = "noopener noreferrer";

            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Unable to download comparison report:", err);
            setError(
                err?.message || "Unable to download the comparison report."
            );
        } finally {
            setDownloadingId(null);
        }
    };

    /* -----------------------------------------------------
       LOADING STATE
       ----------------------------------------------------- */

    if (loading) {
        return (
            <section className="history-page">
                <div className="history-page-header">
                    <div>
                        <h1>Comparison History</h1>
                        <p>
                            View and access your previous Process Compass
                            comparisons.
                        </p>
                    </div>
                </div>

                <div className="history-state-container">
                    <RefreshCw className="history-loading-icon" size={28} />
                    <h3>Loading comparison history...</h3>
                    <p>Please wait while we retrieve your records.</p>
                </div>
            </section>
        );
    }

    /* -----------------------------------------------------
       ERROR STATE
       ----------------------------------------------------- */

    if (error && history.length === 0) {
        return (
            <section className="history-page">
                <div className="history-page-header">
                    <div>
                        <h1>Comparison History</h1>
                        <p>
                            View and access your previous Process Compass
                            comparisons.
                        </p>
                    </div>
                </div>

                <div className="history-state-container history-error-state">
                    <AlertCircle size={32} />
                    <h3>Unable to load history</h3>
                    <p>{error}</p>

                    <button
                        type="button"
                        className="history-retry-button"
                        onClick={loadHistory}
                    >
                        <RefreshCw size={16} />
                        Try Again
                    </button>
                </div>
            </section>
        );
    }

    /* -----------------------------------------------------
       EMPTY STATE
       ----------------------------------------------------- */

    if (history.length === 0) {
        return (
            <section className="history-page">
                <div className="history-page-header">
                    <div>
                        <h1>Comparison History</h1>
                        <p>
                            View and access your previous Process Compass
                            comparisons.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="history-refresh-button"
                        onClick={loadHistory}
                    >
                        <RefreshCw size={16} />
                        Refresh
                    </button>
                </div>

                <div className="history-state-container">
                    <div className="history-empty-icon">
                        <HistoryIcon size={34} />
                    </div>

                    <h3>No comparison history yet</h3>
                    <p>
                        Your completed comparisons will appear here once
                        you run your first comparison.
                    </p>
                </div>
            </section>
        );
    }

    /* -----------------------------------------------------
       HISTORY PAGE
       ----------------------------------------------------- */

    return (
        <section className="history-page">
            {/* PAGE HEADER */}

            <div className="history-page-header">
                <div>
                    <h1>Comparison History</h1>
                    <p>
                        View and access your previous Process Compass
                        comparisons.
                    </p>
                </div>

                <button
                    type="button"
                    className="history-refresh-button"
                    onClick={loadHistory}
                >
                    <RefreshCw size={16} />
                    Refresh
                </button>
            </div>

            {/* SUMMARY */}

            <div className="history-summary">
                <div className="history-summary-icon">
                    <HistoryIcon size={22} />
                </div>

                <div>
                    <span className="history-summary-label">
                        Total Comparisons
                    </span>

                    <strong className="history-summary-value">
                        {history.length}
                    </strong>
                </div>
            </div>

            {/* INLINE ERROR */}

            {error && (
                <div className="history-inline-error">
                    <AlertCircle size={17} />
                    <span>{error}</span>
                </div>
            )}

            {/* HISTORY TABLE */}

            <div className="history-table-container">
                <div className="history-table-heading">
                    <div>
                        <h2>All Comparisons</h2>
                        <p>
                            Your comparison records, arranged from newest
                            to oldest.
                        </p>
                    </div>
                </div>

                <div className="history-table-scroll">
                    <table className="history-table">
                        <thead>
                            <tr>
                                <th>Comparison</th>
                                <th>Process</th>
                                <th>Date &amp; Time</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>

                        <tbody>
                            {paginatedHistory.map((item, index) => {
                                const recordId =
                                    item.id ||
                                    item.comparison_id ||
                                    item.comparisonId ||
                                    `${currentPage}-${index}`;

                                const status = getComparisonStatus(item);

                                const canDownload = [
                                    "completed",
                                    "success",
                                    "successful",
                                ].includes(status);

                                const processName =
                                    item.process_name ||
                                    item.processName ||
                                    item.process ||
                                    "—";

                                const isDownloading =
                                    downloadingId === recordId ||
                                    downloadingId === getComparisonName(item);

                                return (
                                    <tr key={recordId}>
                                        <td>
                                            <div className="history-comparison-cell">
                                                <FileSpreadsheet
                                                    size={19}
                                                    className="history-file-icon"
                                                />

                                                <div>
                                                    <strong>
                                                        {getComparisonName(item)}
                                                    </strong>

                                                    {item.description && (
                                                        <span>
                                                            {item.description}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>

                                        <td>
                                            <span className="history-process-name">
                                                {processName}
                                            </span>
                                        </td>

                                        <td>
                                            <div className="history-date-cell">
                                                <CalendarDays size={15} />
                                                <span>
                                                    {formatDateTime(
                                                        getComparisonDate(item)
                                                    )}
                                                </span>
                                            </div>
                                        </td>

                                        <td>
                                            <StatusBadge status={item.status} />
                                        </td>

                                        <td>
                                            {canDownload ? (
                                                <button
                                                    type="button"
                                                    className="history-download-button"
                                                    onClick={() =>
                                                        handleDownload(item)
                                                    }
                                                    disabled={isDownloading}
                                                >
                                                    <Download size={15} />
                                                    {isDownloading
                                                        ? "Downloading..."
                                                        : "Download"}
                                                </button>
                                            ) : (
                                                <span className="history-no-action">
                                                    {status === "failed"
                                                        ? "No report available"
                                                        : "—"}
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                {/* PAGINATION */}

                {history.length > ITEMS_PER_PAGE && (
                    <div className="history-pagination">
                        <span className="history-pagination-info">
                            Showing {firstRecord}–{lastRecord} of{" "}
                            {history.length} comparisons
                        </span>

                        <div className="history-pagination-controls">
                            <button
                                type="button"
                                className="history-page-button"
                                onClick={() =>
                                    setCurrentPage((page) =>
                                        Math.max(1, page - 1)
                                    )
                                }
                                disabled={currentPage === 1}
                                aria-label="Previous page"
                            >
                                <ChevronLeft size={17} />
                            </button>

                            <span className="history-page-number">
                                Page {currentPage} of {totalPages}
                            </span>

                            <button
                                type="button"
                                className="history-page-button"
                                onClick={() =>
                                    setCurrentPage((page) =>
                                        Math.min(totalPages, page + 1)
                                    )
                                }
                                disabled={currentPage === totalPages}
                                aria-label="Next page"
                            >
                                <ChevronRight size={17} />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </section>
    );
}

export default History;
