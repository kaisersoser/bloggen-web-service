'use client';

import { useSession } from 'next-auth/react';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';

interface AuditAnalytics {
  summary: {
    totalCost: number;
    totalTokens: number;
    totalCalls: number;
    totalSessions: number;
    serperCost?: number;
    llmCost?: number;
    dateRange: {
      from: string;
      to: string;
    };
  };
  chartData: Array<{
    date: string;
    totalCost: number;
    llmCost: number;
    serperCost: number;
  }>;
  breakdowns: {
    byPhase: Array<{
      phase: string;
      cost: number;
    }>;
    byModel: Array<{
      model: string;
      cost: number;
    }>;
    byUserRole: Array<{
      role: string;
      cost: number;
    }>;
  };
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

export default function AdminAuditPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<AuditAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState(30);

  // Redirect if not admin
  useEffect(() => {
    if (status === 'loading') return;
    
    if (!session || session.user?.role !== 'ADMIN') {
      router.push('/');
      return;
    }
  }, [session, status, router]);

  // Fetch analytics data
  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/admin/audit/analytics?days=${dateRange}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }
      
      const data = await response.json();
      setAnalytics(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  useEffect(() => {
    if (session?.user?.role !== 'ADMIN') return;

    fetchAnalytics();
  }, [session, fetchAnalytics]);

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-pulse text-center">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64 mb-4 mx-auto"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48 mx-auto"></div>
        </div>
      </div>
    );
  }

  if (!session || session.user?.role !== 'ADMIN') {
    return null; // Will redirect
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-4xl mx-auto">
          <Card className="p-6 border-red-200 bg-red-50 dark:bg-red-900/20">
            <h1 className="text-xl font-bold text-red-800 dark:text-red-200 mb-2">Error Loading Analytics</h1>
            <p className="text-red-600 dark:text-red-300 mb-4">{error}</p>
            <Button onClick={fetchAnalytics} variant="outline">
              Retry
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-4xl mx-auto">
          <Card className="p-6">
            <p>No analytics data available.</p>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-4">
            {/* Back to Main Blog Button */}
            <Button
              onClick={() => router.push('/blog')}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Blog
            </Button>
            
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                🔍 Admin Audit Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Cost tracking and usage analytics for blog generation
              </p>
            </div>
          </div>
          
          {/* Date Range Selector */}
          <div className="flex gap-2">
            {[7, 30, 90].map((days) => (
              <Button
                key={days}
                variant={dateRange === days ? "default" : "outline"}
                size="sm"
                onClick={() => setDateRange(days)}
              >
                {days} days
              </Button>
            ))}
          </div>
        </div>

  {/* Summary Cards */}
  <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Cost</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  ${analytics.summary.totalCost.toFixed(4)}
                </p>
              </div>
              <div className="text-green-500">💰</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">LLM Cost</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  ${((analytics.summary.llmCost ?? analytics.summary.totalCost - (analytics.summary.serperCost || 0))).toFixed(4)}
                </p>
              </div>
              <div className="text-blue-500">🧠</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Serper Cost</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  ${((analytics.summary.serperCost) || 0).toFixed(4)}
                </p>
              </div>
              <div className="text-purple-500">🔎</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Tokens</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {analytics.summary.totalTokens.toLocaleString()}
                </p>
              </div>
              <div className="text-blue-500">🔢</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">API Calls</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {analytics.summary.totalCalls.toLocaleString()}
                </p>
              </div>
              <div className="text-purple-500">📞</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sessions</p>
                <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {analytics.summary.totalSessions}
                </p>
              </div>
              <div className="text-orange-500">🎯</div>
            </div>
          </Card>
        </div>

        {/* Cost Over Time Chart */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Cost Trends Over Time (Total vs LLM vs Serper)</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value: string) => new Date(value).toLocaleDateString()}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value: number) => `$${value.toFixed(3)}`}
                />
                <Tooltip 
                  labelFormatter={(value: string) => new Date(value).toLocaleDateString()}
                  formatter={(value: number, name: string) => [`$${value.toFixed(4)}`, name]}
                />
                <Line type="monotone" dataKey="totalCost" name="Total" stroke="#0088FE" strokeWidth={2} dot={{ fill: '#0088FE', strokeWidth: 2, r: 3 }} />
                <Line type="monotone" dataKey="llmCost" name="LLM" stroke="#34D399" strokeWidth={2} dot={{ fill: '#34D399', strokeWidth: 2, r: 3 }} />
                <Line type="monotone" dataKey="serperCost" name="Serper" stroke="#A855F7" strokeWidth={2} dot={{ fill: '#A855F7', strokeWidth: 2, r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Breakdown Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cost by Phase */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Cost by Phase</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analytics.breakdowns.byPhase}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ phase, percent }: { phase?: string; percent?: number }) => `${phase || 'Unknown'} (${percent ? (percent * 100).toFixed(1) : 0}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="cost"
                  >
                    {analytics.breakdowns.byPhase.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toFixed(4)}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Cost by Model */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Cost by Model</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.breakdowns.byModel}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="model" 
                    tick={{ fontSize: 10 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value: number) => `$${value.toFixed(3)}`}
                  />
                  <Tooltip formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']} />
                  <Bar dataKey="cost" fill="#00C49F" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Cost by User Role */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Cost by User Role</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analytics.breakdowns.byUserRole}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ role, percent }: { role?: string; percent?: number }) => `${role || 'Unknown'} (${percent ? (percent * 100).toFixed(1) : 0}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="cost"
                  >
                    {analytics.breakdowns.byUserRole.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toFixed(4)}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Detailed Breakdown Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Phase Breakdown</h3>
            <div className="space-y-2">
              {analytics.breakdowns.byPhase.map((item, index) => (
                <div key={index} className="flex justify-between items-center py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm font-medium">{item.phase}</span>
                  <span className="text-sm text-green-600 dark:text-green-400 font-mono">
                    ${item.cost.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">Model Breakdown</h3>
            <div className="space-y-2">
              {analytics.breakdowns.byModel.map((item, index) => (
                <div key={index} className="flex justify-between items-center py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm font-medium">{item.model}</span>
                  <span className="text-sm text-green-600 dark:text-green-400 font-mono">
                    ${item.cost.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">User Role Breakdown</h3>
            <div className="space-y-2">
              {analytics.breakdowns.byUserRole.map((item, index) => (
                <div key={index} className="flex justify-between items-center py-2 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm font-medium">{item.role}</span>
                  <span className="text-sm text-green-600 dark:text-green-400 font-mono">
                    ${item.cost.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Insights */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">💡 Cost Insights</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium">Average Cost per Session</h4>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                ${(analytics.summary.totalCost / analytics.summary.totalSessions).toFixed(4)}
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium">Average Cost per Token</h4>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                ${(analytics.summary.totalCost / analytics.summary.totalTokens).toFixed(6)}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
