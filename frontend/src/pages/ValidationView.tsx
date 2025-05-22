
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { AlertTriangle, ArrowLeft, Check, CheckCircle2, ExternalLink, UploadCloud, X } from 'lucide-react';

// Mock validation data
const mockValidationData = {
  'asset-1': {
    id: 'asset-1',
    name: 'Sales Performance Overview',
    jobId: 'JOB-2023-05',
    source: {
      name: 'Sales Performance Overview.twbx',
      type: 'Tableau',
      url: 'https://tableau-server.example.com/views/Sales/Overview'
    },
    target: {
      name: 'Sales Performance Overview',
      type: 'Power BI',
      url: 'https://app.powerbi.com/report/abc123'
    },
    metadata: {
      status: 'Completed',
      issues: [
        { 
          type: 'Warning', 
          description: 'Field "Profit Ratio" on visual "Sales Trend" has different calculation logic' 
        },
        { 
          type: 'Warning', 
          description: 'Filter "Region" is configured differently in the target' 
        }
      ],
      summary: {
        visualCount: 8,
        matchedVisuals: 7,
        filters: 4,
        matchedFilters: 3,
        parameters: 2,
        matchedParameters: 2
      }
    },
    data: {
      status: 'Pending',
      comparisons: [
        {
          visualName: 'Sales by Region',
          sourceDataStatus: 'Not Uploaded',
          targetDataStatus: 'Not Uploaded'
        },
        {
          visualName: 'Sales Trend',
          sourceDataStatus: 'Not Uploaded',
          targetDataStatus: 'Not Uploaded'
        }
      ]
    },
    visual: {
      status: 'Pending',
      sourceScreenshot: null,
      targetScreenshot: null
    },
    functional: {
      status: 'In Progress',
      items: [
        { id: 'check-1', name: 'Region filter updates all visuals correctly', status: 'Passed' },
        { id: 'check-2', name: 'Date range filter functions as expected', status: 'Not Checked' },
        { id: 'check-3', name: 'Drill-through to detail works correctly', status: 'Failed' },
        { id: 'check-4', name: 'All interactive tooltips display properly', status: 'Not Checked' }
      ]
    }
  }
};

