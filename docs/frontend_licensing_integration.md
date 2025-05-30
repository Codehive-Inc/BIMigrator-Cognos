# BIMigrator Licensing System - Frontend Integration Guide

This document provides detailed instructions for integrating the BIMigrator licensing system with a Node.js-based frontend application (TypeScript/Vite).

## Overview

The frontend integration for the licensing system focuses on:
1. Displaying license status information to users
2. Handling license-related errors during migration attempts
3. Providing admin functionality for license management (optional)

## 1. Prerequisites

- Node.js 14+ and npm/yarn
- React or Vue.js frontend application
- Access to the Django backend APIs

## 2. API Integration

### 2.1 Update Environment Variables

Add the following license-related endpoints to your `.env` file:

```
# Existing environment variables
VITE_ENVIRONMENT = prod # dev or prod

# API Endpoints (existing)
VITE_AUTH_ENDPOINT = auth/login/
VITE_AUTH_REFRESH_ENDPOINT = auth/refresh/
VITE_UPLOAD_ENDPOINT = services/tasks/
VITE_STATUS_ENDPOINT = services/tasks/{id}/
VITE_START_TASK_ENDPOINT = services/tasks/{id}/start/
VITE_RESULTS_ENDPOINT = services/results/{id}/

# Development environment (existing)
VITE_DEV_API_BASE_URL=http://localhost:8000

# License API Endpoints (new)
VITE_LICENSE_STATUS_ENDPOINT = license/status/
VITE_LICENSE_VALIDATE_ENDPOINT = license/validate/
VITE_LICENSE_CREATE_ENDPOINT = license/create/
VITE_MIGRATE_ENDPOINT = migrate/
```

### 2.2 Create API Client

Create a dedicated API client for license-related operations:

```typescript
// src/api/licenseApi.ts
import axios from 'axios';

// Use the same environment variable pattern as existing code
const API_BASE_URL = import.meta.env.VITE_ENVIRONMENT === 'prod' 
  ? import.meta.env.VITE_PROD_API_BASE_URL 
  : import.meta.env.VITE_DEV_API_BASE_URL;

export interface LicenseStatus {
  is_active: boolean;
  expires_at: string;
  max_migrations: number;
  migrations_used: number;
  migrations_remaining: number;
  status_message: string;
  days_remaining: number;
  expires_at_formatted: string;
}

// Define endpoints following the existing pattern
const LICENSE_ENDPOINTS = {
  STATUS_ENDPOINT: 'license/status/',
  VALIDATE_ENDPOINT: 'license/validate/',
  CREATE_ENDPOINT: 'license/create/'
};

export const licenseApi = {
  /**
   * Get the current license status
   */
  getStatus: async (): Promise<LicenseStatus> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/${LICENSE_ENDPOINTS.STATUS_ENDPOINT}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch license status:', error);
      throw error;
    }
  },

  /**
   * Validate the license before performing a migration
   */
  validateLicense: async (): Promise<{ success: boolean; status: LicenseStatus }> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/${LICENSE_ENDPOINTS.VALIDATE_ENDPOINT}`);
      return response.data;
    } catch (error) {
      console.error('License validation failed:', error);
      throw error;
    }
  },

  /**
   * Create a new license (admin only)
   */
  createLicense: async (licenseData: any): Promise<{ success: boolean }> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/${LICENSE_ENDPOINTS.CREATE_ENDPOINT}`, licenseData);
      return response.data;
    } catch (error) {
      console.error('Failed to create license:', error);
      throw error;
    }
  }
};
```

### 2.2 Create Migration API Client

Update your migration API client to handle license-related errors:

