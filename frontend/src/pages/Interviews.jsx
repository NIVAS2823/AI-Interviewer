// src/pages/Interviews.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { interviewAPI } from '../lib/api';
import { Video, Loader2, Plus, Award } from 'lucide-react';
import { formatDate, formatDuration, getScoreColor } from '../lib/utils';
import toast from 'react-hot-toast';

export default function Interviews() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, completed, in_progress, created

  useEffect(() => {
    const run = async () => {
      await loadInterviews();
    };
    run();
  }, []);

  const loadInterviews = async () => {
    try {
      const response = await interviewAPI.list();
      setInterviews(response.data || []);
    } catch (error) {
      console.error('Failed to load interviews:', error);
      toast.error('Failed to load interviews');
    } finally {
      setLoading(false);
    }
  };

  const filteredInterviews = (interviews || []).filter((interview) => {
    if (filter === 'all') return true;
    return interview.status === filter;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Interviews</h1>
          <p className="text-gray-600 mt-2">View and manage your interview sessions</p>
        </div>
        <Link to="/interviews/new" className="btn btn-primary flex items-center">
          <Plus className="w-4 h-4 mr-2" />
          New Interview
        </Link>
      </div>

      <div className="flex items-center space-x-2 overflow-x-auto">
        {[
          { label: 'All', value: 'all' },
          { label: 'Completed', value: 'completed' },
          { label: 'In Progress', value: 'in_progress' },
          { label: 'Created', value: 'created' },
        ].map((item) => (
          <button
            key={item.value}
            onClick={() => setFilter(item.value)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
              filter === item.value ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {filteredInterviews.length === 0 ? (
        <div className="card text-center py-12">
          <Video className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {filter === 'all' ? 'No interviews yet' : `No ${filter} interviews`}
          </h3>
          <p className="text-gray-600 mb-6">Start practicing with AI-powered interviews</p>
          <Link to="/interviews/new" className="btn btn-primary inline-flex items-center">
            <Plus className="w-4 h-4 mr-2" />
            Create First Interview
          </Link>
        </div>
      ) : (
        <div className="grid gap-6">
          {filteredInterviews.map((interview) => {
            const iid = interview.id || interview._id;
            return (
              <Link key={iid} to={`/interviews/${iid}`} className="card hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Video className="w-6 h-6 text-primary-600" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 capitalize">
                        {String(interview.interview_type || '').replace('_', ' ')} Interview
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {formatDate(interview.created_at)}
                        {interview.duration_minutes && ` • ${formatDuration(interview.duration_minutes)}`}
                      </p>

                      <div className="flex items-center space-x-3 mt-3">
                        <span
                          className={`px-3 py-1 rounded-full text-sm font-medium ${
                            interview.status === 'completed' ? 'bg-green-100 text-green-700' :
                            interview.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {String(interview.status || '').replace('_', ' ')}
                        </span>

                        <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium capitalize">
                          {interview.difficulty}
                        </span>
                      </div>
                    </div>
                  </div>

                  {interview.overall_score !== null && interview.overall_score !== undefined && (
                    <div className="text-right ml-4">
                      <div className="flex items-center space-x-2">
                        <Award className="w-5 h-5 text-yellow-500" />
                        <span className={`text-3xl font-bold ${getScoreColor(interview.overall_score)}`}>
                          {interview.overall_score}%
                        </span>
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
  );
}
