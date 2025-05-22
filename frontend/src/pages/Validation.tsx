
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { 
  AlertTriangle, 
  CheckCircle2, 
  ChevronRight, 
  ExternalLink, 
  Search, 
  Sliders
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Mock validation data for all jobs
const mockValidations = [
  {
    id: 'validation-1',
    assetId: 'asset-1',
    jobId: 'JOB-2023-05',
    name: 'Sales Performance Overview',
    source: 'Tableau Production',
    target: 'Power BI Production',
    status: 'Completed',
    issues: 2,
    lastUpdated: '2023-03-05T15:30:00',
    reviewStatus: 'Approved',
    targetUrl: 'https://app.powerbi.com/report/abc123',
  },
  {
    id: 'validation-2',
    assetId: 'asset-2',
    jobId: 'JOB-2023-05',
    name: 'Sales by Region',
    source: 'Tableau Production',
    target: 'Power BI Production',
    status: 'In Progress',
    issues: 0,
    lastUpdated: '2023-03-05T14:45:00',
    reviewStatus: 'Pending Review',
    targetUrl: 'https://app.powerbi.com/report/abc124',
  },
  {
    id: 'validation-3',
    assetId: 'asset-3',
    jobId: 'JOB-2023-05',
    name: 'Product Sales Analysis',
    source: 'Tableau Production',
    target: 'Power BI Production',
    status: 'Completed',
    issues: 0,
    lastUpdated: '2023-03-05T15:00:00',
    reviewStatus: 'Approved',
    targetUrl: 'https://app.powerbi.com/report/abc125',
  },
  {
    id: 'validation-4',
    assetId: 'asset-4',
    jobId: 'JOB-2023-05',
    name: 'Customer Segmentation',
    source: 'Tableau Production',
    target: 'Power BI Production',
    status: 'Completed',
    issues: 1,
    lastUpdated: '2023-03-05T15:15:00',
    reviewStatus: 'Needs Revision',
    targetUrl: 'https://app.powerbi.com/report/abc126',
  },
  {
    id: 'validation-5',
    assetId: 'asset-5',
    jobId: 'JOB-2023-05',
    name: 'Sales Funnel',
    source: 'Tableau Production',
    target: 'Power BI Production',
    status: 'Failed',
    issues: 5,
    lastUpdated: '2023-03-05T15:20:00',
    reviewStatus: 'Not Started',
    targetUrl: 'https://app.powerbi.com/report/abc127',
  },
  {
    id: 'validation-6',
    assetId: 'asset-6',
    jobId: 'JOB-2023-04',
    name: 'Marketing Campaign Performance',
    source: 'Tableau Development',
    target: 'Power BI Production',
    status: 'In Progress',
    issues: 0,
    lastUpdated: '2023-03-05T16:30:00',
    reviewStatus: 'Not Started',
    targetUrl: 'https://app.powerbi.com/report/abc128',
  }
];

const Validation: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [reviewFilter, setReviewFilter] = useState('all');

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'Completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'In Progress':
        return <Badge className="bg-amber-100 text-amber-800">In Progress</Badge>;
      case 'Failed':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };
  
  const getReviewStatusBadge = (status: string) => {
    let classes = '';
    switch(status) {
      case 'Approved':
        classes = 'bg-green-100 text-green-800';
        break;
      case 'Needs Revision':
        classes = 'bg-red-100 text-red-800';
        break;
      case 'Pending Review':
        classes = 'bg-amber-100 text-amber-800';
        break;
      case 'Not Started':
      default:
        classes = 'bg-gray-100 text-gray-800';
    }
    
    return (
      <Badge className={classes} variant="outline">
        {status}
      </Badge>
    );
  };

  const filteredValidations = mockValidations
    .filter(validation => 
      validation.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      validation.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
      validation.target.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .filter(validation => 
      statusFilter === 'all' || 
      validation.status.toLowerCase() === statusFilter.toLowerCase()
    )
    .filter(validation => 
      reviewFilter === 'all' || 
      validation.reviewStatus.toLowerCase().replace(' ', '-') === reviewFilter.toLowerCase()
    );
  
  const totalIssues = filteredValidations.reduce((sum, val) => sum + val.issues, 0);
  const completedCount = filteredValidations.filter(val => val.status === 'Completed').length;
  const approvedCount = filteredValidations.filter(val => val.reviewStatus === 'Approved').length;
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Validation Dashboard</h1>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Total Dashboards</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{mockValidations.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{completedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Approved</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{approvedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Issues Found</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">{totalIssues}</div>
          </CardContent>
        </Card>
      </div>
      
      <Card className="mb-6">
        <CardHeader>
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
            <CardTitle>Dashboard Validations</CardTitle>
            <div className="flex items-center w-full sm:w-auto gap-2">
              <div className="relative w-full sm:w-64">
                <Search className="h-4 w-4 absolute left-2.5 top-2.5 text-gray-500" />
                <Input
                  placeholder="Search validations..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button variant="ghost" size="sm">
                <Sliders className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Status:</span>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="in progress">In Progress</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Review Status:</span>
              <Select value={reviewFilter} onValueChange={setReviewFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by review status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Review Statuses</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="pending-review">Pending Review</SelectItem>
                  <SelectItem value="needs-revision">Needs Revision</SelectItem>
                  <SelectItem value="not-started">Not Started</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="border rounded-md overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Dashboard Name</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Review Status</TableHead>
                  <TableHead>Issues</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredValidations.map((validation) => (
                  <TableRow key={validation.id}>
                    <TableCell className="font-medium">{validation.name}</TableCell>
                    <TableCell>{validation.source}</TableCell>
                    <TableCell>{validation.target}</TableCell>
                    <TableCell>
                      {getStatusIcon(validation.status)}
                    </TableCell>
                    <TableCell>
                      {getReviewStatusBadge(validation.reviewStatus)}
                    </TableCell>
                    <TableCell>
                      {validation.issues > 0 ? (
                        <Badge variant="outline" className="bg-amber-100 text-amber-800">
                          {validation.issues} {validation.issues === 1 ? 'Issue' : 'Issues'}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-green-100 text-green-800">
                          No Issues
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Link
                          to={`/validation/${validation.jobId}/${validation.assetId}`}
                          className="text-sm font-medium text-enterprise-600 hover:text-enterprise-700 inline-flex items-center"
                        >
                          Validate
                          <ChevronRight className="ml-1 h-4 w-4" />
                        </Link>
                        <a
                          href={validation.targetUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-enterprise-600 hover:text-enterprise-700 inline-flex items-center"
                        >
                          Open
                          <ExternalLink className="ml-1 h-4 w-4" />
                        </a>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {filteredValidations.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center h-32 text-gray-500">
                      No validation results found matching your filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Validation;