```typescript
// src/api/migrationApi.ts
import axios from 'axios';
import { LicenseStatus } from './licenseApi';

// Use the same environment variable pattern as existing code
const API_BASE_URL = import.meta.env.VITE_ENVIRONMENT === 'prod' 
  ? import.meta.env.VITE_PROD_API_BASE_URL 
  : import.meta.env.VITE_DEV_API_BASE_URL;

// Define the migration endpoint following existing pattern
const MIGRATE_ENDPOINT = 'migrate/';

export interface MigrationResponse {
  success: boolean;
  message: string;
  output_dir?: string;
  license_status?: LicenseStatus;
  error?: string;
}

export const migrationApi = {
  /**
   * Migrate a Tableau workbook to Power BI
   */
  migrateWorkbook: async (file: File, outputDir?: string): Promise<MigrationResponse> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (outputDir) {
        formData.append('output_dir', outputDir);
      }
      
      const response = await axios.post(`${API_BASE_URL}/${MIGRATE_ENDPOINT}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        // Handle license-related errors
        if (error.response.status === 403) {
          return {
            success: false,
            message: 'License error',
            error: error.response.data.error,
            license_status: error.response.data.status
          };
        }
      }
      
      console.error('Migration failed:', error);
      throw error;
    }
  }
};
```

## 3. UI Components

### 3.1 License Status Component

Create a component to display the current license status:

```tsx
// src/components/LicenseStatus.tsx
import React, { useEffect, useState } from 'react';
import { licenseApi, LicenseStatus } from '../api/licenseApi';

