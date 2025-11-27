import React, { useEffect, useState } from "react";
import { resumeAPI } from "../lib/api";
import {
  FileText,
  Upload,
  Trash2,
  Loader2,
  CheckCircle,
  Clock,
} from "lucide-react";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";



export default function Resumes() {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Confirm modal UI state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);



  const loadResumes = async () => {
    try {
      const response = await resumeAPI.list();

      const sorted = [...response.data].sort(
        (a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at)
      );

      setResumes(sorted);
    } catch (error) {
      console.error("Failed to load resumes:", error);
      toast.error("Failed to load resumes");
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 3s until parsing is completed
  useEffect(() => {
    loadResumes();

    const interval = setInterval(() => {
      const stillProcessing = resumes.some(
        (r) => r.parsing_status === "processing"
      );
      if (stillProcessing) loadResumes();
    }, 3000);

    return () => clearInterval(interval);
  }, [resumes]);

  /* ------------------------------------------------------------------ */
  /*                             UPLOAD                                 */
  /* ------------------------------------------------------------------ */

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      toast.error("Please upload a PDF file");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error("File must be less than 10MB");
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      await resumeAPI.upload(file, (p) => setUploadProgress(p));
      toast.success("Resume uploaded!");
      loadResumes();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error("Upload failed");
    } finally {
      setUploading(false);
      setUploadProgress(0);
      e.target.value = "";
    }
  };

  /* ------------------------------------------------------------------ */
  /*                           DELETE RESUME                            */
  /* ------------------------------------------------------------------ */

  const handleDeleteConfirmed = async (id) => {
    try {
      await resumeAPI.delete(id);
      toast.success("Resume deleted");
      loadResumes();
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete resume");
    } finally {
      setConfirmOpen(false);
    }
  };

  const askDelete = (id, fileName) => {
    setConfirmText(`Delete "${fileName}"?`);
    setConfirmAction(() => () => handleDeleteConfirmed(id));
    setConfirmOpen(true);
  };

  /* ------------------------------------------------------------------ */
  /*                             RENDER                                 */
  /* ------------------------------------------------------------------ */

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-neon-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-10 text-gray-200">
      {/* HEADER */}
      <div>
        <h1 className="text-3xl font-bold text-neon-primary drop-shadow-[0_0_10px_var(--neon-primary)]">
          My Resumes
        </h1>
        <p className="text-gray-400 mt-2">Upload and manage your resumes</p>
      </div>

      {/* UPLOAD BOX */}
      <div
        className="border-2 border-dashed border-white/20 bg-darkbg-card 
        p-10 text-center rounded-xl hover:border-neon-primary 
        hover:shadow-[0_0_20px_var(--neon-primary)] transition-all"
      >
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />

        <h3 className="text-lg font-semibold text-white mb-2">
          Upload Your Resume
        </h3>
        <p className="text-gray-500 mb-6">PDF format only. Max 10MB.</p>

        <label
          className="px-6 py-3 inline-flex items-center rounded-lg cursor-pointer
          bg-neon-primary text-black font-medium shadow-[0_0_15px_var(--neon-primary)]
          hover:shadow-[0_0_25px_var(--neon-primary)] transition-all"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Uploading {uploadProgress}%
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-2" />
              Choose File
            </>
          )}

          <input
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>

      {/* RESUME LIST */}
      {resumes.length === 0 ? (
        <div className="bg-darkbg-card border border-white/10 p-10 text-center rounded-xl shadow">
          <FileText className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">
            No resumes found
          </h3>
          <p className="text-gray-500">Upload your first resume to begin</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {resumes.map((resume) => {
            const resumeId = resume._id || resume.id;

            return (
              <div
                key={resumeId}
                className="bg-darkbg-card border border-white/10 p-6 rounded-xl 
                shadow-md hover:border-neon-primary hover:shadow-[0_0_20px_var(--neon-primary)] 
                transition-all"
              >
                <div className="flex items-start justify-between">
                  {/* LEFT */}
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="w-12 h-12 bg-[#00f0ff15] border border-neon-primary/40 
                    rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-neon-primary" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-white truncate">
                        {resume.file_name}
                      </h3>
                      <p className="text-sm text-gray-400 mt-1">
                        Uploaded {formatDate(resume.uploaded_at)}
                      </p>

                      {/* STATUS */}
                      <div className="mt-3">
                        <span
                          className={`inline-flex items-center px-3 py-1 text-sm rounded-full font-medium
                          ${
                            resume.parsing_status === "completed"
                              ? "bg-green-500/20 text-green-300"
                              : resume.parsing_status === "processing"
                              ? "bg-yellow-500/20 text-yellow-300"
                              : "bg-red-500/20 text-red-300"
                          }`}
                        >
                          {resume.parsing_status === "completed" && (
                            <CheckCircle className="w-4 h-4 mr-1" />
                          )}
                          {resume.parsing_status === "processing" && (
                            <Clock className="w-4 h-4 mr-1 animate-spin" />
                          )}
                          {resume.parsing_status}
                        </span>
                      </div>

                      {/* ACTIONS */}
                      <div className="flex items-center space-x-4 mt-4">
                        <Link
                          to={`/resumes/${resumeId}`}
                          className="text-neon-primary hover:underline text-sm"
                        >
                          View Details →
                        </Link>

                        {resume.parsing_status === "completed" && (
                          <Link
                            to="/interviews/new"
                            state={{ resumeId }}
                            className="text-neon-green hover:underline text-sm"
                          >
                            Start Interview →
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* DELETE */}
                  <button
                    onClick={() => askDelete(resumeId, resume.file_name)}
                    className="p-2 text-gray-400 hover:text-red-500 
                    hover:bg-red-500/10 rounded-lg transition"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CONFIRM MODAL */}
      {confirmOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow-xl w-[90%] max-w-md text-center">
            <h3 className="text-xl font-semibold text-white mb-4">
              Are you sure?
            </h3>
            <p className="text-gray-300 mb-6">{confirmText}</p>

            <div className="flex items-center justify-center space-x-4">
              <button
                className="px-5 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-400/40 hover:bg-red-600/30 transition"
                onClick={() => confirmAction && confirmAction()}
              >
                Yes, Delete
              </button>

              <button
                className="px-5 py-2 rounded-lg border border-white/20 text-gray-300 hover:bg-white/10 transition"
                onClick={() => setConfirmOpen(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
