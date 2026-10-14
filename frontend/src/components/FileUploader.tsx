import React, { useState, useRef } from 'react'
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { uploadDocument } from '../api/documents'

interface FileUploaderProps {
  onUploadSuccess?: () => void
}

export const FileUploader: React.FC<FileUploaderProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [successFile, setSuccessFile] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setSuccessFile(null)

    // Validation
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents are supported.')
      return
    }

    if (file.size > 20 * 1024 * 1024) {
      setError('File size exceeds the 20MB limit.')
      return
    }

    if (file.size === 0) {
      setError('Selected PDF file is empty (0 bytes).')
      return
    }

    setIsUploading(true)
    setProgress(15)

    try {
      // Simulate stepped upload progress
      const timer = setInterval(() => {
        setProgress((prev) => (prev < 80 ? prev + 20 : prev))
      }, 150)

      await uploadDocument(file)
      clearInterval(timer)
      setProgress(100)
      setSuccessFile(file.name)
      if (onUploadSuccess) {
        onUploadSuccess()
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setError(msg)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-all duration-200 ${
          isDragging
            ? 'border-emerald-500 bg-emerald-50/50'
            : 'border-slate-200 bg-slate-50/50 hover:border-emerald-400 hover:bg-slate-50'
        } ${isUploading ? 'opacity-70 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFile(e.target.files[0])
            }
          }}
          disabled={isUploading}
        />

        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 group-hover:scale-105 transition-transform">
          {isUploading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : (
            <UploadCloud className="h-6 w-6" />
          )}
        </div>

        <div className="mt-3 text-center">
          <p className="text-sm font-semibold text-slate-700">
            {isUploading ? 'Uploading & Queuing Ingestion...' : 'Click to upload or drag & drop'}
          </p>
          <p className="mt-1 text-xs text-slate-400">PDF documents up to 20MB</p>
        </div>

        {/* Progress Bar */}
        {isUploading && (
          <div className="mt-4 w-full max-w-xs">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Uploading</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Notifications */}
      {error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-in fade-in">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {successFile && !error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>
            <strong className="font-semibold">{successFile}</strong> uploaded successfully. Ingestion in progress.
          </span>
        </div>
      )}
    </div>
  )
}

export default FileUploader
