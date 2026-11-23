
import { useEffect, useState } from "react";

import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Layers,
  GitBranch,
  Upload,
} from "lucide-react";

// Custom image assets
import downloadIcon from "./assests/download.png";
import uploadIcon from "./assests/upload.png";

import {
  fetchRevisionChildPages,
  fetchRevisionRootPages,
  generateCompassConfig,
  uploadRevisionConfig,
} from "./api";


/* =========================================================
   FILE DOWNLOAD HELPER
   ========================================================= */

function saveFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.setTimeout(() => {
    window.URL.revokeObjectURL(url);
  }, 0);
}


/* =========================================================
   CONFIGURATION BUILDER COMPONENT
   ========================================================= */

function ConfigBuilder({ onConfigurationUpdated }) {

  const [mode, setMode] = useState("revision");

  const [rootPages, setRootPages] = useState([]);
  const [level2Pages, setLevel2Pages] = useState([]);

  const [selectedRootId, setSelectedRootId] = useState("");
  const [selectedLevel2Id, setSelectedLevel2Id] = useState("");

  const [loadingPages, setLoadingPages] = useState(true);
  const [working, setWorking] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [generatedFile, setGeneratedFile] = useState(null);
  const [generatedFilename, setGeneratedFilename] = useState("");


  /* =========================================================
     LOAD ROOT PROCESS LANDSCAPES
     ========================================================= */

  useEffect(() => {

    let active = true;

    fetchRevisionRootPages()
      .then((pages) => {
        if (active) {
          setRootPages(pages);
        }
      })
      .catch((err) => {
        if (active) {
          setError(
            err.message || "Could not load process landscapes."
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoadingPages(false);
        }
      });

    return () => {
      active = false;
    };

  }, []);


  /* =========================================================
     RESET GENERATED OUTPUT
     ========================================================= */

  const resetOutput = () => {
    setGeneratedFile(null);
    setGeneratedFilename("");
    setNotice("");
    setError("");
  };


  /* =========================================================
     PROCESS LANDSCAPE CHANGE
     ========================================================= */

  const handleRootChange = async (pageId) => {

    setSelectedRootId(pageId);
    setSelectedLevel2Id("");

    setLevel2Pages([]);

    resetOutput();

    if (!pageId) return;

    setLoadingPages(true);

    try {

      const pages = await fetchRevisionChildPages(pageId);

      setLevel2Pages(pages);

    } catch (err) {

      setError(
        err.message || "Could not load process pages."
      );

    } finally {

      setLoadingPages(false);

    }
  };


  /* =========================================================
     PROCESS CHANGE
     ========================================================= */

  const handleLevel2Change = (pageId) => {

    setSelectedLevel2Id(pageId);

    resetOutput();
  };


  /* =========================================================
     GENERATE COMPASS CONFIGURATION
     ========================================================= */

  const handleCompassConfig = async () => {

    if (!selectedLevel2Id || working) return;

    setWorking(true);
    resetOutput();

    try {

      const blob = await generateCompassConfig([
        selectedLevel2Id,
      ]);

      setGeneratedFile(blob);

      setGeneratedFilename(
        "Confluence_Page_Config.xml"
      );

      setNotice(
        "Compass configuration is ready to download."
      );

    } catch (err) {

      setError(
        err.message ||
        "Could not generate the Compass configuration."
      );

    } finally {

      setWorking(false);

    }
  };


  /* =========================================================
     UPLOAD REVISION CONFIGURATION
     ========================================================= */

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
        err.message ||
        "Could not upload the revision configuration."
      );

    } finally {

      setWorking(false);

    }
  };


  /* =========================================================
     CHANGE CONFIGURATION MODE
     ========================================================= */

  const changeMode = (nextMode) => {

    if (working) return;

    setMode(nextMode);

    resetOutput();
  };


  /* =========================================================
     UI
     ========================================================= */

  return (

    <div className="config-builder">

      {/* PAGE HEADING */}

      <div className="page-heading">

        <div>

          <div className="eyebrow">
            CONFIGURATION
          </div>

          <h2>Configuration Tools</h2>

          <p>
            Manage revision configuration and generate
            Process Compass page tree files.
          </p>

        </div>

      </div>


      {/* CONFIGURATION CARD */}

      <section className="content-card config-card">

        {/* WORKFLOW TABS */}

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
            disabled={working}
          >

            <GitBranch size={17} />

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
            disabled={working}
          >

            <Layers size={17} />

            Compass page tree

          </button>

        </div>


        {/* SECTION HEADING */}

        <div className="section-heading">

          <div className="section-icon">

            {mode === "revision" ? (
              <GitBranch size={20} />
            ) : (
              <Layers size={20} />
            )}

          </div>

          <div>

            <h3>
              {mode === "revision"
                ? "Revision configuration"
                : "Process Selection"}
            </h3>

            <p>
              {mode === "revision"
                ? "Upload an existing revision configuration XML file."
                : "Choose a process to generate its Compass page tree."}
            </p>

          </div>

        </div>


        {/* REVISION CONFIGURATION CONTENT */}

        {mode === "revision" && (

          <div className="config-mode-content">

            <div className="config-upload-area">

              <div className="config-upload-icon">

                <Upload size={25} />

              </div>

              <div className="config-upload-text">

                <h4>Upload revision configuration</h4>

                <p>
                  Select the XML configuration file to activate
                  the revision configuration.
                </p>

              </div>

            </div>


            <div className="config-actions">

              <label
                className={`upload-config ${
                  working ? "disabled" : ""
                }`}
              >

                <img
                  src={uploadIcon}
                  alt=""
                  className="button-icon"
                />

                {working
                  ? "Uploading..."
                  : "Upload XML"}

                <input
                  type="file"
                  accept=".xml,application/xml,text/xml"
                  onChange={handleUpload}
                  disabled={working}
                />

              </label>

            </div>

          </div>

        )}


        {/* COMPASS PAGE TREE CONTENT */}

        {mode === "compass" && (

          <div className="config-mode-content">

            <div className="selection-grid config-selection-grid">

              {/* PROCESS LANDSCAPE */}

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
                  disabled={
                    loadingPages && rootPages.length === 0
                  }
                >

                  <option value="">

                    {loadingPages && rootPages.length === 0
                      ? "Loading..."
                      : "-- Select Landscape --"}

                  </option>

                  {rootPages.map((page) => (

                    <option
                      key={page.id}
                      value={page.id}
                    >
                      {page.title}
                    </option>

                  ))}

                </select>

              </div>


              {/* PROCESS */}

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
                  disabled={
                    !selectedRootId || loadingPages
                  }
                >

                  <option value="">
                    -- Select Process --
                  </option>

                  {level2Pages.map((page) => (

                    <option
                      key={page.id}
                      value={page.id}
                    >
                      {page.title}
                    </option>

                  ))}

                </select>

              </div>

            </div>


            {/* LOADING STATUS */}

            {loadingPages && (

              <div className="config-loading">

                <span className="loading-spinner" />

                Loading process information...

              </div>

            )}


            {/* EMPTY PROCESS LANDSCAPE */}

            {!loadingPages &&
              rootPages.length === 0 && (

                <div className="connection-notice">

                  <AlertCircle size={17} />

                  <span>
                    Could not load process landscapes.
                    Check the backend connection and
                    Confluence settings.
                  </span>

                </div>

              )}


            {/* NO CHILD PROCESSES */}

            {!loadingPages &&
              selectedRootId &&
              level2Pages.length === 0 && (

                <div className="empty-state">

                  No processes found for the selected
                  Process Landscape.

                </div>

              )}


            {/* GENERATE XML ACTION */}

            <div className="config-actions">

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


              {/* DOWNLOAD GENERATED XML */}

              {generatedFile && (

                <button
                  type="button"
                  className="download-button"
                  onClick={() =>
                    saveFile(
                      generatedFile,
                      generatedFilename
                    )
                  }
                >

                  <img
                    src={downloadIcon}
                    alt=""
                    className="button-icon"
                  />

                  Download XML

                </button>

              )}

            </div>

          </div>

        )}


        {/* ERROR MESSAGE */}

        {error && (

          <div
            className="error-message"
            role="alert"
          >

            <AlertCircle size={18} />

            <span>{error}</span>

          </div>

        )}


        {/* SUCCESS MESSAGE */}

        {notice && (

          <div
            className="success-message"
            role="status"
          >

            <CheckCircle2 size={18} />

            <span>{notice}</span>

          </div>

        )}

      </section>

    </div>

  );
}

export default ConfigBuilder;