export const LicenseStatusComponent: React.FC = () => {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLicenseStatus = async () => {
      try {
        setLoading(true);
        const status = await licenseApi.getStatus();
        setLicenseStatus(status);
        setError(null);
      } catch (err) {
        setError('Failed to load license status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLicenseStatus();
    
    // Poll for license status updates every 5 minutes
    const intervalId = setInterval(fetchLicenseStatus, 5 * 60 * 1000);
    
    return () => clearInterval(intervalId);
  }, []);

  if (loading) {
    return <div>Loading license status...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!licenseStatus) {
    return <div>No license information available</div>;
  }

  return (
    <div className="license-status-container">
      <h2>License Status</h2>
      <div className={`status-indicator ${licenseStatus.is_active ? 'active' : 'inactive'}`}>
        {licenseStatus.status_message}
      </div>
      
      <div className="license-details">
        <div className="detail-row">
          <span className="label">Migrations Used:</span>
          <span className="value">{licenseStatus.migrations_used}</span>
        </div>
        
        <div className="detail-row">
          <span className="label">Migrations Remaining:</span>
          <span className="value">{licenseStatus.migrations_remaining}</span>
        </div>
        
        <div className="detail-row">
          <span className="label">Migration Limit:</span>
          <span className="value">{licenseStatus.max_migrations}</span>
        </div>
        
        <div className="detail-row">
          <span className="label">Expires On:</span>
          <span className="value">{licenseStatus.expires_at_formatted}</span>
        </div>
        
        <div className="detail-row">
          <span className="label">Days Remaining:</span>
          <span className="value">{licenseStatus.days_remaining}</span>
        </div>
      </div>
    </div>
  );
};
```

### 3.2 Migration Form with License Validation

Update your migration form to include license validation:

```tsx
// src/components/MigrationForm.tsx
import React, { useState } from 'react';
import { migrationApi } from '../api/migrationApi';
import { licenseApi, LicenseStatus } from '../api/licenseApi';

export const MigrationForm: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [outputDir, setOutputDir] = useState<string>('output');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [licenseError, setLicenseError] = useState<string | null>(null);
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setResult({ success: false, message: 'Please select a file to upload' });
      return;
    }
    
    setLoading(true);
    setResult(null);
    setLicenseError(null);
    
    try {
      // First validate the license
      const licenseValidation = await licenseApi.validateLicense();
      setLicenseStatus(licenseValidation.status);
      
      // If license is valid, proceed with migration
      if (file) {
        const response = await migrationApi.migrateWorkbook(file, outputDir);
        
        if (response.success) {
          setResult({
            success: true,
            message: `Migration completed successfully. Output directory: ${response.output_dir}`
          });
          
          // Update license status after successful migration
          if (response.license_status) {
            setLicenseStatus(response.license_status);
          }
        } else {
          setResult({
            success: false,
            message: response.error || 'Migration failed'
          });
          
          if (response.license_status) {
            setLicenseStatus(response.license_status);
          }
        }
      }
    } catch (error: any) {
      // Handle license-specific errors
      if (error.response && error.response.status === 403) {
        setLicenseError(error.response.data.error || 'License validation failed');
        if (error.response.data.status) {
          setLicenseStatus(error.response.data.status);
        }
      } else {
        setResult({
          success: false,
          message: 'An error occurred during migration'
        });
      }
      console.error('Migration error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="migration-form-container">
      <h2>Migrate Tableau Workbook</h2>
      
      {licenseError && (
        <div className="license-error-banner">
          <h3>License Error</h3>
          <p>{licenseError}</p>
          {licenseStatus && !licenseStatus.is_active && (
            <p>Your license expired on {licenseStatus.expires_at_formatted}</p>
          )}
          {licenseStatus && licenseStatus.is_active && licenseStatus.migrations_remaining <= 0 && (
            <p>You have used all {licenseStatus.max_migrations} migrations allowed by your license.</p>
          )}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="file-upload">Tableau Workbook (.twb)</label>
          <input
            id="file-upload"
            type="file"
            accept=".twb"
            onChange={handleFileChange}
            disabled={loading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="output-dir">Output Directory</label>
          <input
            id="output-dir"
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            disabled={loading}
          />
        </div>
        
        <button
          type="submit"
          disabled={loading || !file}
          className="submit-button"
        >
          {loading ? 'Processing...' : 'Migrate Workbook'}
        </button>
      </form>
      
      {result && (
        <div className={`result-container ${result.success ? 'success' : 'error'}`}>
          <h3>{result.success ? 'Success!' : 'Error'}</h3>
          <p>{result.message}</p>
        </div>
      )}
    </div>
  );
};
```

### 3.3 Admin License Management Component (Optional)

Create an admin component for license management:

```tsx
// src/components/admin/LicenseManagement.tsx
import React, { useState, useEffect } from 'react';
import { licenseApi, LicenseStatus } from '../../api/licenseApi';

export const LicenseManagement: React.FC = () => {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    license_key: '',
    client_name: '',
    license_type: 'standard',
    max_migrations: 100,
    expires_at: '',
  });
  const [createSuccess, setCreateSuccess] = useState<boolean>(false);

  useEffect(() => {
    fetchLicenseStatus();
  }, []);

  const fetchLicenseStatus = async () => {
    try {
      setLoading(true);
      const status = await licenseApi.getStatus();
      setLicenseStatus(status);
      setError(null);
    } catch (err) {
      setError('Failed to load license status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setCreateSuccess(false);
    
    try {
      await licenseApi.createLicense(formData);
      setCreateSuccess(true);
      
      // Reset form
      setFormData({
        license_key: '',
        client_name: '',
        license_type: 'standard',
        max_migrations: 100,
        expires_at: '',
      });
      
      // Refresh license status
      fetchLicenseStatus();
    } catch (err) {
      setError('Failed to create license');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="license-management-container">
      <h2>License Management</h2>
      
      {/* Current License Status */}
      {loading && <div>Loading...</div>}
      
      {error && <div className="error-message">{error}</div>}
      
      {licenseStatus && (
        <div className="current-license">
          <h3>Current License</h3>
          <div className="license-details">
            <div className="detail-row">
              <span className="label">Status:</span>
              <span className="value">{licenseStatus.status_message}</span>
            </div>
            <div className="detail-row">
              <span className="label">Migrations Used:</span>
              <span className="value">{licenseStatus.migrations_used} / {licenseStatus.max_migrations}</span>
            </div>
            <div className="detail-row">
              <span className="label">Expires On:</span>
              <span className="value">{licenseStatus.expires_at_formatted}</span>
            </div>
          </div>
        </div>
      )}
      
      {/* Create New License Form */}
      <div className="create-license">
        <h3>Create New License</h3>
        
        {createSuccess && (
          <div className="success-message">License created successfully!</div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="license_key">License Key</label>
            <input
              id="license_key"
              name="license_key"
              type="text"
              value={formData.license_key}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="client_name">Client Name</label>
            <input
              id="client_name"
              name="client_name"
              type="text"
              value={formData.client_name}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="license_type">License Type</label>
            <select
              id="license_type"
              name="license_type"
              value={formData.license_type}
              onChange={handleInputChange}
              required
            >
              <option value="trial">Trial</option>
              <option value="standard">Standard</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          
          <div className="form-group">
            <label htmlFor="max_migrations">Maximum Migrations</label>
            <input
              id="max_migrations"
              name="max_migrations"
              type="number"
              min="1"
              value={formData.max_migrations}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="expires_at">Expiry Date</label>
            <input
              id="expires_at"
              name="expires_at"
              type="date"
              value={formData.expires_at}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="submit-button"
          >
            {loading ? 'Creating...' : 'Create License'}
          </button>
        </form>
      </div>
    </div>
  );
};
```

## 4. Styling

Add CSS styles for the license components:

```css
/* src/styles/license.css */
.license-status-container {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  background-color: #f9f9f9;
}

.status-indicator {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-weight: bold;
  margin-bottom: 15px;
}

.status-indicator.active {
  background-color: #d4edda;
  color: #155724;
}

.status-indicator.inactive {
  background-color: #f8d7da;
  color: #721c24;
}

.license-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.detail-row .label {
  font-weight: bold;
  color: #555;
}

.license-error-banner {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.migration-form-container {
  max-width: 600px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.submit-button {
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 16px;
}

.submit-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.result-container {
  margin-top: 20px;
  padding: 15px;
  border-radius: 4px;
}

.result-container.success {
  background-color: #d4edda;
  color: #155724;
}

.result-container.error {
  background-color: #f8d7da;
  color: #721c24;
}

.license-management-container {
  max-width: 800px;
  margin: 0 auto;
}

.current-license {
  margin-bottom: 30px;
}

.success-message {
  background-color: #d4edda;
  color: #155724;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}
```

## 5. Integration with Main Application

### 5.1 Add License Status to Dashboard

Add the license status component to your dashboard or settings page:

```tsx
// src/pages/Dashboard.tsx
import React from 'react';
import { LicenseStatusComponent } from '../components/LicenseStatus';
import { MigrationForm } from '../components/MigrationForm';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-container">
      <h1>BIMigrator Dashboard</h1>
      
      <div className="dashboard-grid">
        <div className="dashboard-sidebar">
          <LicenseStatusComponent />
          {/* Other sidebar components */}
        </div>
        
        <div className="dashboard-main">
          <MigrationForm />
          {/* Other main content */}
        </div>
      </div>
    </div>
  );
};
```

### 5.2 Add Admin License Management to Admin Panel

Add the license management component to your admin panel:

```tsx
// src/pages/AdminPanel.tsx
import React from 'react';
import { LicenseManagement } from '../components/admin/LicenseManagement';

export const AdminPanel: React.FC = () => {
  return (
    <div className="admin-panel-container">
      <h1>Admin Panel</h1>
      
      <div className="admin-sections">
        <LicenseManagement />
        {/* Other admin sections */}
      </div>
    </div>
  );
};
```

## 6. Handling License Expiry

Add a global license check to prevent usage when license is expired:

```tsx
// src/App.tsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { licenseApi, LicenseStatus } from './api/licenseApi';
import { Dashboard } from './pages/Dashboard';
import { AdminPanel } from './pages/AdminPanel';
import { LicenseExpiredPage } from './pages/LicenseExpiredPage';

export const App: React.FC = () => {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLicenseStatus = async () => {
      try {
        setLoading(true);
        const status = await licenseApi.getStatus();
        setLicenseStatus(status);
        setError(null);
      } catch (err) {
        setError('Failed to load license status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLicenseStatus();
    
    // Poll for license status updates every 5 minutes
    const intervalId = setInterval(fetchLicenseStatus, 5 * 60 * 1000);
    
    return () => clearInterval(intervalId);
  }, []);

  if (loading) {
    return <div className="loading-screen">Loading application...</div>;
  }

  if (error) {
    return <div className="error-screen">
      <h2>Error Loading Application</h2>
      <p>{error}</p>
      <button onClick={() => window.location.reload()}>Retry</button>
    </div>;
  }

  // Redirect to license expired page if license is not active
  const isLicenseActive = licenseStatus?.is_active ?? false;

  return (
    <BrowserRouter>
      <Routes>
        {!isLicenseActive && (
          <>
            <Route path="/license-expired" element={<LicenseExpiredPage licenseStatus={licenseStatus} />} />
            <Route path="*" element={<Navigate to="/license-expired" replace />} />
          </>
        )}
        
        {isLicenseActive && (
          <>
            <Route path="/" element={<Dashboard />} />
            <Route path="/admin" element={<AdminPanel />} />
            {/* Other routes */}
          </>
        )}
      </Routes>
    </BrowserRouter>
  );
};
```

Create a license expired page:

```tsx
// src/pages/LicenseExpiredPage.tsx
import React from 'react';
import { LicenseStatus } from '../api/licenseApi';

interface LicenseExpiredPageProps {
  licenseStatus: LicenseStatus | null;
}

export const LicenseExpiredPage: React.FC<LicenseExpiredPageProps> = ({ licenseStatus }) => {
  return (
    <div className="license-expired-container">
      <div className="license-expired-card">
        <h1>License Expired</h1>
        
        <div className="expired-icon">⚠️</div>
        
        <p className="expired-message">
          Your BIMigrator license has expired or is no longer valid.
        </p>
        
        {licenseStatus && (
          <div className="license-details">
            <div className="detail-row">
              <span className="label">Status:</span>
              <span className="value">{licenseStatus.status_message}</span>
            </div>
            
            {licenseStatus.expires_at && (
              <div className="detail-row">
                <span className="label">Expired On:</span>
                <span className="value">{licenseStatus.expires_at_formatted}</span>
              </div>
            )}
            
            {licenseStatus.migrations_used >= licenseStatus.max_migrations && (
              <div className="detail-row">
                <span className="label">Migrations Used:</span>
                <span className="value">{licenseStatus.migrations_used} / {licenseStatus.max_migrations}</span>
              </div>
            )}
          </div>
        )}
        
        <p className="contact-info">
          Please contact your administrator or support to renew your license.
        </p>
        
        <a href="mailto:support@bimigrator.com" className="contact-button">
          Contact Support
        </a>
      </div>
    </div>
  );
};
```

## 7. Testing

### 7.1 Testing License Status Display

1. Run the application and navigate to the dashboard
2. Verify that the license status component displays:
   - License status (active/expired)
   - Migrations used and remaining
   - Expiry date and days remaining

### 7.2 Testing License Validation During Migration

1. Upload a Tableau workbook file
2. Click the "Migrate Workbook" button
3. Verify that the license is validated before migration starts
4. Verify that the migration proceeds if the license is valid
5. Verify that an appropriate error message is displayed if the license is invalid

### 7.3 Testing License Expiry Handling

1. Modify the license in the database to be expired
2. Refresh the application
3. Verify that you are redirected to the license expired page
4. Verify that the license expired page displays the correct information

## 8. Troubleshooting

### 8.1 API Connection Issues

If you encounter issues connecting to the license API:

1. Verify that the API base URL is correct in your environment variables
2. Check that the Django backend is running and accessible
3. Check browser console for CORS-related errors
4. Verify that the API endpoints are correctly implemented in the backend

### 8.2 License Display Issues

If the license status is not displaying correctly:

1. Check the API response format in the browser developer tools
2. Verify that the license status component is correctly parsing the API response
3. Check for any JavaScript errors in the browser console

## 9. Deployment Considerations

1. **Environment Variables**: Follow the existing pattern for environment variables, separating development and production settings
2. **Error Handling**: Implement comprehensive error handling for API failures
3. **Security**: Ensure that admin license management is properly secured
4. **Performance**: Optimize license status polling frequency for production
5. **Configuration**: Update the environment configuration in your deployment pipeline to include the new license endpoints

## 10. Conclusion

This integration guide provides a comprehensive approach to integrating the BIMigrator licensing system with a Node.js-based frontend application. By following these instructions, you can implement license status display, validation during migration, and proper handling of license expiry.
