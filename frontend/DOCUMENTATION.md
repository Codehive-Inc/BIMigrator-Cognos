# Dashboard Verse Mover - Documentation

## Project Overview

Dashboard Verse Mover is an automated BI report migration tool designed to streamline the process of migrating dashboards and reports from one Business Intelligence (BI) platform to another. The primary focus is on migrating from Tableau to Power BI, but the architecture supports extensibility to other BI platforms.

## Key Features

1. **Connection Management**
   - Configure and manage connections to source and target BI platforms
   - Support for multiple connection types (Tableau Server, Tableau Cloud, Power BI Service)
   - Connection testing and status monitoring

2. **Migration Job Management**
   - Create and configure migration jobs with step-by-step workflow
   - Select source dashboards for migration
   - Configure target settings and migration parameters
   - Monitor job progress and status

3. **Dashboard Migration**
   - Extract dashboard structure, visuals, and data from source platform
   - Convert and transform to target platform format
   - Deploy to target platform with proper configurations

4. **Validation & Quality Assurance**
   - Metadata validation to ensure structural integrity
   - Data validation to verify data accuracy
   - Visual comparison between source and target dashboards
   - Functional testing to ensure interactive elements work correctly

5. **Monitoring & Reporting**
   - Dashboard with migration statistics and status
   - Detailed job logs and history
   - Validation reports and issue tracking

## System Architecture

The application is built as a modern web application with the following technology stack:

- **Frontend**: React, TypeScript, Vite
- **UI Components**: shadcn/ui, Tailwind CSS
- **State Management**: React Query
- **Routing**: React Router

The application follows a component-based architecture with a clear separation of concerns:

- **Pages**: Main application views
- **Components**: Reusable UI components
- **Hooks**: Custom React hooks for business logic
- **Lib**: Utility functions and services

## User Workflow

### 1. Setting Up Connections

Before starting any migration, users need to configure connections to both source and target BI platforms:

1. Navigate to the Connections page
2. Click "Add Connection"
3. Select connection type (Source/Target)
4. Configure connection details (URL, credentials, etc.)
5. Test the connection
6. Save the connection

### 2. Creating a Migration Job

To migrate dashboards:

1. Navigate to the Jobs page
2. Click "New Job"
3. Follow the 3-step wizard:
   - Step 1: Enter job name and select source/target connections
   - Step 2: Select source dashboards to migrate
   - Step 3: Configure target settings (workspace, overwrite options, etc.)
4. Start the migration job

### 3. Monitoring Migration Progress

During and after migration:

1. View job status on the Jobs page
2. Check detailed progress on the Job Detail page
3. Review logs for any issues or warnings

### 4. Validating Migrated Dashboards

After migration completes:

1. Navigate to the Validation page
2. Select a migrated dashboard to validate
3. Use the validation tools to compare:
   - Metadata (structure, visuals, filters)
   - Data accuracy
   - Visual appearance
   - Functional behavior
4. Approve the migration or request revisions

## Data Models

### Connection
- ID
- Name
- Type (Tableau Server, Tableau Cloud, Power BI Service)
- Connection Type (Source/Target)
- URL
- Credentials
- Status
- Last Tested Date

### Migration Job
- ID
- Name
- Source Connection
- Target Connection
- Status (Created, In Progress, Completed, Failed)
- Progress
- Created Date
- Started Date
- Completed Date
- Assets (dashboards to migrate)
- Target Configuration

### Migrated Asset
- ID
- Name
- Job ID
- Source Details
- Target Details
- Status
- Validation Status

### Validation Report
- Asset ID
- Metadata Validation
- Data Validation
- Visual Validation
- Functional Testing Results
- Issues and Warnings

## API Integration

The application integrates with various BI platform APIs:

### Tableau APIs
- Authentication
- Content Management
- Dashboard Export/Download
- Metadata Extraction

### Power BI APIs
- Authentication
- Workspace Management
- Report Creation/Upload
- Dataset Configuration

## Future Enhancements

Potential areas for future development:

1. **Support for Additional BI Platforms**
   - Looker
   - QlikView/Qlik Sense
   - MicroStrategy

2. **Advanced Migration Features**
   - Custom transformation rules
   - Data model migration
   - Scheduled migrations

3. **Enhanced Validation**
   - Automated screenshot comparison
   - AI-assisted validation
   - Regression testing

4. **Enterprise Features**
   - User management and role-based access
   - Audit logging
   - Integration with CI/CD pipelines

## Troubleshooting

Common issues and solutions:

1. **Connection Issues**
   - Verify network connectivity
   - Check credentials and permissions
   - Ensure API access is enabled on the BI platform

2. **Migration Failures**
   - Review job logs for specific errors
   - Check for unsupported features in source dashboards
   - Verify target platform capacity and permissions

3. **Validation Discrepancies**
   - Compare calculation logic between platforms
   - Check for data refresh timing differences
   - Review visual rendering differences between platforms
