// src/pages/ResumeDetail.jsx
import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { resumeAPI } from '../lib/api';
import { Loader2, ArrowLeft, Briefcase, GraduationCap, Award, Code } from 'lucide-react';
import { formatDate } from '../lib/utils';
import toast from 'react-hot-toast';

export default function ResumeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log("DEBUG ResumeDetail useParams id:", id); // 🔍 Debug
    if (!id) return;
    loadResume();
  }, [id]);

  const loadResume = async () => {
    try {
      const response = await resumeAPI.get(id);
      console.log("DEBUG ResumeDetail API Response:", response.data); // 🔍 Debug
      setResume(response.data);
    } catch (error) {
      console.error('Failed to load resume:', error);
      toast.error('Failed to load resume');
      navigate('/resumes');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!resume) return null;

  const { parsed_data } = resume;

  return (
    <div className="space-y-8">
      {/* Back button */}
      <Link
        to="/resumes"
        className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Resumes
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{resume.file_name}</h1>
          <p className="text-gray-600 mt-2">Uploaded {formatDate(resume.uploaded_at)}</p>
        </div>

        <Link
          to="/interviews/new"
          state={{ resumeId: resume._id || resume.id }} // ✅ FIXED
          className="btn btn-primary"
        >
          Start Interview
        </Link>
      </div>

      {/* Score */}
      <div className="card bg-gradient-to-br from-primary-50 to-primary-100">
        <div className="text-center py-6">
          <p className="text-gray-700 mb-2">Completeness Score</p>
          <p className="text-5xl font-bold text-primary-700">
            {resume.completeness_score}%
          </p>
        </div>
      </div>

      {/* Parsed Data */}
      {parsed_data ? (
        <div className="grid gap-6">

          {/* Personal Info */}
          {(parsed_data.name || parsed_data.email || parsed_data.phone) && (
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Personal Information</h2>
              {parsed_data.name && <p><strong>Name:</strong> {parsed_data.name}</p>}
              {parsed_data.email && <p><strong>Email:</strong> {parsed_data.email}</p>}
              {parsed_data.phone && <p><strong>Phone:</strong> {parsed_data.phone}</p>}
            </div>
          )}

          {/* Summary */}
          {parsed_data.summary && (
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Summary</h2>
              <p>{parsed_data.summary}</p>
            </div>
          )}

          {/* Skills */}
          {parsed_data.skills?.length > 0 && (
            <div className="card">
              <div className="flex items-center space-x-2 mb-4">
                <Code className="w-5 h-5 text-primary-600" />
                <h2 className="text-xl font-bold">Skills</h2>
              </div>

              <div className="flex flex-wrap gap-2">
                {parsed_data.skills.map((skill, i) => (
                  <span key={i} className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Experience */}
          {parsed_data.experience?.length > 0 && (
            <div className="card">
              <div className="flex items-center space-x-2 mb-4">
                <Briefcase className="w-5 h-5 text-primary-600" />
                <h2 className="text-xl font-bold">Experience</h2>
              </div>

              {parsed_data.experience.map((exp, i) => (
                <div key={i} className="border-l-2 border-primary-300 pl-4 mb-4">
                  <h3 className="font-semibold">{exp.role}</h3>
                  <p>{exp.company}</p>
                  <p className="text-sm text-gray-600">{exp.duration}</p>
                </div>
              ))}
            </div>
          )}

          {/* Education */}
          {parsed_data.education?.length > 0 && (
            <div className="card">
              <div className="flex items-center space-x-2 mb-4">
                <GraduationCap className="w-5 h-5 text-primary-600" />
                <h2 className="text-xl font-bold">Education</h2>
              </div>

              {parsed_data.education.map((edu, i) => (
                <div key={i} className="mb-3">
                  <h3 className="font-semibold">{edu.degree} in {edu.field}</h3>
                  <p>{edu.institution}</p>
                </div>
              ))}
            </div>
          )}

          {/* Certifications */}
          {parsed_data.certifications?.length > 0 && (
            <div className="card">
              <div className="flex items-center space-x-2 mb-4">
                <Award className="w-5 h-5 text-primary-600" />
                <h2 className="text-xl font-bold">Certifications</h2>
              </div>

              <ul className="list-disc ml-5">
                {parsed_data.certifications.map((cert, i) => (
                  <li key={i}>{cert}</li>
                ))}
              </ul>
            </div>
          )}

        </div>
      ) : (
        <div className="text-center text-gray-500">Resume not parsed yet.</div>
      )}
    </div>
  );
}
