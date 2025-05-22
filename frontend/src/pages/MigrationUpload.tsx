import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import { Upload, FileUp, Download, AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface MigrationStatus {
  status: 'idle' | 'uploading' | 'uploaded' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  migrationId?: string;
  downloadUrl?: string;
};

const getStatusColor = (status: MigrationStatus['status']) => {
  switch (status) {
    case 'error':
      return 'bg-red-100 text-red-800 border-2 border-red-200';
    case 'uploaded':
      return 'bg-green-100 text-green-800 border-2 border-green-200';
    default:
      return 'bg-blue-100 text-blue-800 border-2 border-blue-200';
  }
};

export default function MigrationUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFileUpload(files[0]);
    }
  };

  const checkFileExists = async (filename: string) => {
    const response = await fetch(`/api/migration/check-file/${encodeURIComponent(filename)}`);
    const data = await response.json();
    return data.exists;
  };

  const handleFileUpload = async (uploadFile: File) => {
    try {
      setMigrationStatus({
        status: 'uploading',
        progress: 0,
        message: 'Uploading file...'
      });

      const formData = new FormData();
      formData.append('file', uploadFile);

      // Check if file exists
      const exists = await checkFileExists(uploadFile.name);
      
      if (exists) {
        const confirmOverwrite = window.confirm(
          `A file named '${uploadFile.name}' already exists. Do you want to overwrite it?`
        );
        if (!confirmOverwrite) {
          setMigrationStatus({
            status: 'idle',
            progress: 0,
            message: 'Upload cancelled.'
          });
          return;
        }
      }

      console.log('Uploading file:', uploadFile.name);
      const response = await fetch('/api/migration/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload file');
      }

      const data = await response.json();
      console.log('Upload response:', data);
      
      if (!data.migration_id) {
        throw new Error('No migration ID received from server');
      }

      // Update status to uploaded and store migration ID
      setMigrationStatus({
        status: 'uploaded',
        progress: 0,
        message: `File ${uploadFile.name} uploaded successfully. Ready to start migration.`,
        migrationId: data.migration_id
      });

    } catch (err) {
      console.error('Upload error:', err);
      setMigrationStatus({
        status: 'error',
        progress: 0,
        message: `Error: ${err instanceof Error ? err.message : 'Failed to upload file'}. Please try again.`
      });
    }
  };

  const startMigration = async () => {
    if (!migrationStatus.migrationId) {
      setMigrationStatus({
        status: 'error',
        progress: 0,
        message: 'No migration ID found'
      });
      return;
    }

    try {
      const response = await fetch(`/api/migration/start/${migrationStatus.migrationId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to start migration');
      }

      setMigrationStatus(prev => ({
        ...prev,
        status: 'processing',
        message: 'Migration started...'
      }));

      // Start polling for status
      pollMigrationStatus(migrationStatus.migrationId);

    } catch (err) {
      setMigrationStatus(prev => ({
        ...prev,
        status: 'error',
        message: err instanceof Error ? err.message : 'Failed to start migration'
      }));
    }
  };

  const pollMigrationStatus = async (id: string) => {
    try {
      const response = await fetch(`/api/migration/status/${id}`);
      const data = await response.json();

      setMigrationStatus({
        status: data.status,
        progress: data.progress,
        message: data.message,
        downloadUrl: data.downloadUrl
      });

      if (data.status === 'processing') {
        setTimeout(() => pollMigrationStatus(id), 2000);
      } else if (data.status === 'completed') {
        setMigrationStatus(prev => ({
          ...prev,
          message: 'Migration completed successfully!'
        }));
      }
    } catch (err) {
      setMigrationStatus({
        status: 'error',
        progress: 0,
        message: 'Failed to get migration status'
      });
    }
  };

  return (
    <div className="container mx-auto pt-16 pb-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Tableau to Power BI Migration</h1>
      
        {migrationStatus.message && (
        <div className={`mb-4 p-4 rounded-lg text-center ${getStatusColor(migrationStatus.status)}`}>
          <p className="text-lg">{migrationStatus.message}</p>
        </div>
      )}

      <Card className="p-6">
        {migrationStatus.status === 'idle' && (
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center ${
              dragActive ? 'border-primary bg-primary/10' : 'border-gray-300'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              Drag and drop your Tableau workbook here
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              or click to select a file
            </p>
            <input
              type="file"
              className="hidden"
              accept=".twb,.twbx"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
              id="file-upload"
            />
            <Button asChild>
              <label htmlFor="file-upload" className="cursor-pointer">
                <FileUp className="mr-2 h-4 w-4" />
                Select File
              </label>
            </Button>
          </div>
        )}

        {(migrationStatus.status === 'uploading' || migrationStatus.status === 'processing') && (
          <div className="space-y-4">
            <Progress value={migrationStatus.progress} />
            <p className="text-center text-sm text-gray-500">
              {migrationStatus.message}
            </p>
          </div>
        )}

        {migrationStatus.status === 'uploaded' && (
          <div className="text-center space-y-4">
            <div className={`mb-4 p-4 rounded-lg text-center ${getStatusColor(migrationStatus.status)}`}>
              {migrationStatus.message}
            </div>
            <div className="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <p className="text-lg font-semibold mb-2">
                  Ready to start migration
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Click the button below to start the migration process
                </p>
              </div>
              <Button 
                onClick={startMigration}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                Start Migration
              </Button>
            </div>
          </div>
        )}

        {migrationStatus.status === 'completed' && migrationStatus.downloadUrl && (
          <div className="text-center space-y-4">
            <Button asChild>
              <a href={migrationStatus.downloadUrl} download>
                <Download className="mr-2 h-4 w-4" />
                Download Results
              </a>
            </Button>
          </div>
        )}

        {migrationStatus.status === 'error' && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              {migrationStatus.message}
            </AlertDescription>
          </Alert>
        )}
        </Card>
      </div>
    </div>
  );
}
