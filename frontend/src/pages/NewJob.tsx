
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, ArrowRight, CheckCheck, Loader2, Upload } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';

const NewJob: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [jobName, setJobName] = useState('');
  const [sourceConnection, setSourceConnection] = useState('');
  const [targetConnection, setTargetConnection] = useState('');
  const [selectedTab, setSelectedTab] = useState('api');
  const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
  const [targetWorkspace, setTargetWorkspace] = useState('');
  const [overwriteExisting, setOverwriteExisting] = useState(false);
  
  // Mock data for the form
  const sourceConnections = [
    { id: '1', name: 'Tableau Production', type: 'Tableau Server' },
    { id: '2', name: 'Tableau Development', type: 'Tableau Server' },
    { id: '3', name: 'Tableau Analytics', type: 'Tableau Cloud' },
  ];
  
  const targetConnections = [
    { id: '4', name: 'Power BI Production', type: 'Power BI Service' },
    { id: '5', name: 'Power BI Development', type: 'Power BI Service' },
  ];
  
  const mockAssets = [
    { id: 'asset-1', name: 'Sales Dashboard', project: 'Sales', type: 'Dashboard' },
    { id: 'asset-2', name: 'Marketing Overview', project: 'Marketing', type: 'Dashboard' },
    { id: 'asset-3', name: 'Customer Insights', project: 'Sales', type: 'Dashboard' },
    { id: 'asset-4', name: 'Financial Report', project: 'Finance', type: 'Dashboard' },
    { id: 'asset-5', name: 'Product Performance', project: 'Product', type: 'Dashboard' },
  ];
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // This would be a real API call in production
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      toast.success('Migration job created successfully');
      navigate('/jobs');
    } catch (error) {
      console.error('Error creating job:', error);
      toast.error('Failed to create migration job');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleAssetToggle = (assetId: string) => {
    if (selectedAssets.includes(assetId)) {
      setSelectedAssets(selectedAssets.filter(id => id !== assetId));
    } else {
      setSelectedAssets([...selectedAssets, assetId]);
    }
  };
  
  const nextStep = () => {
    if (step === 1) {
      if (!jobName || !sourceConnection || !targetConnection) {
        toast.error('Please fill in all required fields');
        return;
      }
    } else if (step === 2) {
      if (selectedTab === 'api' && selectedAssets.length === 0) {
        toast.error('Please select at least one asset to migrate');
        return;
      }
    }
    
    setStep(step + 1);
  };
  
  const prevStep = () => {
    setStep(step - 1);
  };
  
  return (
    <div>
      <Button
        variant="ghost"
        className="mb-6"
        onClick={() => navigate('/jobs')}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Jobs
      </Button>
      
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Create Migration Job</h1>
        <p className="text-gray-500 mt-1">
          Configure and start a new dashboard migration job
        </p>
      </div>
      
      <div className="mb-8">
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className={`flex items-center ${step >= 1 ? 'text-enterprise-600' : 'text-gray-400'}`}>
                <div className={`rounded-full h-8 w-8 flex items-center justify-center border-2 ${step >= 1 ? 'border-enterprise-600 bg-enterprise-50' : 'border-gray-300'}`}>
                  {step > 1 ? <CheckCheck className="h-4 w-4" /> : '1'}
                </div>
                <span className="ml-2 font-medium">Basic Information</span>
              </div>
            </div>
            <div className="w-full sm:w-32 h-0.5 bg-gray-200">
              <div className={`h-0.5 bg-enterprise-600 transition-all duration-500 ${step > 1 ? 'w-full' : 'w-0'}`}></div>
            </div>
            <div className="flex-1">
              <div className={`flex items-center ${step >= 2 ? 'text-enterprise-600' : 'text-gray-400'}`}>
                <div className={`rounded-full h-8 w-8 flex items-center justify-center border-2 ${step >= 2 ? 'border-enterprise-600 bg-enterprise-50' : 'border-gray-300'}`}>
                  {step > 2 ? <CheckCheck className="h-4 w-4" /> : '2'}
                </div>
                <span className="ml-2 font-medium">Source Assets</span>
              </div>
            </div>
            <div className="w-full sm:w-32 h-0.5 bg-gray-200">
              <div className={`h-0.5 bg-enterprise-600 transition-all duration-500 ${step > 2 ? 'w-full' : 'w-0'}`}></div>
            </div>
            <div className="flex-1">
              <div className={`flex items-center ${step >= 3 ? 'text-enterprise-600' : 'text-gray-400'}`}>
                <div className={`rounded-full h-8 w-8 flex items-center justify-center border-2 ${step >= 3 ? 'border-enterprise-600 bg-enterprise-50' : 'border-gray-300'}`}>
                  3
                </div>
                <span className="ml-2 font-medium">Target Configuration</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit}>
            {/* Step 1: Basic Information */}
            {step === 1 && (
              <div className="space-y-6">
                <div>
                  <Label htmlFor="job-name" className="text-base">Job Name</Label>
                  <Input
                    id="job-name"
                    placeholder="Enter a descriptive name for this migration job"
                    className="mt-1.5"
                    value={jobName}
                    onChange={(e) => setJobName(e.target.value)}
                    required
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="source-connection" className="text-base">Source Connection</Label>
                    <Select 
                      value={sourceConnection} 
                      onValueChange={setSourceConnection}
                    >
                      <SelectTrigger id="source-connection" className="mt-1.5">
                        <SelectValue placeholder="Select source connection" />
                      </SelectTrigger>
                      <SelectContent>
                        {sourceConnections.map(conn => (
                          <SelectItem key={conn.id} value={conn.id}>
                            {conn.name} ({conn.type})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="target-connection" className="text-base">Target Connection</Label>
                    <Select 
                      value={targetConnection} 
                      onValueChange={setTargetConnection}
                    >
                      <SelectTrigger id="target-connection" className="mt-1.5">
                        <SelectValue placeholder="Select target connection" />
                      </SelectTrigger>
                      <SelectContent>
                        {targetConnections.map(conn => (
                          <SelectItem key={conn.id} value={conn.id}>
                            {conn.name} ({conn.type})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}
            
            {/* Step 2: Source Asset Selection */}
            {step === 2 && (
              <div>
                <h3 className="text-lg font-medium mb-4">Select Source Assets</h3>
                
                <Tabs defaultValue="api" value={selectedTab} onValueChange={setSelectedTab}>
                  <TabsList className="mb-6">
                    <TabsTrigger value="api">Select from Available Assets</TabsTrigger>
                    <TabsTrigger value="file">Upload Files</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="api" className="space-y-4">
                    <div className="border rounded-md overflow-hidden">
                      <table className="w-full">
                        <thead>
                          <tr className="bg-gray-50 text-left">
                            <th className="p-3 font-medium">Select</th>
                            <th className="p-3 font-medium">Name</th>
                            <th className="p-3 font-medium">Project</th>
                            <th className="p-3 font-medium">Type</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {mockAssets.map((asset) => (
                            <tr key={asset.id} className="hover:bg-gray-50">
                              <td className="p-3">
                                <Checkbox 
                                  checked={selectedAssets.includes(asset.id)}
                                  onCheckedChange={() => handleAssetToggle(asset.id)}
                                />
                              </td>
                              <td className="p-3">{asset.name}</td>
                              <td className="p-3">{asset.project}</td>
                              <td className="p-3">{asset.type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    
                    <div className="mt-4 flex items-center justify-between">
                      <span className="text-sm text-gray-500">
                        {selectedAssets.length} item{selectedAssets.length !== 1 && 's'} selected
                      </span>
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => setSelectedAssets([])}
                        disabled={selectedAssets.length === 0}
                      >
                        Clear Selection
                      </Button>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="file">
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                      <div className="mx-auto">
                        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <div className="mt-2">
                          <label
                            htmlFor="file-upload"
                            className="inline-flex items-center rounded-md bg-enterprise-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-enterprise-500 cursor-pointer"
                          >
                            Select Files
                          </label>
                          <input
                            id="file-upload"
                            name="file-upload"
                            type="file"
                            className="sr-only"
                            multiple
                            accept=".twb,.twbx,.pbix"
                          />
                        </div>
                        <p className="mt-2 text-sm text-gray-500">
                          Drag and drop files or click to select files
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Supported formats: .twb, .twbx, .pbix
                        </p>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            )}
            
            {/* Step 3: Target Configuration */}
            {step === 3 && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium mb-4">Target Configuration</h3>
                
                <div>
                  <Label htmlFor="target-workspace" className="text-base">Target Workspace</Label>
                  <Input
                    id="target-workspace"
                    placeholder="Enter Power BI workspace name or ID"
                    className="mt-1.5"
                    value={targetWorkspace}
                    onChange={(e) => setTargetWorkspace(e.target.value)}
                    required
                  />
                </div>
                
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="overwrite"
                    checked={overwriteExisting}
                    onCheckedChange={() => setOverwriteExisting(!overwriteExisting)}
                  />
                  <Label htmlFor="overwrite" className="text-sm font-medium leading-none">
                    Overwrite existing dashboards with the same name
                  </Label>
                </div>
              </div>
            )}
            
            <div className="mt-8 pt-6 border-t border-gray-200 flex justify-between">
              {step > 1 && (
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Previous Step
                </Button>
              )}
              
              {step < 3 ? (
                <Button type="button" className="ml-auto" onClick={nextStep}>
                  Next Step
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              ) : (
                <Button type="submit" className="ml-auto" disabled={isLoading}>
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating Job...
                    </>
                  ) : (
                    <>Start Migration</>
                  )}
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default NewJob;
