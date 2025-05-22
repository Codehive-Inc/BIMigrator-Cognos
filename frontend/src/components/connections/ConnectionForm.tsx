
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { DialogFooter } from '@/components/ui/dialog';

interface ConnectionFormProps {
  onSubmit: (data: any) => void;
  initialData?: any;
}

const ConnectionForm: React.FC<ConnectionFormProps> = ({ onSubmit, initialData }) => {
  const [name, setName] = useState(initialData?.name || '');
  const [connectionType, setConnectionType] = useState(initialData?.connectionType || 'source');
  const [platformType, setPlatformType] = useState(initialData?.type || '');
  const [url, setUrl] = useState(initialData?.url || '');
  const [tokenName, setTokenName] = useState(initialData?.tokenName || '');
  const [tokenSecret, setTokenSecret] = useState('');
  const [siteId, setSiteId] = useState(initialData?.siteId || '');
  const [tenantId, setTenantId] = useState(initialData?.tenantId || '');
  const [clientId, setClientId] = useState(initialData?.clientId || '');
  const [clientSecret, setClientSecret] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const formData = {
      name,
      connectionType,
      type: platformType,
      url: platformType.includes('Tableau') ? url : undefined,
      tokenName: platformType.includes('Tableau') ? tokenName : undefined,
      tokenSecret: platformType.includes('Tableau') ? tokenSecret : undefined,
      siteId: platformType.includes('Tableau') ? siteId : undefined,
      tenantId: platformType === 'Power BI Service' ? tenantId : undefined,
      clientId: platformType === 'Power BI Service' ? clientId : undefined,
      clientSecret: platformType === 'Power BI Service' ? clientSecret : undefined
    };
    
    onSubmit(formData);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <div className="grid gap-6 py-4">
        <div className="grid grid-cols-4 gap-4">
          <Label htmlFor="name" className="text-right flex items-center">
            Connection Name
          </Label>
          <Input
            id="name"
            placeholder="Enter a name for this connection"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="col-span-3"
            required
          />
        </div>
        
        <div className="grid grid-cols-4 gap-4">
          <Label htmlFor="connection-type" className="text-right flex items-center">
            Connection Type
          </Label>
          <RadioGroup
            defaultValue={connectionType}
            onValueChange={setConnectionType}
            className="flex flex-row space-x-4 col-span-3"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="source" id="r1" />
              <Label htmlFor="r1">Source System</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="target" id="r2" />
              <Label htmlFor="r2">Target System</Label>
            </div>
          </RadioGroup>
        </div>
        
        <div className="grid grid-cols-4 gap-4">
          <Label htmlFor="platform-type" className="text-right flex items-center">
            Platform Type
          </Label>
          <Select 
            value={platformType}
            onValueChange={setPlatformType}
          >
            <SelectTrigger className="col-span-3">
              <SelectValue placeholder="Select platform type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Tableau Server">Tableau Server</SelectItem>
              <SelectItem value="Tableau Cloud">Tableau Cloud</SelectItem>
              <SelectItem value="Tableau File">Tableau File (.twb/.twbx)</SelectItem>
              <SelectItem value="Power BI Service">Power BI Service</SelectItem>
              <SelectItem value="Power BI File">Power BI File (.pbix)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        {/* Conditional fields based on the platform type */}
        {platformType.includes('Tableau') && platformType !== 'Tableau File' && (
          <>
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="url" className="text-right flex items-center">
                Server URL
              </Label>
              <Input
                id="url"
                placeholder="https://your-tableau-server.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="col-span-3"
                required
              />
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="site-id" className="text-right flex items-center">
                Site ID
              </Label>
              <Input
                id="site-id"
                placeholder="Site ID (leave blank for default)"
                value={siteId}
                onChange={(e) => setSiteId(e.target.value)}
                className="col-span-3"
              />
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="token-name" className="text-right flex items-center">
                API Token Name
              </Label>
              <Input
                id="token-name"
                placeholder="Token name"
                value={tokenName}
                onChange={(e) => setTokenName(e.target.value)}
                className="col-span-3"
                required
              />
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="token-secret" className="text-right flex items-center">
                API Token Secret
              </Label>
              <Input
                id="token-secret"
                type="password"
                placeholder="••••••••••••••••"
                value={tokenSecret}
                onChange={(e) => setTokenSecret(e.target.value)}
                className="col-span-3"
                required={!initialData} // Not required when editing
              />
            </div>
          </>
        )}
        
        {platformType === 'Power BI Service' && (
          <>
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="tenant-id" className="text-right flex items-center">
                Tenant ID
              </Label>
              <Input
                id="tenant-id"
                placeholder="Your Azure AD Tenant ID"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="col-span-3"
                required
              />
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="client-id" className="text-right flex items-center">
                Client ID
              </Label>
              <Input
                id="client-id"
                placeholder="App Registration Client ID"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="col-span-3"
                required
              />
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <Label htmlFor="client-secret" className="text-right flex items-center">
                Client Secret
              </Label>
              <Input
                id="client-secret"
                type="password"
                placeholder="••••••••••••••••"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                className="col-span-3"
                required={!initialData} // Not required when editing
              />
            </div>
          </>
        )}
      </div>
      
      <DialogFooter>
        <Button type="submit">
          {initialData ? 'Update Connection' : 'Create Connection'}
        </Button>
      </DialogFooter>
    </form>
  );
};

export default ConnectionForm;
