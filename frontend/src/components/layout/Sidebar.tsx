
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

const Sidebar: React.FC<SidebarProps> = ({ open }) => {
  return (
    <aside 
      className={cn(
        "fixed inset-y-0 left-0 z-20 bg-white border-r border-gray-200 transition-all duration-300 pt-16",
        open ? "w-64" : "w-0 -translate-x-full"
      )}
    >
      <div className="overflow-y-auto h-full p-3">
        <nav className="space-y-1">
          <NavItem to="/dashboard" icon={<Home size={20} />} label="Dashboard" />
          <NavItem to="/connections" icon={<Database size={20} />} label="Connections" />
          <NavItem to="/jobs" icon={<Truck size={20} />} label="Migration Jobs" />
          <NavItem to="/monitoring" icon={<BarChart3 size={20} />} label="Monitoring" />
          <NavItem to="/validation" icon={<ListChecks size={20} />} label="Validation" />
          <NavItem to="/settings" icon={<Settings size={20} />} label="Settings" />
        </nav>
      </div>
    </aside>
  );
};

export default Sidebar;
