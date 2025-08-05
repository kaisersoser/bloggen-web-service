// Audit and analytics types for cost tracking

export interface LLMCallData {
  id: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  totalCost: number;
  phase: string;
  agentRole: string;
  callType: string;
  timestamp: Date;
}

export interface AuditSessionData {
  id: string;
  sessionType: string;
  startTime: Date;
  endTime: Date | null;
  totalCost: number;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  callCount: number;
  createdAt: Date;
  llmCalls: LLMCallData[];
  user: {
    name: string | null;
    email: string | null;
    role: string;
  } | null;
  blog: {
    topic: string;
    status: string;
  } | null;
}

export interface AnalyticsSummary {
  totalCost: number;
  totalTokens: number;
  totalCalls: number;
  totalSessions: number;
  dateRange: {
    from: string;
    to: string;
  };
}

export interface ChartDataPoint {
  date: string;
  cost: number;
}

export interface BreakdownItem {
  phase?: string;
  model?: string;
  role?: string;
  cost: number;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  chartData: ChartDataPoint[];
  breakdowns: {
    byPhase: BreakdownItem[];
    byModel: BreakdownItem[];
    byUserRole: BreakdownItem[];
  };
}
