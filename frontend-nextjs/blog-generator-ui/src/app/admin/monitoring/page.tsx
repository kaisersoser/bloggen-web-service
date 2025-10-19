'use client';

import { useSession } from 'next-auth/react';
import { useState, useEffect, useCallback, memo, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, RefreshCw, Activity, Database, Zap, HardDrive, Cpu, MemoryStick } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface HealthStatus {
  service: string;
  healthy: boolean;
  response_time_ms: number;
  details: Record<string, any>;
  error: string | null;
}

interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_available_mb: number;
  disk_usage_percent: number;
  open_connections: number;
  thread_count: number;
  timestamp: string;
}

interface DatabasePoolStats {
  initialized: boolean;
  closed: boolean;
  size: number;
  free: number;
  in_use: number;
  max_size: number;
  min_size: number;
}

interface DatabasePoolHistory {
  timestamp: string;
  size: number;
  free: number;
  in_use: number;
  utilization: number;
}

interface PerformanceMetric {
  execution_count: number;
  avg_duration: number;
  min_duration: number;
  max_duration: number;
  total_duration: number;
  last_execution: string | null;
}

interface MonitoringData {
  status: 'healthy' | 'degraded';
  health: Record<string, HealthStatus>;
  metrics: {
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    avg_response_time: number;
    error_rate: number;
    requests_per_minute: number;
  };
  performance: Record<string, PerformanceMetric>;
  system: SystemMetrics;
  timestamp: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// Memoized chart components to prevent unnecessary re-renders
const SystemHistoryChart = memo(({ data }: { data: SystemMetrics[] }) => {
  if (data.length === 0) return null;
  
  return (
    <Card className="p-6">
      <h2 className="text-xl font-semibold mb-4">Resource Usage Trends (Last 10 minutes)</h2>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              label={{ value: 'Usage (%)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              labelFormatter={(value) => new Date(value).toLocaleString()}
              formatter={(value: number) => `${value.toFixed(1)}%`}
            />
            <Line
              type="monotone"
              dataKey="cpu_percent"
              name="CPU"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={false}
              isAnimationActive={true}
              animationDuration={300}
            />
            <Line
              type="monotone"
              dataKey="memory_percent"
              name="Memory"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              isAnimationActive={true}
              animationDuration={300}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
});
SystemHistoryChart.displayName = 'SystemHistoryChart';

const DatabasePoolChart = memo(({ data }: { data: DatabasePoolHistory[] }) => {
  if (data.length === 0) return null;
  
  return (
    <div>
      <h3 className="text-sm font-semibold mb-3">Connection Usage Over Time</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            dataKey="timestamp" 
            stroke="#9CA3AF"
            fontSize={10}
            tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              second: '2-digit'
            })}
          />
          <YAxis stroke="#9CA3AF" fontSize={12} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#1F2937', 
              border: '1px solid #374151',
              borderRadius: '6px'
            }}
            labelFormatter={(value) => new Date(value as string).toLocaleTimeString()}
            formatter={(value: number, name: string) => {
              const label = name === 'in_use' ? 'In Use' : name === 'free' ? 'Free' : 'Total';
              return [value, label];
            }}
          />
          <Line 
            type="monotone" 
            dataKey="in_use" 
            stroke="#3B82F6" 
            strokeWidth={2}
            name="In Use"
            dot={false}
            isAnimationActive={true}
            animationDuration={300}
          />
          <Line 
            type="monotone" 
            dataKey="free" 
            stroke="#10B981" 
            strokeWidth={2}
            name="Free"
            dot={false}
            isAnimationActive={true}
            animationDuration={300}
          />
          <Line 
            type="monotone" 
            dataKey="size" 
            stroke="#8B5CF6" 
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Total"
            dot={false}
            isAnimationActive={true}
            animationDuration={300}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});
DatabasePoolChart.displayName = 'DatabasePoolChart';

