
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CheckCircle2, Clock, FileUp, Plus, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';

// Mock jobs data
const mockJobs = [
  {
    id: 'JOB-2023-05',
    name: 'Sales Performance Dashboards',
    source: 'Tableau Production',
    sourceType: 'Tableau Server',
    target: 'Power BI Production',
    targetType: 'Power BI Service',
    status: 'Completed',
    progress: 100,
    createdAt: '2023-03-05T14:30:00',
    completedAt: '2023-03-05T14:45:00',
    assetsCount: 5
  },
  {
    id: 'JOB-2023-04',
    name: 'Marketing Campaign Analytics',
    source: 'Tableau Production',
    sourceType: 'Tableau Server',
    target: 'Power BI Production',
    targetType: 'Power BI Service',
    status: 'In Progress',
    progress: 65,
    createdAt: '2023-03-05T11:15:00',
    completedAt: null,
    assetsCount: 3
  },
  {
    id: 'JOB-2023-03',
    name: 'Supply Chain Overview',
    source: 'Tableau Development',
    sourceType: 'Tableau Server',
    target: 'Power BI Development',
    targetType: 'Power BI Service',
    status: 'In Progress',
    progress: 28,
    createdAt: '2023-03-05T09:45:00',
    completedAt: null,
    assetsCount: 2
  },
  {
    id: 'JOB-2023-02',
    name: 'Financial Reporting',
    source: 'Tableau Analytics',
    sourceType: 'Tableau Cloud',
    target: 'Power BI Production',
    targetType: 'Power BI Service',
    status: 'Failed',
    progress: 45,
    createdAt: '2023-03-04T16:20:00',
    completedAt: '2023-03-04T16:35:00',
    assetsCount: 4,
    error: 'Connection to target system failed'
  },
  {
    id: 'JOB-2023-01',
    name: 'HR Analytics Dashboards',
    source: 'Tableau File',
    sourceType: 'Tableau File',
    target: 'Power BI Production',
    targetType: 'Power BI Service',
    status: 'Completed',
    progress: 100,
    createdAt: '2023-03-03T13:10:00',
    completedAt: '2023-03-03T13:25:00',
    assetsCount: 2
  }
];

const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState(mockJobs);
  const [statusFilter, setStatusFilter] = useState('all');
  
  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'Completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'In Progress':
        return <RefreshCw className="h-4 w-4 text-amber-500" />;
      case 'Failed':
        return <Clock className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };
  
  const getStatusBadge = (status: string) => {
    let classes = '';
    switch(status) {
      case 'Completed':
        classes = 'bg-green-100 text-green-800';
        break;
      case 'In Progress':
        classes = 'bg-amber-100 text-amber-800';
        break;
      case 'Failed':
        classes = 'bg-red-100 text-red-800';
        break;
      default:
        classes = 'bg-gray-100 text-gray-800';
    }
    
    return (
      <div className="flex items-center space-x-1.5">
        {getStatusIcon(status)}
        <Badge className={classes} variant="outline">
          {status}
        </Badge>
      </div>
    );
  };
  
  const filteredJobs = statusFilter === 'all' 
    ? jobs 
    : jobs.filter(job => job.status.toLowerCase() === statusFilter);
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Migration Jobs</h1>
        <Button onClick={() => navigate('/new-job')}>
          <Plus className="mr-2 h-4 w-4" />
          New Migration Job
        </Button>
      </div>
      
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">Filter:</span>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Jobs</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="in progress">In Progress</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" size="sm" className="flex items-center">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {filteredJobs.map((job) => (
          <Link key={job.id} to={`/jobs/${job.id}`}>
            <Card className={cn(
              "overflow-hidden hover:shadow-md transition-shadow",
              job.status === 'In Progress' && "border-amber-200",
              job.status === 'Failed' && "border-red-200"
            )}>
              <div className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4">
                  <div>
                    <div className="flex items-center space-x-3">
                      <span className="bg-enterprise-100 text-enterprise-700 text-xs font-semibold px-2.5 py-0.5 rounded">
                        {job.id}
                      </span>
                      <h3 className="text-lg font-medium text-gray-900">{job.name}</h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Created {new Date(job.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <div className="mt-2 sm:mt-0">
                    <div className="text-xs font-medium text-right mb-1">
                      {job.progress}% Complete
                    </div>
                    <Progress value={job.progress} className="h-2 w-full sm:w-48" />
                  </div>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                  <div className="bg-gray-50 p-3 rounded-md">
                    <div className="text-xs text-gray-500 mb-1">Source</div>
                    <div className="font-medium">{job.source}</div>
                    <div className="text-xs text-gray-500 mt-1">{job.sourceType}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-md">
                    <div className="text-xs text-gray-500 mb-1">Target</div>
                    <div className="font-medium">{job.target}</div>
                    <div className="text-xs text-gray-500 mt-1">{job.targetType}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-md">
                    <div className="text-xs text-gray-500 mb-1">Assets</div>
                    <div className="font-medium">{job.assetsCount} Dashboard{job.assetsCount !== 1 && 's'}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {job.completedAt 
                        ? `Completed ${new Date(job.completedAt).toLocaleString()}` 
                        : 'Processing...'}
                    </div>
                  </div>
                </div>
                
                {job.error && (
                  <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                    Error: {job.error}
                  </div>
                )}
              </div>
            </Card>
          </Link>
        ))}
        
        {filteredJobs.length === 0 && (
          <div className="text-center py-12">
            <FileUp className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No jobs found</h3>
            <p className="text-gray-500 mt-2">
              {statusFilter === 'all' 
                ? 'Start by creating your first migration job'
                : `No ${statusFilter} jobs found`}
            </p>
            <Button onClick={() => navigate('/new-job')} className="mt-6">
              <Plus className="mr-2 h-4 w-4" />
              New Migration Job
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Jobs;
