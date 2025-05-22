import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { 
  AlertCircle, 
  ArrowLeft, 
  Check, 
  CheckCircle2, 
  ChevronRight, 
  Clock, 
  Download, 
  ExternalLink, 
  File, 
  FileText, 
  RefreshCw 
} from 'lucide-react';

const mockJobData = {
  'JOB-2023-05': {
    id: 'JOB-2023-05',
    name: 'Sales Performance Dashboards',
    source: 'Tableau Production',
    sourceType: 'Tableau Server',
    target: 'Power BI Production',
    targetType: 'Power BI Service',
    targetWorkspace: 'Sales Analytics',
    status: 'Completed',
    progress: 100,
    createdAt: '2023-03-05T14:30:00',
    startedAt: '2023-03-05T14:30:10',
    completedAt: '2023-03-05T14:45:00',
    assetsCount: 5,
    successCount: 5,
    failedCount: 0,
    logs: [
      { time: '2023-03-05T14:30:00', level: 'INFO', message: 'Migration job created' },
      { time: '2023-03-05T14:30:10', level: 'INFO', message: 'Migration started' },
      { time: '2023-03-05T14:31:23', level: 'INFO', message: 'Connecting to Tableau Server' },
      { time: '2023-03-05T14:31:45', level: 'INFO', message: 'Successfully connected to Tableau Server' },
      { time: '2023-03-05T14:32:12', level: 'INFO', message: 'Extracting "Sales Performance Overview" dashboard' },
      { time: '2023-03-05T14:33:40', level: 'INFO', message: 'Connecting to Power BI Service' },
      { time: '2023-03-05T14:34:05', level: 'INFO', message: 'Successfully connected to Power BI Service' },
      { time: '2023-03-05T14:36:30', level: 'INFO', message: 'Converting dashboard: "Sales Performance Overview"' },
      { time: '2023-03-05T14:40:15', level: 'INFO', message: 'Successfully migrated "Sales Performance Overview"' },
      { time: '2023-03-05T14:43:22', level: 'INFO', message: 'Validating all migrated dashboards' },
      { time: '2023-03-05T14:45:00', level: 'INFO', message: 'Migration completed successfully' }
    ],
    assets: [
      { 
        id: 'asset-1', 
        name: 'Sales Performance Overview', 
        status: 'Success', 
        validationStatus: 'Validated',
        targetUrl: 'https://app.powerbi.com/report/abc123'
      },
      { 
        id: 'asset-2', 
        name: 'Sales by Region', 
        status: 'Success', 
        validationStatus: 'Manual Review',
        targetUrl: 'https://app.powerbi.com/report/abc124'
      },
      { 
        id: 'asset-3', 
        name: 'Product Sales Analysis', 
        status: 'Success', 
        validationStatus: 'Validated',
        targetUrl: 'https://app.powerbi.com/report/abc125'
      },
      { 
        id: 'asset-4', 
        name: 'Customer Segmentation', 
        status: 'Success', 
        validationStatus: 'Validated',
        targetUrl: 'https://app.powerbi.com/report/abc126'
      },
      { 
        id: 'asset-5', 
        name: 'Sales Funnel', 
        status: 'Success', 
        validationStatus: 'Manual Review',
        targetUrl: 'https://app.powerbi.com/report/abc127'
      }
    ],
    validation: {
      summary: {
        assetsValidated: 5,
        structuralIssues: 2,
        dataMismatches: 1,
        visualDifferences: 3
      }
    }
  },
};

