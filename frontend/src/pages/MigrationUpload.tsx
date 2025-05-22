import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/use-toast";
import { Upload, FileUp, Download, AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface MigrationStatus {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  downloadUrl?: string;
}

export default function MigrationUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  });
  const { toast } = useToast();

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

  const handleFileUpload = async (file: File) => {
    try {
      setMigrationStatus({
        status: 'uploading',
        progress: 0,
        message: 'Uploading Tableau workbook...'
      });

      const formData = new FormData();
      formData.append('file', file);

      // TODO: Replace with actual API endpoint
      const response = await fetch('/api/migration/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      
      // Start polling for migration status
      pollMigrationStatus(data.migrationId);

    } catch (error) {
      setMigrationStatus({
        status: 'error',
        progress: 0,
        message: 'Failed to upload file'
      });
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to upload file. Please try again."
      });
    }
  };

  const pollMigrationStatus = async (migrationId: string) => {
    try {
      // TODO: Replace with actual API endpoint
      const response = await fetch(`/api/migration/status/${migrationId}`);
      const data = await response.json();

      setMigrationStatus({
        status: data.status,
        progress: data.progress,
        message: data.message,
        downloadUrl: data.downloadUrl
      });

      if (data.status === 'processing') {
        setTimeout(() => pollMigrationStatus(migrationId), 2000);
      } else if (data.status === 'completed') {
        toast({
          title: "Success",
          description: "Migration completed successfully!"
        });
      }
    } catch (error) {
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

        {migrationStatus.status === 'completed' && (
          <div className="text-center space-y-4">
            <h3 className="text-lg font-semibold text-green-600">
              Migration Completed Successfully!
            </h3>
            <Button asChild>
              <a href={migrationStatus.downloadUrl} download>
                <Download className="mr-2 h-4 w-4" />
                Download Power BI Files
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
