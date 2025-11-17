// src/pages/Resumes.jsx
import React, { useEffect, useState } from 'react';
import { resumeAPI } from '../lib/api';
import { FileText, Upload, Trash2, Loader2, CheckCircle, Clock } from 'lucide-react';
import { formatDate } from '../lib/utils';
import toast from 'react-hot-toast';
import { Link } from 'react-router-dom';

export default function Resumes() {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  useEffect(() => {
    loadResumes();
  }, []);

  const loadResumes = async () => {
    try {
      const response = await resumeAPI.list();
      console.log("DEBUG Resumes List:", response.data); // 🔍 Debug
      setResumes(response.data);
    } catch (error) {
      console.error('Failed to load resumes:', error);
      toast.error('Failed to load resumes');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      toast.error('Please upload a PDF file');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error('File must be less than 10MB');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      await resumeAPI.upload(file, (progress) => setUploadProgress(progress));
      toast.success('Resume uploaded successfully!');
      loadResumes();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
      setUploadProgress(0);
      e.target.value = '';
    }
  };

  const handleDelete = async (_id, fileName) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;

    try {
      await resumeAPI.delete(_id);
      toast.success('Resume deleted');
      loadResumes();
    } catch (error) {
      console.error('Delete failed:', error);
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
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">My Resumes</h1>
        <p className="text-gray-600 mt-2">Upload and manage your resumes</p>
      </div>

      {/* Upload Section */}
      <div className="card border-2 border-dashed border-gray-300 hover:border-primary-400 transition-colors">
        <div className="text-center py-8">
          <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Your Resume</h3>
          <p className="text-gray-600 mb-6">PDF format only. Max 10MB.</p>

          <label className="btn btn-primary cursor-pointer inline-flex items-center">
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
      </div>

      {/* Resumes List */}
      {resumes.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No resumes found</h3>
          <p className="text-gray-600">Upload your first resume to begin</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {resumes.map((resume) => {
            const resumeId = resume._id || resume.id; // ✅ FIXED ID handling
            console.log("DEBUG Resume Item:", resume); // 🔍 Debug

            return (
              <div key={resumeId} className="card hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {resume.file_name}
                      </h3>

                      <p className="text-sm text-gray-600 mt-1">
                        Uploaded {formatDate(resume.uploaded_at)}
                      </p>

                      {/* Status Badge */}
                      <div className="flex items-center space-x-4 mt-3">
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                            resume.parsing_status === 'completed'
                              ? 'bg-green-100 text-green-700'
                              : resume.parsing_status === 'processing'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {resume.parsing_status === 'completed' && (
                            <CheckCircle className="w-4 h-4 mr-1" />
                          )}
                          {resume.parsing_status === 'processing' && (
                            <Clock className="w-4 h-4 mr-1 animate-spin" />
                          )}
                          {resume.parsing_status}
                        </span>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-3 mt-4">
                        <Link
                          to={`/resumes/${resumeId}`}
                          className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                        >
                          View Details →
                        </Link>

                        {resume.parsing_status === 'completed' && (
                          <Link
                            to="/interviews/new"
                            state={{ resumeId }}
                            className="text-green-600 hover:text-green-700 text-sm font-medium"
                          >
                            Start Interview →
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Delete */}
                  <button
                    onClick={() => handleDelete(resumeId, resume.file_name)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