export default function AdminMonitoringPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [monitoringData, setMonitoringData] = useState<MonitoringData | null>(null);
  const [systemHistory, setSystemHistory] = useState<SystemMetrics[]>([]);
  const [poolHistory, setPoolHistory] = useState<DatabasePoolHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Redirect if not admin
  useEffect(() => {
    if (status === 'loading') return;
    
    if (!session || session.user?.role !== 'ADMIN') {
      router.push('/');
      return;
    }
  }, [session, status, router]);

  // Fetch monitoring data
  const fetchMonitoringData = useCallback(async (isInitialLoad = false) => {
    try {
      // Only show full loading on initial load, use refreshing state for updates
      if (isInitialLoad) {
        setLoading(true);
      } else {
        setIsRefreshing(true);
      }
      
      // Fetch full status
      const statusResponse = await fetch(`${BACKEND_URL}/metrics`);
      if (!statusResponse.ok) {
        throw new Error('Failed to fetch monitoring data');
      }
      const statusData = await statusResponse.json();
      setMonitoringData(statusData);
      
      // Fetch system history
      const historyResponse = await fetch(`${BACKEND_URL}/metrics/system`);
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setSystemHistory(historyData.history || []);
      }
      
      // Fetch database pool stats and update history
      const poolResponse = await fetch(`${BACKEND_URL}/health/database-pool`);
      if (poolResponse.ok) {
        const poolData = await poolResponse.json();
        if (poolData.stats && poolData.stats.initialized) {
          const newPoolEntry: DatabasePoolHistory = {
            timestamp: new Date().toISOString(),
            size: poolData.stats.size || 0,
            free: poolData.stats.free || 0,
            in_use: poolData.stats.in_use || 0,
            utilization: poolData.stats.max_size > 0 
              ? (poolData.stats.in_use / poolData.stats.max_size) * 100 
              : 0,
          };
          
          setPoolHistory(prev => {
            const updated = [...prev, newPoolEntry];
            // Keep only last 20 entries for the graph
            return updated.slice(-20);
          });
        }
      }
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch monitoring data');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    if (session?.user?.role !== 'ADMIN') return;
    fetchMonitoringData(true);
  }, [session, fetchMonitoringData]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      fetchMonitoringData(false); // Not initial load, so won't show loading spinner
    }, 10000); // Refresh every 10 seconds
    
    return () => clearInterval(interval);
  }, [autoRefresh, fetchMonitoringData]);

  const getStatusColor = (healthy: boolean) => healthy ? 'text-green-500' : 'text-red-500';
  const getStatusIcon = (healthy: boolean) => healthy ? '✅' : '❌';
  const getStatusBadge = (healthy: boolean) => {
    return healthy 
      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
  };

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
    return null;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <Button onClick={() => router.push('/admin/audit')} variant="outline" className="mb-6">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Cost Analytics
          </Button>
          
          <Card className="p-6">
            <div className="text-center text-red-600 dark:text-red-400">
              <p className="text-lg font-semibold mb-2">❌ Error Loading Monitoring Data</p>
              <p className="text-sm">{error}</p>
              <Button onClick={() => fetchMonitoringData(true)} className="mt-4">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (!monitoringData) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Button onClick={() => router.push('/admin/audit')} variant="outline" className="mb-2">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Cost Analytics
            </Button>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
              <Activity className="w-8 h-8" />
              System Health & Performance Monitoring
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Real-time monitoring of system health, performance, and resources
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => setAutoRefresh(!autoRefresh)}
              variant={autoRefresh ? 'default' : 'outline'}
              className="relative"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
            </Button>
            <Button onClick={() => fetchMonitoringData(false)} variant="outline" disabled={isRefreshing}>
              <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
            </Button>
          </div>
        </div>

        {/* Overall Status */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold mb-2">System Status</h2>
              <div className="flex items-center gap-3">
                <span className={`text-3xl font-bold ${monitoringData.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                  {monitoringData.status === 'healthy' ? '✅ HEALTHY' : '⚠️ DEGRADED'}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  monitoringData.status === 'healthy' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
                }`}>
                  {monitoringData.status.toUpperCase()}
                </span>
              </div>
            </div>
            <div className="text-right text-sm text-gray-600 dark:text-gray-400">
              Last updated: {new Date(monitoringData.timestamp).toLocaleString()}
            </div>
          </div>
        </Card>

        {/* Service Health Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(monitoringData.health).map(([serviceName, health]) => (
            <Card key={serviceName} className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {serviceName === 'database' && <Database className="w-5 h-5 text-blue-500" />}
                  {serviceName === 'redis' && <Zap className="w-5 h-5 text-red-500" />}
                  {serviceName === 'sse' && <Activity className="w-5 h-5 text-purple-500" />}
                  {serviceName === 'system' && <Cpu className="w-5 h-5 text-orange-500" />}
                  <h3 className="font-semibold capitalize">{serviceName}</h3>
                </div>
                <span className={getStatusColor(health.healthy)}>{getStatusIcon(health.healthy)}</span>
              </div>
              
              <div className={`px-2 py-1 rounded text-xs font-medium mb-2 ${getStatusBadge(health.healthy)}`}>
                {health.healthy ? 'Healthy' : 'Unhealthy'}
              </div>
              
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Response:</span>
                  <span className="font-mono">{health.response_time_ms.toFixed(2)}ms</span>
                </div>
                
                {health.error && (
                  <div className="text-red-600 dark:text-red-400 text-xs mt-2">
                    Error: {health.error}
                  </div>
                )}
                
                {Object.entries(health.details).slice(0, 2).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">{key}:</span>
                    <span className="font-mono">{String(value)}</span>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>

        {/* Request Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Requests</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {monitoringData.metrics.total_requests.toLocaleString()}
                </p>
              </div>
              <div className="text-blue-500">📊</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Success Rate</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {monitoringData.metrics.total_requests > 0
                    ? ((monitoringData.metrics.successful_requests / monitoringData.metrics.total_requests) * 100).toFixed(1)
                    : 0}%
                </p>
              </div>
              <div className="text-green-500">✅</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Response Time</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {monitoringData.metrics.avg_response_time.toFixed(3)}s
                </p>
              </div>
              <div className="text-purple-500">⚡</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Error Rate</p>
                <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {monitoringData.metrics.error_rate.toFixed(2)}%
                </p>
              </div>
              <div className="text-red-500">❌</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Requests/Min</p>
                <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {monitoringData.metrics.requests_per_minute}
                </p>
              </div>
              <div className="text-orange-500">📈</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Failed Requests</p>
                <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {monitoringData.metrics.failed_requests}
                </p>
              </div>
              <div className="text-gray-500">⚠️</div>
            </div>
          </Card>
        </div>

        {/* System Resources */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <HardDrive className="w-5 h-5" />
            System Resources
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* CPU */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-2">
                  <Cpu className="w-4 h-4" />
                  CPU Usage
                </span>
                <span className="text-lg font-bold">{monitoringData.system.cpu_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    monitoringData.system.cpu_percent > 80
                      ? 'bg-red-500'
                      : monitoringData.system.cpu_percent > 60
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(monitoringData.system.cpu_percent, 100)}%` }}
                ></div>
              </div>
            </div>

            {/* Memory */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-2">
                  <MemoryStick className="w-4 h-4" />
                  Memory Usage
                </span>
                <span className="text-lg font-bold">{monitoringData.system.memory_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    monitoringData.system.memory_percent > 80
                      ? 'bg-red-500'
                      : monitoringData.system.memory_percent > 60
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${Math.min(monitoringData.system.memory_percent, 100)}%` }}
                ></div>
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                {monitoringData.system.memory_used_mb.toFixed(0)} MB / {(monitoringData.system.memory_used_mb + monitoringData.system.memory_available_mb).toFixed(0)} MB
              </div>
            </div>

            {/* Disk */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium flex items-center gap-2">
                  <HardDrive className="w-4 h-4" />
                  Disk Usage
                </span>
                <span className="text-lg font-bold">{monitoringData.system.disk_usage_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    monitoringData.system.disk_usage_percent > 80
                      ? 'bg-red-500'
                      : monitoringData.system.disk_usage_percent > 60
                      ? 'bg-yellow-500'
                      : 'bg-purple-500'
                  }`}
                  style={{ width: `${Math.min(monitoringData.system.disk_usage_percent, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <span className="text-sm text-gray-600 dark:text-gray-400">Open Connections</span>
              <span className="font-mono font-semibold">{monitoringData.system.open_connections}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <span className="text-sm text-gray-600 dark:text-gray-400">Thread Count</span>
              <span className="font-mono font-semibold">{monitoringData.system.thread_count}</span>
            </div>
          </div>
        </Card>

        {/* Database Connection Pool */}
        {monitoringData.health.system?.details?.database_pool && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Database className="w-5 h-5" />
              Database Connection Pool
            </h2>
            
            {(() => {
              const pool = monitoringData.health.system.details.database_pool as DatabasePoolStats;
              const utilization = pool.max_size > 0 ? (pool.in_use / pool.max_size) * 100 : 0;
              const isHealthy = pool.initialized && !pool.closed && utilization < 80;
              
              return (
                <>
                  {/* Pool Status Banner */}
                  <div className={`p-4 rounded-lg mb-6 ${
                    !pool.initialized || pool.closed 
                      ? 'bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700'
                      : utilization > 80
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700'
                      : 'bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {!pool.initialized || pool.closed ? '❌' : utilization > 80 ? '⚠️' : '✅'}
                        </span>
                        <div>
                          <div className="font-semibold">
                            {!pool.initialized 
                              ? 'Pool Not Initialized' 
                              : pool.closed 
                              ? 'Pool Closed' 
                              : utilization > 80
                              ? `High Utilization: ${utilization.toFixed(1)}%`
                              : `Healthy: ${utilization.toFixed(1)}% Utilized`
                            }
                          </div>
                          <div className="text-sm opacity-75">
                            {pool.in_use} in use • {pool.free} free • {pool.size} total (max: {pool.max_size})
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-bold">{pool.in_use}/{pool.max_size}</div>
                        <div className="text-xs opacity-75">connections</div>
                      </div>
                    </div>
                  </div>

                  {/* Pool Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="text-sm text-blue-600 dark:text-blue-400 mb-1">In Use</div>
                      <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">{pool.in_use}</div>
                      <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">Active connections</div>
                    </div>
                    
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                      <div className="text-sm text-green-600 dark:text-green-400 mb-1">Free</div>
                      <div className="text-2xl font-bold text-green-700 dark:text-green-300">{pool.free}</div>
                      <div className="text-xs text-green-600 dark:text-green-400 mt-1">Available now</div>
                    </div>
                    
                    <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                      <div className="text-sm text-purple-600 dark:text-purple-400 mb-1">Total</div>
                      <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">{pool.size}</div>
                      <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">Current pool size</div>
                    </div>
                    
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
                      <div className="text-sm text-orange-600 dark:text-orange-400 mb-1">Utilization</div>
                      <div className="text-2xl font-bold text-orange-700 dark:text-orange-300">{utilization.toFixed(0)}%</div>
                      <div className="text-xs text-orange-600 dark:text-orange-400 mt-1">of max capacity</div>
                    </div>
                  </div>

                  {/* Visual Bar */}
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Connection Distribution</span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {pool.in_use} / {pool.max_size} ({utilization.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="relative w-full h-8 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      {/* In Use - Blue */}
                      <div
                        className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500"
                        style={{ width: `${(pool.in_use / pool.max_size) * 100}%` }}
                      >
                        {pool.in_use > 0 && (
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                            {pool.in_use} in use
                          </span>
                        )}
                      </div>
                      {/* Free - Green */}
                      <div
                        className="absolute top-0 h-full bg-gradient-to-r from-green-500 to-green-600 transition-all duration-500"
                        style={{ 
                          left: `${(pool.in_use / pool.max_size) * 100}%`,
                          width: `${(pool.free / pool.max_size) * 100}%` 
                        }}
                      >
                        {pool.free > 0 && (
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                            {pool.free} free
                          </span>
                        )}
                      </div>
                      {/* Unused capacity - Light gray */}
                      <div
                        className="absolute top-0 right-0 h-full bg-gray-300 dark:bg-gray-600 transition-all duration-500"
                        style={{ width: `${Math.max(0, 100 - ((pool.size / pool.max_size) * 100))}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mt-2">
                      <span>Min: {pool.min_size}</span>
                      <span>Current: {pool.size}</span>
                      <span>Max: {pool.max_size}</span>
                    </div>
                  </div>

                  {/* Real-time Graph - Using Memoized Component */}
                  <DatabasePoolChart data={poolHistory} />
                </>
              );
            })()}
          </Card>
        )}

        {/* System History Chart - Using Memoized Component */}
        <SystemHistoryChart data={systemHistory} />

        {/* Performance Metrics */}
        {Object.keys(monitoringData.performance).length > 0 && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Performance Metrics</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4">Operation</th>
                    <th className="text-right py-3 px-4">Executions</th>
                    <th className="text-right py-3 px-4">Avg Duration</th>
                    <th className="text-right py-3 px-4">Min</th>
                    <th className="text-right py-3 px-4">Max</th>
                    <th className="text-right py-3 px-4">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(monitoringData.performance).map(([operation, metrics]) => (
                    <tr key={operation} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-3 px-4 font-medium">{operation}</td>
                      <td className="text-right py-3 px-4 font-mono">{metrics.execution_count}</td>
                      <td className="text-right py-3 px-4 font-mono text-blue-600 dark:text-blue-400">
                        {metrics.avg_duration.toFixed(3)}s
                      </td>
                      <td className="text-right py-3 px-4 font-mono text-green-600 dark:text-green-400">
                        {metrics.min_duration.toFixed(3)}s
                      </td>
                      <td className="text-right py-3 px-4 font-mono text-red-600 dark:text-red-400">
                        {metrics.max_duration.toFixed(3)}s
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {metrics.total_duration.toFixed(2)}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