const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const job = id ? mockJobData[id as keyof typeof mockJobData] : undefined;
  
  if (!job) {
    return (
      <div className="py-12 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Job Not Found</h2>
        <p className="text-gray-500 mb-6">The migration job you're looking for doesn't exist.</p>
        <Button onClick={() => navigate('/jobs')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Jobs
        </Button>
      </div>
    );
  }
  
  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      toast.success('Job information refreshed');
    }, 1500);
  };
  
  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };
  
  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'Completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'In Progress':
        return <RefreshCw className="h-4 w-4 text-amber-500" />;
      case 'Failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
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
  
  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-600';
      case 'WARNING':
        return 'text-amber-600';
      case 'SUCCESS':
        return 'text-green-600';
      case 'INFO':
      default:
        return 'text-blue-600';
    }
  };
  
  return (
    <div>
      <div className="mb-4">
        <Button variant="ghost" onClick={() => navigate('/jobs')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Jobs
        </Button>
      </div>
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-semibold text-gray-900">{job.name}</h1>
            <span className="bg-enterprise-100 text-enterprise-700 text-xs font-semibold px-2.5 py-0.5 rounded">
              {job.id}
            </span>
            {getStatusBadge(job.status)}
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Created {formatDateTime(job.createdAt)}
          </p>
        </div>
        
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            className="flex items-center"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
          <Button size="sm" className="flex items-center">
            <Download className="mr-2 h-4 w-4" />
            Download Report
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Source Connection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{job.source}</div>
            <div className="text-sm text-gray-500">{job.sourceType}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Target Connection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{job.target}</div>
            <div className="text-sm text-gray-500">
              {job.targetType} - {job.targetWorkspace}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{job.progress}% Complete</div>
            <Progress value={job.progress} className="h-2 mt-2" />
            <div className="text-sm text-gray-500 mt-2">
              {job.completedAt ? `Completed ${formatDateTime(job.completedAt)}` : 'In Progress...'}
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Tabs defaultValue="assets">
        <TabsList className="mb-6">
          <TabsTrigger value="assets">Migrated Assets</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>
        
        <TabsContent value="assets">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Migration Assets</CardTitle>
                <div className="text-sm text-gray-500">
                  {job.successCount}/{job.assetsCount} Successfully Migrated
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="border rounded-md overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="p-3 font-medium">Name</th>
                      <th className="p-3 font-medium">Status</th>
                      <th className="p-3 font-medium">Validation</th>
                      <th className="p-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {job.assets.map((asset) => (
                      <tr key={asset.id} className="hover:bg-gray-50">
                        <td className="p-3">
                          <div className="flex items-center space-x-2">
                            <File className="h-4 w-4 text-gray-500" />
                            <span>{asset.name}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge
                            className={
                              asset.status === 'Success'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }
                            variant="outline"
                          >
                            {asset.status}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <Badge
                            className={
                              asset.validationStatus === 'Validated'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-amber-100 text-amber-800'
                            }
                            variant="outline"
                          >
                            {asset.validationStatus}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <div className="flex space-x-2">
                            <Link
                              to={`/validation/${job.id}/${asset.id}`}
                              className="text-sm font-medium text-enterprise-600 hover:text-enterprise-700 inline-flex items-center"
                            >
                              Validate
                              <ChevronRight className="ml-1 h-4 w-4" />
                            </Link>
                            <a
                              href={asset.targetUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-medium text-enterprise-600 hover:text-enterprise-700 inline-flex items-center"
                            >
                              Open
                              <ExternalLink className="ml-1 h-4 w-4" />
                            </a>
                            <Button onClick={() => window.open(asset.targetUrl, '_blank')} size="sm" variant="outline">View Report</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="logs">
          <Card className="mb-6">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Migration Logs</CardTitle>
                <Button variant="outline" size="sm">
                  <FileText className="mr-2 h-4 w-4" />
                  Download Logs
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 border rounded-md bg-gray-50">
                <div className="p-4 font-mono text-sm">
                  {job.logs.map((log, i) => (
                    <div key={i} className="mb-1">
                      <span className="text-gray-500">{new Date(log.time).toLocaleTimeString()}</span>{' '}
                      <span className={getLogLevelColor(log.level)}>[{log.level}]</span>{' '}
                      {log.message}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="validation">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">Assets Validated</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{job.validation.summary.assetsValidated}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">Structural Issues</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-600">{job.validation.summary.structuralIssues}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">Data Mismatches</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-600">{job.validation.summary.dataMismatches}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">Visual Differences</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-600">{job.validation.summary.visualDifferences}</div>
              </CardContent>
            </Card>
          </div>
          
          <Card>
            <CardHeader>
              <CardTitle>Validation Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-enterprise-50 mb-4">
                  <ChevronRight className="h-8 w-8 text-enterprise-600" />
                </div>
                <h3 className="text-lg font-medium mb-2">Select an asset to view validation details</h3>
                <p className="text-gray-500 max-w-md mx-auto mb-6">
                  Click on an asset from the "Migrated Assets" tab to view detailed validation results and perform validation tasks.
                </p>
                <Button 
                  variant="outline"
                  onClick={() => document.querySelector('[data-value="assets"]')?.click()}
                >
                  Go to Assets
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default JobDetail;
