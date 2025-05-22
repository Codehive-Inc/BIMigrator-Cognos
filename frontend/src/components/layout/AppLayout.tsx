
import React from 'react';
import { cn } from '@/lib/utils';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main 
          className={cn(
            "flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 transition-all duration-300",
            "px-4 py-6 md:px-8 md:ml-64",
            !sidebarOpen && "md:ml-0"
          )}
        >
          <div className="max-w-7xl w-full mx-auto px-4">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
