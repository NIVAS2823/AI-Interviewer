// src/pages/Dashboard.jsx
import React, { useEffect, useState } from "react";
import { resumeAPI, interviewAPI } from "../lib/api";
import {
  FileText,
  Video,
  TrendingUp,
  Plus,
  Loader2,
  Award,
} from "lucide-react";
import { formatDate, getScoreColor } from "../lib/utils";
import toast from "react-hot-toast";
import { useAuthStore } from "../store/authStore";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalResumes: 0,
    totalInterviews: 0,
    averageScore: 0,
    recentInterviews: [],
  });

  useEffect(() => {
    const run = async () => {
      try {
        const [resumesRes, interviewsRes] = await Promise.all([
          resumeAPI.list(),
          interviewAPI.list(),
        ]);
        const interviews = interviewsRes.data || [];
        const completedInterviews = interviews.filter(
          (i) =>
            i.status === "completed" &&
            (i.overall_score !== null && i.overall_score !== undefined)
        );

        const avgScore =
          completedInterviews.length > 0
            ? Math.round(
                completedInterviews.reduce(
                  (sum, i) => sum + (i.overall_score || 0),
                  0
                ) / completedInterviews.length
              )
            : 0;

        setStats({
          totalResumes: (resumesRes.data || []).length,
          totalInterviews: interviews.length,
          averageScore: avgScore,
          recentInterviews: interviews.slice(0, 5),
        });
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
        toast.error("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

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
          Welcome back, {user?.name || "User"} 👋
        </h1>
        <p className="text-gray-400 mt-2">
          Here's your interview practice overview
        </p>
      </div>

      {/* STAT CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* TOTAL RESUMES */}
        <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow-md hover:border-neon-primary hover:shadow-[0_0_20px_var(--neon-primary)] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Resumes</p>
              <p className="text-3xl font-bold text-white mt-1">
                {stats.totalResumes}
              </p>
            </div>
            <div className="w-12 h-12 bg-[#00f0ff20] border border-neon-primary/50 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-neon-primary" />
            </div>
          </div>

          <Link
            to="/resumes"
            className="text-neon-primary hover:underline text-sm font-medium mt-4 inline-flex items-center"
          >
            Manage resumes →
          </Link>
        </div>

        {/* TOTAL INTERVIEWS */}
        <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow-md hover:border-neon-green hover:shadow-[0_0_20px_var(--neon-green)] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Interviews</p>
              <p className="text-3xl font-bold text-white mt-1">
                {stats.totalInterviews}
              </p>
            </div>
            <div className="w-12 h-12 bg-[#39ff1420] border border-neon-green/50 rounded-lg flex items-center justify-center">
              <Video className="w-6 h-6 text-neon-green" />
            </div>
          </div>

          <Link
            to="/interviews"
            className="text-neon-primary hover:underline text-sm font-medium mt-4 inline-flex items-center"
          >
            View all interviews →
          </Link>
        </div>

        {/* AVERAGE SCORE */}
        <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow-md hover:border-neon-secondary hover:shadow-[0_0_20px_var(--neon-secondary)] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Average Score</p>
              <p
                className={`text-3xl font-bold mt-1 ${getScoreColor(
                  stats.averageScore
                )}`}
              >
                {stats.averageScore}%
              </p>
            </div>
            <div className="w-12 h-12 bg-[#ff00e620] border border-neon-secondary/50 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-neon-secondary" />
            </div>
          </div>

          <p className="text-gray-500 text-sm mt-4">
            {stats.averageScore >= 80
              ? "Excellent performance! 🎉"
              : stats.averageScore >= 60
              ? "Good job! Keep practicing 💪"
              : "Keep practicing to improve 📈"}
          </p>
        </div>
      </div>

      {/* ACTION BLOCKS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* UPLOAD RESUME */}
        <Link
          to="/resumes"
          className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow-md hover:scale-105 hover:border-neon-primary hover:shadow-[0_0_20px_var(--neon-primary)] transition-all cursor-pointer group"
        >
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-[#00f0ff15] border border-neon-primary/40 rounded-xl flex items-center justify-center group-hover:border-neon-primary">
              <Plus className="w-8 h-8 text-neon-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">
                Upload New Resume
              </h3>
              <p className="text-gray-400 text-sm">
                Start by uploading your resume for AI analysis
              </p>
            </div>
          </div>
        </Link>

        {/* START INTERVIEW */}
        <Link
          to="/interviews/new"
          className="bg-gradient-to-br from-[#00f0ff10] to-[#ff00e610] border border-white/10 p-6 rounded-xl shadow-md hover:scale-105 transition-all cursor-pointer group"
        >
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-white/10 border border-white/20 rounded-xl flex items-center justify-center group-hover:shadow-lg">
              <Video className="w-8 h-8 text-neon-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">
                Start Interview
              </h3>
              <p className="text-gray-400 text-sm">
                Practice with AI interviewer right now
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* RECENT INTERVIEWS */}
      <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow-md">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Recent Interviews</h2>
          <Link
            to="/interviews"
            className="text-neon-primary hover:underline text-sm font-medium"
          >
            View all →
          </Link>
        </div>

        {stats.recentInterviews.length === 0 ? (
          <div className="text-center py-12">
            <Video className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400 mb-4">No interviews yet</p>
            <Link
              to="/interviews/new"
              className="px-6 py-3 bg-neon-primary text-black rounded-lg font-semibold
              shadow-[0_0_15px_var(--neon-primary)] hover:shadow-[0_0_25px_var(--neon-primary)] transition-all"
            >
              Start Your First Interview
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {stats.recentInterviews.map((interview) => {
              const iid = interview.id || interview._id;

              return (
                <Link
                  key={iid}
                  to={`/interviews/${iid}`}
                  className="block p-4 border border-white/10 rounded-lg hover:border-neon-primary hover:shadow-[0_0_15px_var(--neon-primary)] transition-all"
                >
                  <div className="flex items-center justify-between">
                    {/* LEFT */}
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="px-3 py-1 bg-white/10 rounded-full text-sm font-medium text-gray-300 capitalize">
                          {String(interview.interview_type || "").replace(
                            "_",
                            " "
                          )}
                        </span>

                        <span
                          className={`px-3 py-1 rounded-full text-sm font-medium ${
                            interview.status === "completed"
                              ? "bg-green-500/20 text-green-300"
                              : interview.status === "in_progress"
                              ? "bg-yellow-500/20 text-yellow-300"
                              : "bg-gray-500/20 text-gray-300"
                          }`}
                        >
                          {String(interview.status || "").replace("_", " ")}
                        </span>
                      </div>

                      <p className="text-sm text-gray-400 mt-2">
                        {formatDate(interview.created_at)}
                        {interview.duration_minutes &&
                          ` • ${interview.duration_minutes} min`}
                      </p>
                    </div>

                    {/* RIGHT */}
                    {interview.overall_score !== null &&
                      interview.overall_score !== undefined && (
                        <div className="text-right">
                          <div className="flex items-center space-x-2">
                            <Award className="w-5 h-5 text-yellow-400" />
                            <span
                              className={`text-2xl font-bold ${getScoreColor(
                                interview.overall_score
                              )}`}
                            >
                              {interview.overall_score}%
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Overall Score
                          </p>
                        </div>
                      )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
