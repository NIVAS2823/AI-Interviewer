// src/pages/InterviewNew.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { resumeAPI, interviewAPI } from '../lib/api';
import { Loader2, Video, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function InterviewNew() {
  const navigate = useNavigate();
  const location = useLocation();
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [formData, setFormData] = useState({
    resume_id: location.state?.resumeId || '',
    interview_type: 'mixed',
    difficulty: 'medium',
    max_questions: 5,
  });

  useEffect(() => {
    const run = async () => {
      try {
        const response = await resumeAPI.list();
        const completedResumes = (response.data || []).filter(
          (r) => r.parsing_status === 'completed'
        );
        setResumes(completedResumes);

        if (!formData.resume_id && completedResumes.length > 0) {
          // default to first resume if none provided
          setFormData((f) => ({ ...f, resume_id: completedResumes[0]._id || completedResumes[0].id }));
        }

        if (completedResumes.length === 0) {
          toast.error('Please upload a resume first');
          navigate('/resumes');
        }
      } catch (error) {
        console.error('Failed to load resumes:', error);
        toast.error('Failed to load resumes');
      } finally {
        setLoading(false);
      }
    };

    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((s) => ({ ...s, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.resume_id) {
      toast.error('Please select a resume');
      return;
    }

    setCreating(true);

    try {
      const payload = {
        resume_id: formData.resume_id,
        interview_type: formData.interview_type,
        difficulty: formData.difficulty,
        max_questions: Number(formData.max_questions),
      };
      const response = await interviewAPI.create(payload);
      const interview_id = response.data?.interview_id || response.data?.id;
      toast.success('Interview created successfully!');
      navigate(`/interviews/${interview_id}`);
    } catch (error) {
      console.error('Failed to create interview:', error);
      // interceptor handles toast
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Video className="w-8 h-8 text-primary-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Create New Interview</h1>
        <p className="text-gray-600 mt-2">Configure your AI interview session</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="label">Select Resume *</label>
            <select
              name="resume_id"
              value={formData.resume_id}
              onChange={handleChange}
              className="input"
              required
            >
              <option value="">Choose a resume...</option>
              {resumes.map((resume) => (
                <option key={resume._id || resume.id} value={resume._id || resume.id}>
                  {resume.file_name} (Score: {resume.completeness_score}%)
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Questions will be generated based on your resume
            </p>
          </div>

          <div>
            <label className="label">Interview Type *</label>
            <select
              name="interview_type"
              value={formData.interview_type}
              onChange={handleChange}
              className="input"
              required
            >
              <option value="technical">Technical</option>
              <option value="behavioral">Behavioral</option>
              <option value="hr">HR Screening</option>
              <option value="mixed">Mixed (Recommended)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {formData.interview_type === 'technical' &&
                'Focus on technical skills and problem-solving'}
              {formData.interview_type === 'behavioral' &&
                'Focus on past experiences and soft skills'}
              {formData.interview_type === 'hr' &&
                'Focus on motivation, culture fit, and logistics'}
              {formData.interview_type === 'mixed' &&
                'Balanced mix of technical, behavioral, and HR questions'}
            </p>
          </div>

          <div>
            <label className="label">Difficulty Level *</label>
            <div className="grid grid-cols-3 gap-4">
              {['easy', 'medium', 'hard'].map((level) => (
                <label
                  key={level}
                  className={`flex items-center justify-center p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                    formData.difficulty === level
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="difficulty"
                    value={level}
                    checked={formData.difficulty === level}
                    onChange={handleChange}
                    className="sr-only"
                  />
                  <span className="font-medium capitalize">{level}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="label">Number of Questions: {formData.max_questions}</label>
            <input
              type="range"
              name="max_questions"
              min="3"
              max="10"
              value={formData.max_questions}
              onChange={handleChange}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>3 (Quick)</span>
              <span>10 (Comprehensive)</span>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">What to expect:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>AI interviewer will ask {formData.max_questions} personalized questions</li>
                  <li>Questions based on your resume and selected type</li>
                  <li>Interview typically takes 15-25 minutes</li>
                  <li>Instant feedback and evaluation after completion</li>
                </ul>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={creating || !formData.resume_id}
            className="btn btn-primary w-full flex items-center justify-center text-lg py-3"
          >
            {creating ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Creating Interview...
              </>
            ) : (
              <>
                <Video className="w-5 h-5 mr-2" />
                Create Interview
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
