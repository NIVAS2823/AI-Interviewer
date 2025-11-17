// src/pages/Dashboard.jsx
import React, { useEffect, useState } from 'react';
import { resumeAPI, interviewAPI } from '../lib/api';
import { FileText, Video, TrendingUp, Plus, Loader2, Award } from 'lucide-react';
import { formatDate, getScoreColor } from '../lib/utils';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { Link } from 'react-router-dom';

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
        const [resumesRes, interviewsRes] = await Promise.all([resumeAPI.list(), interviewAPI.list()]);
        const interviews = interviewsRes.data || [];
        const completedInterviews = interviews.filter((i) => i.status === 'completed' && (i.overall_score !== null && i.overall_score !== undefined));

        const avgScore = completedInterviews.length > 0
          ? Math.round(completedInterviews.reduce((sum, i) => sum + (i.overall_score || 0), 0) / completedInterviews.length)
          : 0;

        setStats({
          totalResumes: (resumesRes.data || []).length,
          totalInterviews: interviews.length,
          averageScore: avgScore,
          recentInterviews: interviews.slice(0, 5),
        });
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        toast.error('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user?.name || 'User'}! 👋</h1>
        <p className="text-gray-600 mt-2">Here's your interview practice overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Resumes</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalResumes}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <Link to="/resumes" className="text-primary-600 hover:text-primary-700 text-sm font-medium mt-4 inline-flex items-center">
            Manage resumes →
          </Link>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Interviews</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalInterviews}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Video className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <Link to="/interviews" className="text-primary-600 hover:text-primary-700 text-sm font-medium mt-4 inline-flex items-center">
            View all interviews →
          </Link>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Average Score</p>
              <p className={`text-3xl font-bold mt-1 ${getScoreColor(stats.averageScore)}`}>{stats.averageScore}%</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <p className="text-gray-500 text-sm mt-4">
            {stats.averageScore >= 80 ? 'Excellent performance! 🎉' :
             stats.averageScore >= 60 ? 'Good job! Keep practicing 💪' : 'Keep practicing to improve 📈'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link to="/resumes" className="card hover:shadow-lg transition-all hover:scale-105 cursor-pointer group">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center group-hover:bg-primary-200 transition-colors">
              <Plus className="w-8 h-8 text-primary-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Upload New Resume</h3>
              <p className="text-gray-600 text-sm">Start by uploading your resume for AI analysis</p>
            </div>
          </div>
        </Link>

        <Link to="/interviews/new" className="card hover:shadow-lg transition-all hover:scale-105 cursor-pointer group bg-gradient-to-br from-primary-50 to-primary-100">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center group-hover:shadow-md transition-shadow">
              <Video className="w-8 h-8 text-primary-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Start Interview</h3>
              <p className="text-gray-600 text-sm">Practice with AI interviewer right now</p>
            </div>
          </div>
        </Link>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Recent Interviews</h2>
          <Link to="/interviews" className="text-primary-600 hover:text-primary-700 text-sm font-medium">View all →</Link>
        </div>

        {stats.recentInterviews.length === 0 ? (
          <div className="text-center py-12">
            <Video className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-4">No interviews yet</p>
            <Link to="/interviews/new" className="btn btn-primary">Start Your First Interview</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {stats.recentInterviews.map((interview) => {
              const iid = interview.id || interview._id;
              return (
                <Link key={iid} to={`/interviews/${iid}`} className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700 capitalize">
                          {String(interview.interview_type || '').replace('_', ' ')}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${interview.status === 'completed' ? 'bg-green-100 text-green-700' : interview.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'}`}>
                          {String(interview.status || '').replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-2">{formatDate(interview.created_at)}{interview.duration_minutes && ` • ${interview.duration_minutes} min`}</p>
                    </div>
                    {interview.overall_score !== null && interview.overall_score !== undefined && (
                      <div className="text-right">
                        <div className="flex items-center space-x-2">
                          <Award className="w-5 h-5 text-yellow-500" />
                          <span className={`text-2xl font-bold ${getScoreColor(interview.overall_score)}`}>{interview.overall_score}%</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">Overall Score</p>
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