const ValidationView: React.FC = () => {
  const { jobId, assetId } = useParams<{ jobId: string; assetId: string }>();
  const navigate = useNavigate();
  
  // Get validation data for this asset
  const validation = assetId ? mockValidationData[assetId as keyof typeof mockValidationData] : undefined;
  
  const [functionalChecks, setFunctionalChecks] = useState(
    validation?.functional.items || []
  );
  
  if (!validation) {
    return (
      <div className="py-12 text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Asset Not Found</h2>
        <p className="text-gray-500 mb-6">The asset you're looking for doesn't exist.</p>
        <Button onClick={() => navigate(`/jobs/${jobId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Job
        </Button>
      </div>
    );
  }
  
  const handleFunctionalCheck = (id: string, status: string) => {
    setFunctionalChecks(
      functionalChecks.map(item => 
        item.id === id ? { ...item, status } : item
      )
    );
    
    toast.success(`Check updated to "${status}"`);
  };
  
  const handleApprove = () => {
    toast.success(`${validation.name} has been approved!`);
    navigate(`/jobs/${jobId}`);
  };
  
  const handleRequestRevision = () => {
    toast.success(`Revision requested for ${validation.name}`);
    navigate(`/jobs/${jobId}`);
  };
  
  return (
    <div>
      <div className="mb-4">
        <Button variant="ghost" onClick={() => navigate(`/jobs/${jobId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Job
        </Button>
      </div>
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Validation: {validation.name}</h1>
          <p className="text-sm text-gray-500 mt-1">
            Compare and validate the source and target dashboards
          </p>
        </div>
        
        <div className="flex space-x-2">
          <Button 
            variant="outline" 
            className="flex items-center"
            onClick={() => window.open(validation.source.url, '_blank')}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Open Source
          </Button>
          <Button 
            className="flex items-center"
            onClick={() => window.open(validation.target.url, '_blank')}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Open Target
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{validation.source.name}</div>
            <div className="text-sm text-gray-500">{validation.source.type}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Target</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-medium">{validation.target.name}</div>
            <div className="text-sm text-gray-500">{validation.target.type}</div>
          </CardContent>
        </Card>
      </div>
      
      <Tabs defaultValue="metadata">
        <TabsList className="mb-6">
          <TabsTrigger value="metadata">Metadata Validation</TabsTrigger>
          <TabsTrigger value="data">Data Validation</TabsTrigger>
          <TabsTrigger value="visual">Visual Comparison</TabsTrigger>
          <TabsTrigger value="functional">Functional Testing</TabsTrigger>
        </TabsList>
        
        <TabsContent value="metadata">
          <Card className="mb-6">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Structure and Metadata Validation</CardTitle>
                <Badge
                  variant="outline"
                  className={validation.metadata.issues.length > 0 ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}
                >
                  {validation.metadata.issues.length > 0 ? 'Issues Found' : 'No Issues'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500 mb-1">Visuals</div>
                  <div className="text-2xl font-bold">
                    {validation.metadata.summary.matchedVisuals}/{validation.metadata.summary.visualCount}
                  </div>
                  <div className="text-xs text-gray-500">Matched</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500 mb-1">Filters</div>
                  <div className="text-2xl font-bold">
                    {validation.metadata.summary.matchedFilters}/{validation.metadata.summary.filters}
                  </div>
                  <div className="text-xs text-gray-500">Matched</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="text-sm text-gray-500 mb-1">Parameters</div>
                  <div className="text-2xl font-bold">
                    {validation.metadata.summary.matchedParameters}/{validation.metadata.summary.parameters}
                  </div>
                  <div className="text-xs text-gray-500">Matched</div>
                </div>
              </div>
              
              {validation.metadata.issues.length > 0 ? (
                <div>
                  <h3 className="font-medium mb-3">Issues Detected</h3>
                  <div className="border rounded-md overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gray-50 text-left">
                          <th className="p-3 font-medium">Type</th>
                          <th className="p-3 font-medium">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {validation.metadata.issues.map((issue, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="p-3">
                              <Badge
                                variant="outline"
                                className={issue.type === 'Error' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}
                              >
                                {issue.type}
                              </Badge>
                            </td>
                            <td className="p-3">{issue.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mb-3">
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No Metadata Issues Found</h3>
                  <p className="text-gray-500">
                    All visuals, filters, and parameters match between source and target.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="data">
          <Card className="mb-6">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Data Comparison</CardTitle>
                <Badge
                  variant="outline"
                  className="bg-amber-100 text-amber-800"
                >
                  Pending Data Upload
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {validation.data.comparisons.map((comp, index) => (
                <div key={index} className="mb-6 last:mb-0">
                  <h3 className="font-medium mb-4">{comp.visualName}</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                      <div className="mb-3 text-gray-500">Source Data</div>
                      <div className="mb-4">
                        <UploadCloud className="h-10 w-10 text-gray-400 mx-auto" />
                      </div>
                      <Button variant="outline" className="w-full">
                        Upload Source CSV
                      </Button>
                      <p className="text-xs text-gray-500 mt-2">
                        Upload data extracted from {validation.source.type}
                      </p>
                    </div>
                    
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                      <div className="mb-3 text-gray-500">Target Data</div>
                      <div className="mb-4">
                        <UploadCloud className="h-10 w-10 text-gray-400 mx-auto" />
                      </div>
                      <Button variant="outline" className="w-full">
                        Upload Target CSV
                      </Button>
                      <p className="text-xs text-gray-500 mt-2">
                        Upload data extracted from {validation.target.type}
                      </p>
                    </div>
                  </div>
                  
                  {index < validation.data.comparisons.length - 1 && (
                    <Separator className="my-6" />
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="visual">
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Visual Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <div className="mb-3 text-gray-500">Source Screenshot</div>
                  <div className="mb-4">
                    <UploadCloud className="h-10 w-10 text-gray-400 mx-auto" />
                  </div>
                  <Button variant="outline" className="w-full">
                    Upload Screenshot
                  </Button>
                  <p className="text-xs text-gray-500 mt-2">
                    Upload a screenshot of the {validation.source.type} dashboard
                  </p>
                </div>
                
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <div className="mb-3 text-gray-500">Target Screenshot</div>
                  <div className="mb-4">
                    <UploadCloud className="h-10 w-10 text-gray-400 mx-auto" />
                  </div>
                  <Button variant="outline" className="w-full">
                    Upload Screenshot
                  </Button>
                  <p className="text-xs text-gray-500 mt-2">
                    Upload a screenshot of the {validation.target.type} dashboard
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="functional">
          <Card className="mb-6">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Functional Testing</CardTitle>
                <Badge
                  variant="outline"
                  className="bg-amber-100 text-amber-800"
                >
                  In Progress
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 mb-6">
                Test the interactive functionality of the target dashboard to ensure it matches the expected behavior.
              </p>
              
              <div className="space-y-4">
                {functionalChecks.map((check) => (
                  <div key={check.id} className="p-3 border rounded-md">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{check.name}</div>
                      <div className="flex items-center space-x-2">
                        <Button 
                          size="sm" 
                          variant={check.status === 'Passed' ? 'default' : 'outline'}
                          className={check.status === 'Passed' ? 'bg-green-600 hover:bg-green-700' : ''}
                          onClick={() => handleFunctionalCheck(check.id, 'Passed')}
                        >
                          <Check className="h-4 w-4" />
                          <span className="ml-1">Pass</span>
                        </Button>
                        <Button 
                          size="sm" 
                          variant={check.status === 'Failed' ? 'destructive' : 'outline'}
                          onClick={() => handleFunctionalCheck(check.id, 'Failed')}
                        >
                          <X className="h-4 w-4" />
                          <span className="ml-1">Fail</span>
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      <Separator className="my-6" />
      
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold mb-1">Overall Validation</h2>
          <p className="text-sm text-gray-500">
            Review all validation results before approving or requesting revisions
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" onClick={handleRequestRevision}>
            Request Revision
          </Button>
          <Button onClick={handleApprove}>
            <Check className="mr-2 h-4 w-4" />
            Approve
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ValidationView;
