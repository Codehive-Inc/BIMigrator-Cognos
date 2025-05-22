
import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  BarChart3,
  Database,
  Home,
  LayoutDashboard,
  ListChecks,
  Settings,
  Truck
} from 'lucide-react';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon, label }) => (
  <NavLink
    to={to}
    className={({ isActive }) => 
      cn(
        "flex items-center px-4 py-2 mt-2 text-gray-700 rounded-md",
        "hover:bg-enterprise-50 hover:text-enterprise-700 transition-colors duration-200",
        isActive && "bg-enterprise-50 text-enterprise-700 font-medium"
      )
    }
  >
    <span className="mr-3">{icon}</span>
    <span>{label}</span>
  </NavLink>
);

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-gray-900/50 z-20 md:hidden"
          onClick={onClose}
        />
      )}
      <aside 
        className={cn(
          "fixed md:sticky top-0 inset-y-0 left-0 z-30 bg-white border-r border-gray-200 transition-all duration-300 pt-16",
          "w-64 md:w-64 transform md:translate-x-0",
          !open && "-translate-x-full"
        )}
      >
        <div className="overflow-y-auto h-full p-3">
          <nav className="space-y-1">
            <NavItem to="/dashboard" icon={<LayoutDashboard size={20} />} label="Dashboard" />
            <NavItem to="/connections" icon={<Database size={20} />} label="Connections" />
            <NavItem to="/jobs" icon={<Truck size={20} />} label="Migration Jobs" />
            <NavItem to="/monitoring" icon={<BarChart3 size={20} />} label="Monitoring" />
            <NavItem to="/tasks" icon={<ListChecks size={20} />} label="Tasks" />
            <NavItem to="/settings" icon={<Settings size={20} />} label="Settings" />
          </nav>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
