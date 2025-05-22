
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { Check, ChevronRight, Clock, RefreshCcw, Zap, Upload } from 'lucide-react';

const Dashboard: React.FC = () => {
  const handleStartMigration = () => {
    window.location.href = '/migration/upload';
  };
  // Mock data for the dashboard
  const stats = [
    { 
      title: 'Active Connections', 
      value: '7', 
      description: '4 source, 3 target',
      icon: <Zap className="h-5 w-5 text-enterprise-500" />,
      link: '/connections'
    },
    { 
      title: 'Migration Jobs', 
      value: '12', 
      description: '3 in progress, 9 completed',
      icon: <RefreshCcw className="h-5 w-5 text-enterprise-500" />,
      link: '/jobs'
    },
    { 
      title: 'Dashboards Migrated', 
      value: '36', 
      description: 'This month',
      icon: <Check className="h-5 w-5 text-enterprise-500" />,
      link: '/validation'
    }
  ];

  const recentJobs = [
    { 
      id: 'JOB-2023-05', 
      name: 'Sales Performance Dashboards', 
      source: 'Tableau Server', 
      target: 'Power BI', 
      status: 'Completed',
      progress: 100,
      date: '2 hours ago' 
    },
    { 
      id: 'JOB-2023-04', 
      name: 'Marketing Campaign Analytics', 
      source: 'Tableau Server', 
      target: 'Power BI',
      status: 'In Progress',
      progress: 65,
      date: '5 hours ago' 
    },
    { 
      id: 'JOB-2023-03', 
      name: 'Supply Chain Overview', 
      source: 'Tableau Server', 
      target: 'Power BI',
      status: 'In Progress',
      progress: 28,
      date: '8 hours ago' 
    }
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <span className="text-sm text-gray-500">Welcome back, Admin</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map((stat, i) => (
          <Link to={stat.link} key={i}>
            <Card className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-md font-medium">{stat.title}</CardTitle>
                {stat.icon}
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-enterprise-700">{stat.value}</div>
                <CardDescription className="text-sm mt-1">{stat.description}</CardDescription>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-6">Recent Migration Jobs</h2>
      
      <div className="grid grid-cols-1 gap-4">
        {/* Start New Migration Button */}
        <Card className="border-2 border-primary hover:border-primary/80 cursor-pointer transition-all duration-200" onClick={handleStartMigration}>
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <Upload className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="text-xl font-semibold">Start New Migration</h3>
                <p className="text-muted-foreground">Convert your Tableau workbook to Power BI</p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>
        {recentJobs.map((job) => (
          <Card key={job.id} className="overflow-hidden">
            <CardContent className="p-4 sm:p-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="bg-enterprise-100 text-enterprise-700 text-xs font-semibold px-2.5 py-0.5 rounded">
                      {job.id}
                    </span>
                    <h3 className="text-lg font-medium text-gray-900">{job.name}</h3>
                  </div>
                  <span className="text-sm text-gray-500">{job.date}</span>
                </div>
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mt-4 gap-y-2">
                <div className="flex items-center space-x-6">
                  <div>
                    <p className="text-sm text-gray-500">Source</p>
                    <p className="font-medium">{job.source}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Target</p>
                    <p className="font-medium">{job.target}</p>
                  </div>
                </div>
                
                <div className="flex flex-col sm:items-end">
                  <div className="flex items-center space-x-2 mb-1">
                    {job.status === 'Completed' ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Clock className="h-4 w-4 text-amber-500" />
                    )}
                    <span className={`text-sm font-medium ${job.status === 'Completed' ? 'text-green-600' : 'text-amber-600'}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="w-full sm:w-48">
                    <Progress value={job.progress} className="h-2" />
                  </div>
                </div>
              </div>
              
              <div className="mt-4 flex justify-end">
                <Link 
                  to={`/jobs/${job.id}`}
                  className="inline-flex items-center text-sm font-medium text-enterprise-600 hover:text-enterprise-700"
                >
                  View details
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <div className="mt-6 text-center">
        <Link 
          to="/jobs"
          className="text-enterprise-600 hover:text-enterprise-700 font-medium flex items-center justify-center"
        >
          View all jobs
          <ChevronRight className="ml-1 h-4 w-4" />
        </Link>
      </div>
    </div>
  );
};

export default Dashboard;
