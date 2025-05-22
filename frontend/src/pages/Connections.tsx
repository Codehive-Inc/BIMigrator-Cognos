
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Database, MoreHorizontal, Edit, Plus, Trash2 } from 'lucide-react';
import ConnectionForm from '@/components/connections/ConnectionForm';

// Mock connection data
const mockConnections = [
  {
    id: '1',
    name: 'Tableau Production',
    type: 'Tableau Server',
    url: 'https://tableau.example.com',
    status: 'Active',
    lastTested: '2023-03-05T14:30:00',
    connectionType: 'source'
  },
  {
    id: '2',
    name: 'Tableau Development',
    type: 'Tableau Server',
    url: 'https://tableau-dev.example.com',
    status: 'Active',
    lastTested: '2023-03-04T11:15:00',
    connectionType: 'source'
  },
  {
    id: '3',
    name: 'Tableau Analytics',
    type: 'Tableau Cloud',
    url: 'https://10ay.online.tableau.com',
    status: 'Error',
    lastTested: '2023-03-03T09:45:00',
    connectionType: 'source'
  },
  {
    id: '4',
    name: 'Power BI Production',
    type: 'Power BI Service',
    status: 'Active',
    lastTested: '2023-03-02T16:20:00',
    connectionType: 'target'
  },
  {
    id: '5',
    name: 'Power BI Development',
    type: 'Power BI Service',
    status: 'Untested',
    lastTested: null,
    connectionType: 'target'
  }
];

const Connections: React.FC = () => {
  const [connections, setConnections] = useState(mockConnections);
  const [activeTab, setActiveTab] = useState("all");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [connectionToDelete, setConnectionToDelete] = useState<string | null>(null);

  const handleTestConnection = (id: string) => {
    toast.success(`Connection ${id} tested successfully`);
  };

  const handleDeleteConnection = (id: string) => {
    setConnectionToDelete(id);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = () => {
    if (connectionToDelete) {
      setConnections(connections.filter(conn => conn.id !== connectionToDelete));
      toast.success('Connection deleted successfully');
      setDeleteConfirmOpen(false);
      setConnectionToDelete(null);
    }
  };

  const filteredConnections = activeTab === "all" 
    ? connections
    : connections.filter(conn => conn.connectionType === activeTab);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Connections</h1>
        <Button onClick={() => setIsAddDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Connection
        </Button>
      </div>

      <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="all">All Connections</TabsTrigger>
          <TabsTrigger value="source">Source Systems</TabsTrigger>
          <TabsTrigger value="target">Target Systems</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-0">
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="p-4 font-medium">Name</th>
                    <th className="p-4 font-medium">Type</th>
                    <th className="p-4 font-medium">Connection Type</th>
                    <th className="p-4 font-medium">Status</th>
                    <th className="p-4 font-medium">Last Tested</th>
                    <th className="p-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredConnections.map((conn) => (
                    <tr key={conn.id} className="hover:bg-gray-50">
                      <td className="p-4">
                        <div className="flex items-center">
                          <Database className="mr-2 h-4 w-4 text-enterprise-500" />
                          <span>{conn.name}</span>
                        </div>
                      </td>
                      <td className="p-4">{conn.type}</td>
                      <td className="p-4">
                        <Badge variant={conn.connectionType === 'source' ? 'secondary' : 'outline'}>
                          {conn.connectionType === 'source' ? 'Source' : 'Target'}
                        </Badge>
                      </td>
                      <td className="p-4">
                        <Badge
                          variant={
                            conn.status === 'Active'
                              ? 'default'
                              : conn.status === 'Error'
                              ? 'destructive'
                              : 'outline'
                          }
                          className={
                            conn.status === 'Active'
                              ? 'bg-green-100 text-green-800'
                              : conn.status === 'Error'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }
                        >
                          {conn.status}
                        </Badge>
                      </td>
                      <td className="p-4">
                        {conn.lastTested
                          ? new Date(conn.lastTested).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td className="p-4">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                              <span className="sr-only">Actions</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => handleTestConnection(conn.id)}
                            >
                              Test Connection
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" /> Edit
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => handleDeleteConnection(conn.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" /> Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  ))}
                  {filteredConnections.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-muted-foreground">
                        No connections found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="source" className="mt-0">
          {/* Source connections content - same structure as "all" */}
        </TabsContent>

        <TabsContent value="target" className="mt-0">
          {/* Target connections content - same structure as "all" */}
        </TabsContent>
      </Tabs>

      {/* Add Connection Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add New Connection</DialogTitle>
            <DialogDescription>
              Configure a connection to your source or target BI platform.
            </DialogDescription>
          </DialogHeader>
          <ConnectionForm 
            onSubmit={(data) => {
              console.log("Form submitted:", data);
              toast.success('Connection created successfully');
              setIsAddDialogOpen(false);
            }}
          />
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this connection? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setDeleteConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={confirmDelete}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Connections;
