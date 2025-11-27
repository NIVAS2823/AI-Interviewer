// src/pages/Interviews.jsx

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { interviewAPI } from "../lib/api";
import { Video, Loader2, Plus, Award, Trash2 } from "lucide-react";
import { formatDate, formatDuration, getScoreColor } from "../lib/utils";
import toast from "react-hot-toast";

export default function Interviews() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  // Confirm modal
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);

  /* --------------------------------------------- */
  /*                 LOAD INTERVIEWS               */
  /* --------------------------------------------- */

  const loadInterviews = async () => {
    try {
      const res = await interviewAPI.list();
      setInterviews(res.data || []);
    } catch (err) {
      toast.error("Failed to load interviews");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInterviews();
  }, []);

  /* --------------------------------------------- */
  /*                 DELETE INTERVIEW              */
  /* --------------------------------------------- */

  const handleDeleteConfirmed = async (id) => {
    try {
      await interviewAPI.delete(id);
      toast.success("Interview deleted");
      loadInterviews();
    } catch (err) {
      toast.error("Failed to delete interview");
    } finally {
      setConfirmOpen(false);
    }
  };

  const askDelete = (id) => {
    setConfirmText("Delete this interview?");
    setConfirmAction(() => () => handleDeleteConfirmed(id));
    setConfirmOpen(true);
  };

  /* --------------------------------------------- */
  /*                  FILTER LOGIC                 */
  /* --------------------------------------------- */

  const filteredInterviews = interviews.filter((i) => {
    if (filter === "all") return true;
    return i.status === filter;
  });

  /* --------------------------------------------- */
  /*                     LOADING                   */
  /* --------------------------------------------- */

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-neon-primary" />
      </div>
    );
  }

  /* --------------------------------------------- */
  /*                     RENDER                    */
  /* --------------------------------------------- */

  return (
    <div className="space-y-10 text-gray-200">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neon-primary drop-shadow-[0_0_10px_var(--neon-primary)]">
            My Interviews
          </h1>
          <p className="text-gray-400 mt-2">
            View and manage your interview sessions
          </p>
        </div>

        <Link
          to="/interviews/new"
          className="px-5 py-2 bg-neon-primary text-black font-semibold rounded-lg 
          shadow-[0_0_15px_var(--neon-primary)] hover:shadow-[0_0_25px_var(--neon-primary)] transition flex items-center"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Interview
        </Link>
      </div>

      {/* FILTERS */}
      <div className="flex items-center space-x-3 overflow-x-auto pb-2">
        {[
          { label: "All", value: "all" },
          { label: "Completed", value: "completed" },
          { label: "In Progress", value: "in_progress" },
          { label: "Created", value: "created" },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all
              ${
                filter === f.value
                  ? "bg-neon-primary text-black shadow-[0_0_15px_var(--neon-primary)]"
                  : "bg-darkbg-card border border-white/10 text-gray-300 hover:border-neon-primary hover:text-neon-primary"
              }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* EMPTY STATE */}
      {filteredInterviews.length === 0 ? (
        <div className="bg-darkbg-card border border-white/10 rounded-xl p-12 text-center shadow">
          <Video className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">
            {filter === "all" ? "No interviews yet" : `No ${filter} interviews`}
          </h3>
          <p className="text-gray-400 mb-6">
            Start practicing with AI-powered interviews
          </p>
          <Link
            to="/interviews/new"
            className="px-5 py-2 bg-neon-primary text-black rounded-lg font-medium 
            shadow-[0_0_15px_var(--neon-primary)] hover:shadow-[0_0_25px_var(--neon-primary)] transition inline-flex items-center"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create First Interview
          </Link>
        </div>
      ) : (
        <div className="grid gap-6">
          {filteredInterviews.map((interview) => {
            const iid = interview.id;

            return (
              <div
                key={iid}
                className="bg-darkbg-card border border-white/10 rounded-xl p-6 
                shadow hover:border-neon-primary hover:shadow-[0_0_25px_var(--neon-primary)] 
                transition-all flex flex-col"
              >
                {/* CLICKABLE CONTENT */}
                <Link to={`/interviews/${iid}`} className="block flex-1">
                  <div className="flex items-start justify-between">
                    {/* LEFT BLOCK */}
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="w-12 h-12 bg-[#00f0ff15] border border-neon-primary/40 
                      rounded-lg flex items-center justify-center">
                        <Video className="w-6 h-6 text-neon-primary" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-white capitalize">
                          {String(interview.interview_type).replace("_", " ")}{" "}
                          Interview
                        </h3>

                        <p className="text-sm text-gray-400 mt-1">
                          {formatDate(interview.created_at)}
                          {interview.duration_minutes &&
                            ` • ${formatDuration(interview.duration_minutes)}`}
                        </p>

                        {/* STATUS */}
                        <span
                          className={`inline-block px-3 py-1 mt-3 rounded-full text-sm font-medium
                            ${
                              interview.status === "completed"
                                ? "bg-green-500/20 text-green-300"
                                : interview.status === "in_progress"
                                ? "bg-yellow-500/20 text-yellow-300"
                                : "bg-gray-500/20 text-gray-300"
                            }`}
                        >
                          {String(interview.status).replace("_", " ")}
                        </span>
                      </div>
                    </div>

                    {/* SCORE */}
                    {interview.overall_score !== null &&
                      interview.overall_score !== undefined && (
                        <div className="text-right ml-4">
                          <div className="flex items-center space-x-2">
                            <Award className="w-5 h-5 text-yellow-400" />
                            <span
                              className={`text-3xl font-bold ${getScoreColor(
                                interview.overall_score
                              )}`}
                            >
                              {interview.overall_score}%
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 mt-1">
                            Overall Score
                          </p>
                        </div>
                      )}
                  </div>
                </Link>

                {/* DELETE BUTTON ROW AT BOTTOM */}
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      askDelete(iid);
                    }}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 
                    rounded-lg transition"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CONFIRM DELETE MODAL */}
      {confirmOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div
            className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow-xl 
          w-[90%] max-w-md text-center"
          >
            <h3 className="text-xl font-semibold text-white mb-4">
              Are you sure?
            </h3>
            <p className="text-gray-300 mb-6">{confirmText}</p>

            <div className="flex items-center justify-center space-x-4">
              <button
                className="px-5 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-400/40 
                hover:bg-red-600/30 transition"
                onClick={() => confirmAction && confirmAction()}
              >
                Yes, Delete
              </button>

              <button
                className="px-5 py-2 rounded-lg border border-white/20 text-gray-300 
                hover:bg-white/10 transition"
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
