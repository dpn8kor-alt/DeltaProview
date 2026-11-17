import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Layers,
} from "lucide-react";

import {
  fetchRevisionChildPages,
  fetchRevisionRootPages,
  generateCompassConfig,
  generateRevisionConfig,
  uploadRevisionConfig,
} from "./api";

function saveFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
}

function ConfigBuilder({ onConfigurationUpdated }) {
  const [mode, setMode] = useState("revision");
  const [rootPages, setRootPages] = useState([]);
  const [level2Pages, setLevel2Pages] = useState([]);
  const [methodPages, setMethodPages] = useState([]);

  const [selectedRootId, setSelectedRootId] = useState("");
  const [selectedLevel2Id, setSelectedLevel2Id] = useState("");
  const [selectedMethodId, setSelectedMethodId] = useState("");

  const [loadingPages, setLoadingPages] = useState(true);
  const [working, setWorking] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [generatedFile, setGeneratedFile] = useState(null);
  const [generatedFilename, setGeneratedFilename] = useState("");

  useEffect(() => {
    let active = true;

    fetchRevisionRootPages()
      .then((pages) => {
        if (active) setRootPages(pages);
      })
      .catch((err) => {
        if (active) {
          setError(err.message || "Could not load process landscapes.");
        }
      })
      .finally(() => {
        if (active) setLoadingPages(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const resetOutput = () => {
    setGeneratedFile(null);
    setGeneratedFilename("");
    setNotice("");
    setError("");
  };

  const handleRootChange = async (pageId) => {
    setSelectedRootId(pageId);
    setSelectedLevel2Id("");
    setSelectedMethodId("");

    setLevel2Pages([]);
    setMethodPages([]);

    resetOutput();

    if (!pageId) return;

    setLoadingPages(true);

    try {
      setLevel2Pages(await fetchRevisionChildPages(pageId));
    } catch (err) {
      setError(err.message || "Could not load process pages.");
    } finally {
      setLoadingPages(false);
    }
  };

  const handleLevel2Change = async (pageId) => {
    setSelectedLevel2Id(pageId);
    setSelectedMethodId("");

    setMethodPages([]);

    resetOutput();

    if (!pageId) return;

    setLoadingPages(true);

    try {
      setMethodPages(await fetchRevisionChildPages(pageId));
    } catch (err) {
      setError(err.message || "Could not load methods.");
    } finally {
      setLoadingPages(false);
    }
  };

  const handleRevisionConfig = async () => {
    const selectedMethod = methodPages.find(
      (page) => String(page.id) === selectedMethodId
    );

    const pages = selectedMethod
      ? [{ id: String(selectedMethod.id), title: selectedMethod.title }]
      : [];

    setWorking(true);
    resetOutput();

    try {
      const blob = await generateRevisionConfig(pages);

      const file = new File([blob], "revision-config.xml", {
        type: "application/xml",
      });

      const result = await uploadRevisionConfig(file);

      setGeneratedFile(blob);
      setGeneratedFilename("output.xml");

      setNotice(
        `Configuration activated for ${result.total_pages} process pages.`
      );

      onConfigurationUpdated?.();
    } catch (err) {
      setError(
        err.message ||
          "Could not create or activate the revision configuration."
      );
    } finally {
      setWorking(false);
    }
  };

  const handleCompassConfig = async () => {
    setWorking(true);
    resetOutput();

    try {
      const blob = await generateCompassConfig([selectedLevel2Id]);

      setGeneratedFile(blob);
      setGeneratedFilename("Confluence_Page_Config.xml");

      setNotice("Compass configuration is ready to download.");
    } catch (err) {
      setError(
        err.message || "Could not generate the Compass configuration."
      );
    } finally {
      setWorking(false);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];

    event.target.value = "";

    if (!file) return;

    setWorking(true);
    resetOutput();

    try {
      const result = await uploadRevisionConfig(file);

      setNotice(
        `Configuration activated for ${result.total_pages} process pages.`
      );

      onConfigurationUpdated?.();
    } catch (err) {
      setError(
        err.message || "Could not upload the revision configuration."
      );
    } finally {
      setWorking(false);
    }
  };

  const changeMode = (nextMode) => {
    setMode(nextMode);
    resetOutput();
  };

  return (
    <div className="config-builder">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CREATE REVISION CONFIG</div>
          <h2>Configuration Tools</h2>
          <p>
            Generate revision history or Compass page-tree XML.
          </p>
        </div>
      </div>

      <div
        className="workflow-tabs"
        role="tablist"
        aria-label="Configuration type"
      >
        <button
          type="button"
          className={`workflow-tab ${
            mode === "revision" ? "active" : ""
          }`}
          onClick={() => changeMode("revision")}
          role="tab"
          aria-selected={mode === "revision"}
        >
          Revision configuration
        </button>

        <button
          type="button"
          className={`workflow-tab ${
            mode === "compass" ? "active" : ""
          }`}
          onClick={() => changeMode("compass")}
          role="tab"
          aria-selected={mode === "compass"}
        >
          Compass page tree
        </button>
      </div>

      <section className="content-card config-card">
        <div className="section-heading">
          <div className="section-icon">
            <Layers size={20} />
          </div>

          <div>
            <h3>Process Selection</h3>
            <p>
              {mode === "revision"
                ? "Choose methods to include in revision history."
                : "Choose a process to build its Compass page tree."}
            </p>
          </div>
        </div>

        <div className="selection-grid config-selection-grid">
          <div className="form-group">
            <label htmlFor="root-page">
              Process Landscape
            </label>

            <select
              id="root-page"
              value={selectedRootId}
              onChange={(event) =>
                handleRootChange(event.target.value)
              }
              disabled={loadingPages && rootPages.length === 0}
            >
              <option value="">
                {loadingPages && rootPages.length === 0
                  ? "Loading..."
                  : "-- Select Landscape --"}
              </option>

              {rootPages.map((page) => (
                <option key={page.id} value={page.id}>
                  {page.title}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="level2-page">
              Process
            </label>

            <select
              id="level2-page"
              value={selectedLevel2Id}
              onChange={(event) =>
                handleLevel2Change(event.target.value)
              }
              disabled={!selectedRootId || loadingPages}
            >
              <option value="">
                -- Select Process --
              </option>

              {level2Pages.map((page) => (
                <option key={page.id} value={page.id}>
                  {page.title}
                </option>
              ))}
            </select>
          </div>

          {mode === "revision" && (
            <div className="form-group">
              <label htmlFor="method-page">
                Method
              </label>

              <select
                id="method-page"
                value={selectedMethodId}
                onChange={(event) => {
                  setSelectedMethodId(event.target.value);
                  resetOutput();
                }}
                disabled={!selectedLevel2Id || loadingPages}
              >
                <option value="">
                  {!selectedLevel2Id
                    ? "-- Select Process First --"
                    : loadingPages
                    ? "Loading methods..."
                    : "-- Select Method --"}
                </option>

                {methodPages.map((page) => (
                  <option key={page.id} value={page.id}>
                    {page.title}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {!loadingPages && rootPages.length === 0 && (
          <div className="connection-notice">
            <AlertCircle size={17} />

            <span>
              Could not load process landscapes. Check the backend
              connection and Confluence settings.
            </span>
          </div>
        )}

        {loadingPages && (
          <div className="config-loading">
            Loading process information...
          </div>
        )}

        <div className="config-actions">
          {mode === "revision" ? (
            <>
              <button
                type="button"
                className="compare-button"
                onClick={handleRevisionConfig}
                disabled={!selectedMethodId || working}
              >
                <FileSpreadsheet size={17} />

                {working
                  ? "Generating..."
                  : "Generate and activate"}
              </button>

              <label
                className={`upload-config ${
                  working ? "disabled" : ""
                }`}
              >
                Upload XML

                <input
                  type="file"
                  accept=".xml,application/xml,text/xml"
                  onChange={handleUpload}
                  disabled={working}
                />
              </label>
            </>
          ) : (
            <button
              type="button"
              className="compare-button"
              onClick={handleCompassConfig}
              disabled={!selectedLevel2Id || working}
            >
              <FileSpreadsheet size={17} />

              {working
                ? "Generating..."
                : "Generate Compass XML"}
            </button>
          )}

          {generatedFile && (
            <button
              type="button"
              className="download-button"
              onClick={() =>
                saveFile(generatedFile, generatedFilename)
              }
            >
              <Download size={17} />
              Download XML
            </button>
          )}
        </div>

        {error && (
          <div className="error-message" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {notice && (
          <div className="success-message" role="status">
            <CheckCircle2 size={18} />
            <span>{notice}</span>
          </div>
        )}
      </section>
    </div>
  );
}

export default ConfigBuilder;